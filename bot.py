import asyncio
import datetime
import html
import logging
import sys
import time
from typing import Optional

# Ensure Windows console supports UTF-8 and emojis safely
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode, ChatType
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
import database
import keep_alive
import questions
import scheduler
import vvi_engine

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Active auto-advance tasks tracker to avoid duplicate triggers
_active_auto_tasks = {}

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Returns the main subject selection inline keyboard."""
    keyboard = [
        [InlineKeyboardButton("🔴 LIVE 100 VVI QUIZ (अभी चल रहा है)", callback_data="cmd:live")],
        [InlineKeyboardButton("🧠 AI Live VVI Test (Gemini + DeepSeek)", callback_data="cmd:ai_select")]
    ]
    
    # 2 buttons per row for subjects
    items = list(config.SUBJECTS.items())
    for i in range(0, len(items), 2):
        row = []
        for key, info in items[i:i+2]:
            row.append(InlineKeyboardButton(f"{info['emoji']} {info['title']}", callback_data=f"sub:{key}"))
        keyboard.append(row)
    
    # Extra feature buttons
    keyboard.append([
        InlineKeyboardButton("⏰ टाइम टेबल (/schedule)", callback_data="cmd:schedule"),
        InlineKeyboardButton("⭐ VVI स्पेशल (/vvi)", callback_data="cmd:vvi"),
    ])
    keyboard.append([
        InlineKeyboardButton("📊 मेरा स्कोर (Stats)", callback_data="cmd:stats"),
        InlineKeyboardButton("🏆 ऑल-टाइम लीडरबोर्ड", callback_data="cmd:leaderboard"),
    ])
    keyboard.append([
        InlineKeyboardButton("ℹ️ सहायता (Help)", callback_data="cmd:help"),
    ])
    return InlineKeyboardMarkup(keyboard)

def format_question_message(subject_key: str, q_data: dict, current_q_num: int, total_q_num: int, is_live: bool = False, slot_id: int = 0) -> str:
    """Formats question message with VVI analysis badges."""
    sub_info = config.SUBJECTS.get(subject_key, {"emoji": "🎯", "title": subject_key})
    
    live_banner = ""
    if is_live:
        live_banner = f"🔴 <b>[LIVE VVI TEST 100Q]</b> • "
        
    vvi_badge = q_data.get("vvi_badge", "⭐ [VVI 2024-25]")
    
    chapter_text = ""
    if q_data.get("chapter"):
        chapter_text = f"📌 <i>पाठ: {html.escape(q_data['chapter'])}</i>\n"
    
    q_text = html.escape(q_data["question"])
    
    options_text = ""
    for opt_key in ["A", "B", "C", "D"]:
        if opt_key in q_data["options"]:
            options_text += f"🔘 <b>{opt_key}.</b> {html.escape(q_data['options'][opt_key])}\n"
            
    message_text = (
        f"{live_banner}<b>{sub_info['emoji']} {html.escape(sub_info['title'])}</b>\n"
        f"<b>प्रगति: प्रश्न {current_q_num} / {total_q_num}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔖 <b>{html.escape(vvi_badge)}</b>\n"
        f"{chapter_text}\n"
        f"❓ <b>{q_text}</b>\n\n"
        f"<b>Options:</b>\n"
        f"{options_text}\n"
        f"<i>नीचे सही विकल्प चुनें 👇</i>"
    )
    return message_text

def get_question_keyboard(q_id: int, q_data: dict) -> InlineKeyboardMarkup:
    """Builds inline buttons for question options."""
    keyboard = []
    for opt_key in ["A", "B", "C", "D"]:
        if opt_key in q_data["options"]:
            opt_title = q_data["options"][opt_key]
            if len(opt_title) > 28:
                opt_title = opt_title[:25] + "..."
            button_label = f"🔘 {opt_key}. {opt_title}"
            keyboard.append([InlineKeyboardButton(button_label, callback_data=f"ans:{q_id}:{opt_key}")])
            
    keyboard.append([
        InlineKeyboardButton("⏹️ टेस्ट समाप्त करें", callback_data="cmd:stop")
    ])
    return InlineKeyboardMarkup(keyboard)

async def send_next_question(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int):
    """Sends the next question in the active session."""
    session = database.get_session(user_id)
    if not session:
        return
    
    sub_key = session["subject"]
    q_ids = session["question_ids"]
    curr_idx = session["current_index"]
    total = len(q_ids)
    is_live = bool(session.get("is_live", 0))
    slot_id = session.get("slot_id", 0)
    
    if curr_idx >= total:
        await finish_quiz(context, user_id, chat_id, session)
        return
    
    q_id = q_ids[curr_idx]
    q_data = questions.get_question_by_id(sub_key, q_id)
    if not q_data:
        database.update_session_progress(user_id, curr_idx + 1, session["score"])
        await send_next_question(context, user_id, chat_id)
        return
    
    msg_text = format_question_message(sub_key, q_data, curr_idx + 1, total, is_live=is_live, slot_id=slot_id)
    kb = get_question_keyboard(q_id, q_data)
    
    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=msg_text,
        reply_markup=kb,
        parse_mode=ParseMode.HTML
    )
    database.update_session_progress(user_id, curr_idx, session["score"], last_message_id=msg.message_id)

async def finish_quiz(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int, session: dict):
    """Displays quiz final score, grade, and records live stats."""
    score = session["score"]
    total = len(session["question_ids"])
    sub_key = session["subject"]
    sub_info = config.SUBJECTS.get(sub_key, {"title": sub_key, "emoji": "📝"})
    is_live = bool(session.get("is_live", 0))
    slot_id = session.get("slot_id", 0)
    
    accuracy = (score / total * 100) if total > 0 else 0
    database.record_quiz_completed(user_id, sub_key)
    
    # Calculate grade
    if accuracy >= 90:
        grade = "🌟 <b>A+ ग्रेड (State Topper Material!)</b>"
        feedback = "अद्भुत! आप बिहार बोर्ड 12वीं परीक्षा में 90%+ अंक लाने के पूरे हकदार हैं! 🥇"
    elif accuracy >= 75:
        grade = "🥇 <b>A ग्रेड (First Division)</b>"
        feedback = "शानदार प्रदर्शन! थोड़े और अभ्यास से आप टॉप 10 में आ सकते हैं! 🥈"
    elif accuracy >= 60:
        grade = "🥈 <b>B ग्रेड (First Division)</b>"
        feedback = "अच्छा प्रयास! कमजोर अध्यायों का पुनः अभ्यास करें। 🥉"
    else:
        grade = "🥉 <b>C ग्रेड (Second Division)</b>"
        feedback = "नियमित रूप से 5 टाइम लाइव टेस्ट दें और व्याख्या को ध्यान से पढ़ें! 💪"
        
    # Record live slot result if applicable
    if is_live and slot_id > 0:
        database.record_live_result(user_id, slot_id, sub_key, score, total)
        
    database.clear_session(user_id)
    
    summary_text = (
        f"🎉 <b>100 VVI टेस्ट समाप्त (Test Completed)!</b>\n\n"
        f"📚 <b>विषय:</b> {sub_info['emoji']} {html.escape(sub_info['title'])}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ <b>सही उत्तर (Correct):</b> {score} / {total}\n"
        f"❌ <b>गलत उत्तर (Wrong):</b> {total - score} / {total}\n"
        f"📈 <b>सटीकता (Accuracy):</b> {accuracy:.1f}%\n"
        f"🏆 <b>बोर्ड ग्रेड:</b> {grade}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{feedback}\n\n"
        f"<i>अगला कदम चुनें:</i>"
    )
    
    buttons = [
        [
            InlineKeyboardButton("🔄 फिर से खेलें", callback_data=f"sub:{sub_key}"),
            InlineKeyboardButton("📚 मुख्य मेन्यू", callback_data="cmd:menu")
        ]
    ]
    if is_live and slot_id > 0:
        buttons.insert(0, [InlineKeyboardButton("🏆 आज का लाइव लीडरबोर्ड देखें", callback_data=f"live_board:{slot_id}")])
        
    kb = InlineKeyboardMarkup(buttons)
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=summary_text,
        reply_markup=kb,
        parse_mode=ParseMode.HTML
    )

# ----------------- Commands -----------------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /start and /menu commands."""
    user = update.effective_user
    chat = update.effective_chat
    
    if user:
        database.register_user(user.id, user.username or "", user.first_name or "Student")
    if chat and chat.type in [ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL]:
        database.register_chat(chat.id, chat.type, chat.title or "Bihar Study Group")
        
    welcome_text = (
        f"👋 नमस्ते, <b>{html.escape(user.first_name if user else 'विद्यार्थी')}!</b>\n\n"
        f"🎓 <b>बिहार बोर्ड (BSEB) 12th Highly Advanced 100 VVI Quiz Bot</b> में आपका स्वागत है!\n\n"
        f"🔥 <b>दैनिक 5 लाइव टेस्ट (Daily 5 Live Slots - 100 Questions Each):</b>\n"
        f"• 🕚 <b>11:00 AM</b> — 🔬 भौतिक विज्ञान (100 VVI)\n"
        f"• 🕑 <b>02:00 PM</b> — 🧪 रसायन विज्ञान (100 VVI)\n"
        f"• 🕖 <b>07:00 PM</b> — 🧬 जीव विज्ञान एवं 📐 गणित (100 VVI)\n"
        f"• 🕘 <b>09:00 PM</b> — 📖 हिंदी 100 अंक (100 VVI)\n"
        f"• 🕚 <b>11:00 PM</b> — 🇬🇧 English 100M & ऑल-सब्जेक्ट मेगा टेस्ट\n\n"
        f"✨ <i>प्रत्येक प्रश्न के साथ सटीक व्याख्या और लाइव रैंकिंग!</i>\n\n"
        f"👇 <b>अभ्यास शुरू करने के लिए अपना विकल्प चुनें:</b>"
    )
    
    await update.message.reply_text(
        text=welcome_text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode=ParseMode.HTML
    )

async def live_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /live command: shows countdown and instant launch."""
    next_info = scheduler.get_next_live_slot()
    slot = next_info["slot"]
    mins = next_info["minutes_left"]
    hours = mins // 60
    rem_mins = mins % 60
    
    time_display = f"{hours} घंटे {rem_mins} मिनट" if hours > 0 else f"{rem_mins} मिनट"
    
    live_text = (
        f"🔴 <b>12th बिहार बोर्ड — लाइव टेस्ट स्टेटस</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 <b>अगला लाइव टेस्ट:</b> {html.escape(slot['title'])}\n"
        f"⏰ <b>समय:</b> {slot['time_str']} (IST)\n"
        f"⏳ <b>शुरू होने में शेष समय:</b> {time_display}\n"
        f"💯 <b>प्रश्नों की संख्या:</b> 100 VVI Questions\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>आप चाहें तो अभी भी इस टेस्ट को ऑन-डिमांड शुरू कर सकते हैं:</i>"
    )
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🚀 अभी Live Test शुरू करें (100 Qs)", callback_data=f"live_start:{slot['slot_id']}")],
        [InlineKeyboardButton("🏆 आज का लाइव लीडरबोर्ड", callback_data=f"live_board:{slot['slot_id']}")],
        [InlineKeyboardButton("📚 मुख्य मेन्यू (Menu)", callback_data="cmd:menu")]
    ])
    
    if update.callback_query:
        await update.callback_query.message.reply_text(live_text, reply_markup=kb, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(live_text, reply_markup=kb, parse_mode=ParseMode.HTML)

async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /schedule command."""
    sched_text = (
        f"⏰ <b>12th बिहार बोर्ड — दैनिक 5 लाइव टेस्ट टाइम टेबल (IST):</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"1️⃣ <b>11:00 AM (सुबह):</b> 🔬 भौतिक विज्ञान (Physics) — 100 VVI\n"
        f"2️⃣ <b>02:00 PM (दोपहर):</b> 🧪 रसायन विज्ञान (Chemistry) — 100 VVI\n"
        f"3️⃣ <b>07:00 PM (शाम):</b> 🧬 जीव विज्ञान एवं 📐 गणित — 100 VVI\n"
        f"4️⃣ <b>09:00 PM (रात):</b> 📖 हिंदी 100 अंक — 100 VVI\n"
        f"5️⃣ <b>11:00 PM (रात):</b> 🇬🇧 English 100M & मेगा मिक्स — 100 VVI\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔔 <i>हर टेस्ट से 10 मिनट पहले सभी छात्रों को लाइव अलर्ट भेजा जाता है।</i>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔴 अगला टेस्ट देखें (/live)", callback_data="cmd:live")],
        [InlineKeyboardButton("📚 मुख्य मेन्यू", callback_data="cmd:menu")]
    ])
    if update.callback_query:
        await update.callback_query.message.reply_text(sched_text, reply_markup=kb, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(sched_text, reply_markup=kb, parse_mode=ParseMode.HTML)

async def vvi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /vvi command: top VVI menu."""
    text = (
        f"⭐ <b>12th बिहार बोर्ड — VVI प्रश्न बैंक (Top Analyzed MCQs)</b>\n\n"
        f"ये सभी प्रश्न पिछले 6 वर्षों के बोर्ड पेपर, मॉडल पेपर और अनुभवी शिक्षकों के विश्लेषण पर आधारित हैं।\n\n"
        f"👇 <b>जिस विषय का 100 VVI सेट हल करना चाहते हैं, उसे चुनें:</b>"
    )
    if update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=get_main_menu_keyboard(), parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=get_main_menu_keyboard(), parse_mode=ParseMode.HTML)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /stats command."""
    user = update.effective_user
    stats = database.get_user_stats(user.id)
    
    if not stats:
        text = (
            f"📊 <b>आपका स्कोर रिकॉर्ड:</b>\n\n"
            f"आपने अभी तक कोई टेस्ट नहीं दिया है।\n"
            f"शुरू करने के लिए /start दबाएँ!"
        )
    else:
        text = f"📊 <b>छात्र रिपोर्ट कार्ड: {html.escape(user.first_name)}</b>\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━\n"
        total_att = 0
        total_corr = 0
        for s in stats:
            sub_key = s["subject"]
            sub_title = config.SUBJECTS.get(sub_key, {}).get("title", sub_key)
            emoji = config.SUBJECTS.get(sub_key, {}).get("emoji", "🎯")
            att = s["total_attempted"]
            corr = s["total_correct"]
            total_att += att
            total_corr += corr
            acc = (corr / att * 100) if att > 0 else 0
            text += f"{emoji} <b>{html.escape(sub_title)}:</b>\n"
            text += f"   • हल किए गए: {att} | सही: {corr} | सटीकता: {acc:.1f}%\n"
            
        total_acc = (total_corr / total_att * 100) if total_att > 0 else 0
        text += "━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"🎯 <b>कुल प्रश्न:</b> {total_att} | <b>कुल सही:</b> {total_corr}\n"
        text += f"📈 <b>औसत सटीकता:</b> {total_acc:.1f}%\n"
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 मुख्य मेन्यू (Menu)", callback_data="cmd:menu")]
    ])
    if update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /leaderboard command."""
    rows = database.get_leaderboard(limit=10)
    
    if not rows:
        text = "🏆 <b>लीडरबोर्ड:</b>\n\nअभी तक किसी भी छात्र ने क्विज़ हल नहीं किया है। पहले स्थान पर आने के लिए अभी खेलें!"
    else:
        text = "🏆 <b>बिहार बोर्ड 12th — ऑल-टाइम टॉप 10 छात्र</b>\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━\n"
        medals = ["🥇", "🥈", "🥉"]
        for rank, r in enumerate(rows, 1):
            badge = medals[rank - 1] if rank <= 3 else f"#{rank}"
            name = html.escape(r["first_name"] or r["username"] or "Student")
            corr = r["correct_sum"] or 0
            att = r["attempted_sum"] or 0
            acc = (corr / att * 100) if att > 0 else 0
            text += f"{badge} <b>{name}</b> — {corr} सही ({acc:.0f}%)\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "<i>रोजाना 5 टाइम लाइव टेस्ट दें और शीर्ष पर बने रहें! 🔥</i>"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 मुख्य मेन्यू (Menu)", callback_data="cmd:menu")]
    ])
    if update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)

async def admin_live_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to manually trigger live slot alert or launch."""
    user = update.effective_user
    args = context.args
    slot_id = int(args[0]) if args and args[0].isdigit() else 1
    
    selected_slot = None
    for s in config.LIVE_SLOTS:
        if s["slot_id"] == slot_id:
            selected_slot = s
            break
            
    if not selected_slot:
        await update.message.reply_text("अमान्य स्लॉट ID! (1 से 5 चुनें)")
        return
        
    await update.message.reply_text(f"🚀 Admin Triggering Slot {slot_id} Live Broadcast...")
    dummy_job = type('Job', (), {'data': {'slot': selected_slot}})()
    dummy_ctx = type('Context', (), {'job': dummy_job, 'bot': context.bot})()
    await scheduler.live_start_callback(dummy_ctx)

async def ai_predict_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to predict and play fresh VVI questions using Multi-Agent AI."""
    args = context.args
    sub = args[0].lower() if args else "physics"
    if sub not in config.SUBJECTS:
        await update.message.reply_text("उपलब्ध विषय: physics, chemistry, biology, mathematics, hindi, english")
        return
        
    sub_info = config.SUBJECTS.get(sub, {"title": sub, "emoji": "🎯"})
    status_msg = await update.message.reply_text(
        f"⏳ <b>Multi-Agent AI प्रश्न तैयार कर रहा है ({sub_info['emoji']} {html.escape(sub_info['title'])})...</b>\n\n"
        f"• 🤖 <b>Agent 1 (Google Gemini 3.5 Flash / ChatGPT):</b> BSEB Blueprint से प्रश्न ड्राफ्ट कर रहा है...\n"
        f"• 🧐 <b>Agent 2 (DeepSeek v3.1):</b> शुद्धता व व्याख्या का सत्यापन कर रहा है...\n\n"
        f"<i>कृपया 10-15 सेकंड प्रतीक्षा करें...</i>",
        parse_mode=ParseMode.HTML
    )
    new_questions = await vvi_engine.fetch_ai_predicted_vvi(sub, count=10)
    if not new_questions:
        q_ids = questions.generate_quiz_ids(sub, count=10, shuffle=True)
    else:
        q_ids = questions.register_ai_questions(sub, new_questions)
        
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    if user_id in _active_auto_tasks:
        _active_auto_tasks[user_id].cancel()
        _active_auto_tasks.pop(user_id, None)
        
    database.save_session(
        user_id=user_id,
        subject=sub,
        question_ids=q_ids,
        current_index=0,
        score=0,
        is_live=0,
        slot_id=0
    )
    await status_msg.edit_text(
        f"✅ <b>AI Live VVI Test तैयार!</b>\n"
        f"🎯 <b>विषय:</b> {sub_info['emoji']} {html.escape(sub_info['title'])}\n"
        f"🤖 <b>प्रमाणन:</b> Google Gemini 3.5 + DeepSeek v3.1 Live Certified\n"
        f"💯 <b>कुल प्रश्न:</b> {len(q_ids)}\n\n"
        f"<i>पहला प्रश्न आ रहा है...</i>",
        parse_mode=ParseMode.HTML
    )
    await send_next_question(context, user_id, chat_id)


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stops the current quiz session."""
    user = update.effective_user
    session = database.get_session(user.id)
    if session:
        database.clear_session(user.id)
        msg = "⏹️ <b>आपकी चालू क्विज़ समाप्त कर दी गई है।</b>\n\nनया टेस्ट शुरू करने के लिए /start दबाएँ।"
    else:
        msg = "आपके पास कोई चालू टेस्ट नहीं है। /start दबाकर शुरू करें।"
        
    if update.callback_query:
        await update.callback_query.message.reply_text(msg, reply_markup=get_main_menu_keyboard(), parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(msg, reply_markup=get_main_menu_keyboard(), parse_mode=ParseMode.HTML)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /help command."""
    help_text = (
        f"ℹ️ <b>बिहार बोर्ड 12th लाइव क्विज़ बॉट - सहायता निर्देशिका</b>\n\n"
        f"<b>1. लाइव टेस्ट कैसे दें?</b>\n"
        f"• रोजाना 5 बार लाइव टेस्ट आयोजित होता है:\n"
        f"  (11 AM, 2 PM, 7 PM, 9 PM, 11 PM)\n"
        f"• टेस्ट शुरू होने पर आए मैसेज में 'Live Test शुरू करें' पर टैप करें।\n"
        f"• 100 प्रश्नों के उत्तर देकर अपनी लाइव रैंक देखें।\n\n"
        f"<b>2. मुख्य कमांड्स:</b>\n"
        f"• /start या /menu - मुख्य मेन्यू\n"
        f"• /live - अगला लाइव टेस्ट और काउंटडाउन\n"
        f"• /schedule - दैनिक 5 स्लॉट्स का टाइम टेबल\n"
        f"• /vvi - विषय-वार VVI प्रश्न\n"
        f"• /stats - आपका स्कोर कार्ड\n"
        f"• /leaderboard - टॉप 10 छात्र\n"
        f"• /stop - टेस्ट समाप्त करें\n"
    )
    if update.callback_query:
        await update.callback_query.message.reply_text(help_text, reply_markup=get_main_menu_keyboard(), parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

# ----------------- Callback Handlers -----------------

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user = update.effective_user
    user_id = user.id
    chat_id = query.message.chat_id
    
    # 1. Navigation
    if data == "cmd:menu":
        await query.message.reply_text("📚 <b>मुख्य मेन्यू:</b>", reply_markup=get_main_menu_keyboard(), parse_mode=ParseMode.HTML)
        return
    elif data == "cmd:live":
        await live_command(update, context)
        return
    elif data == "cmd:schedule":
        await schedule_command(update, context)
        return
    elif data == "cmd:vvi":
        await vvi_command(update, context)
        return
    elif data == "cmd:stats":
        await stats_command(update, context)
        return
    elif data == "cmd:leaderboard":
        await leaderboard_command(update, context)
        return
    elif data == "cmd:help":
        await help_command(update, context)
        return
    elif data == "cmd:stop":
        await stop_command(update, context)
        return
        
    # 2. Live slot leaderboard
    if data.startswith("live_board:"):
        slot_id = int(data.split(":")[1])
        rows = database.get_live_slot_leaderboard(slot_id, limit=10)
        slot_obj = next((s for s in config.LIVE_SLOTS if s["slot_id"] == slot_id), None)
        title = slot_obj["title"] if slot_obj else f"Slot {slot_id}"
        
        if not rows:
            text = f"🏆 <b>आज के {html.escape(title)} का लीडरबोर्ड:</b>\n\nअभी तक किसी छात्र ने इस टेस्ट को पूरा नहीं किया है। पहले टॉपर बनने के लिए अभी खेलें!"
        else:
            text = f"🏆 <b>आज के लाइव टॉपर — {html.escape(title)}</b>\n"
            text += "━━━━━━━━━━━━━━━━━━━━━━\n"
            for rank, r in enumerate(rows, 1):
                badge = ["🥇", "🥈", "🥉"][rank - 1] if rank <= 3 else f"#{rank}"
                name = html.escape(r["first_name"] or r["username"] or "Student")
                score = r["score"]
                total = r["total"]
                text += f"{badge} <b>{name}</b> — {score}/{total} अंक\n"
            text += "━━━━━━━━━━━━━━━━━━━━━━\n"
            
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📚 मुख्य मेन्यू", callback_data="cmd:menu")]
        ]), parse_mode=ParseMode.HTML)
        return

    # 2.5 AI Select Subject Menu
    if data == "cmd:ai_select":
        kb = [
            [
                InlineKeyboardButton("🔬 भौतिकी (Physics)", callback_data="ai_start:physics"),
                InlineKeyboardButton("🧪 रसायन (Chemistry)", callback_data="ai_start:chemistry")
            ],
            [
                InlineKeyboardButton("🧬 जीव विज्ञान (Biology)", callback_data="ai_start:biology"),
                InlineKeyboardButton("📐 गणित (Mathematics)", callback_data="ai_start:mathematics")
            ],
            [
                InlineKeyboardButton("📖 हिंदी (Hindi)", callback_data="ai_start:hindi"),
                InlineKeyboardButton("🇬🇧 अंग्रेजी (English)", callback_data="ai_start:english")
            ],
            [InlineKeyboardButton("📚 मुख्य मेन्यू", callback_data="cmd:menu")]
        ]
        await query.message.reply_text(
            "🧠 <b>Multi-Agent AI Live VVI Test (10 Questions)</b>\n\n"
            "• 🤖 <b>Agent 1 (Google Gemini 3.5 Flash / ChatGPT):</b> BSEB Blueprint व PYQ के आधार पर तुरंत नए प्रश्न तैयार करता है।\n"
            "• 🧐 <b>Agent 2 (DeepSeek v3.1):</b> शुद्धता, सही उत्तर व हिंदी व्याख्या का लाइव ऑडिट करता है।\n\n"
            "👇 <i>विषय चुनें जिसके लिए AI तुरंत नए प्रश्न बनाए:</i>",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.HTML
        )
        return

    # 2.6 AI Live Test Start
    if data.startswith("ai_start:"):
        subject_key = data.split(":")[1]
        sub_info = config.SUBJECTS.get(subject_key, {"title": subject_key, "emoji": "🎯"})
        
        load_msg = await query.message.reply_text(
            f"⏳ <b>Multi-Agent AI प्रश्न तैयार कर रहा है ({sub_info['emoji']} {html.escape(sub_info['title'])})...</b>\n\n"
            f"• 🤖 <b>Agent 1 (Gemini 3.5 Flash):</b> बिहार बोर्ड 2025-26 के लिए संभावित प्रश्न ड्राफ्ट कर रहा है...\n"
            f"• 🧐 <b>Agent 2 (DeepSeek v3.1):</b> विकल्पों और व्याख्या की जाँच कर रहा है...\n\n"
            f"<i>कृपया 10-15 सेकंड प्रतीक्षा करें...</i>",
            parse_mode=ParseMode.HTML
        )
        
        ai_questions = await vvi_engine.fetch_ai_predicted_vvi(subject_key, count=10)
        if not ai_questions:
            q_ids = questions.generate_quiz_ids(subject_key, count=10, shuffle=True)
        else:
            q_ids = questions.register_ai_questions(subject_key, ai_questions)
            
        if user_id in _active_auto_tasks:
            _active_auto_tasks[user_id].cancel()
            _active_auto_tasks.pop(user_id, None)
            
        database.save_session(
            user_id=user_id,
            subject=subject_key,
            question_ids=q_ids,
            current_index=0,
            score=0,
            is_live=0,
            slot_id=0
        )
        
        await load_msg.edit_text(
            f"✅ <b>AI Live VVI Test तैयार!</b>\n"
            f"🎯 <b>विषय:</b> {sub_info['emoji']} {html.escape(sub_info['title'])}\n"
            f"🤖 <b>प्रमाणन:</b> Google Gemini 3.5 + DeepSeek v3.1 Double Verified\n"
            f"💯 <b>कुल प्रश्न:</b> {len(q_ids)}\n\n"
            f"<i>पहला प्रश्न आ रहा है...</i>",
            parse_mode=ParseMode.HTML
        )
        await send_next_question(context, user_id, chat_id)
        return

    # 3. Live Quiz Start (100 Questions)
    if data.startswith("live_start:"):
        slot_id = int(data.split(":")[1])
        slot_obj = next((s for s in config.LIVE_SLOTS if s["slot_id"] == slot_id), config.LIVE_SLOTS[0])
        subject_key = slot_obj["subject"]
        
        q_ids = vvi_engine.get_hybrid_100_vvi(subject_key)
        if not q_ids:
            await query.message.reply_text("⚠️ प्रश्न लोड करने में त्रुटि।")
            return
            
        if user_id in _active_auto_tasks:
            _active_auto_tasks[user_id].cancel()
            _active_auto_tasks.pop(user_id, None)
            
        database.save_session(
            user_id=user_id,
            subject=subject_key,
            question_ids=q_ids,
            current_index=0,
            score=0,
            is_live=1,
            slot_id=slot_id
        )
        
        await query.message.reply_text(
            f"🚀 <b>LIVE 100 VVI TEST प्रारंभ!</b>\n"
            f"🎯 <b>{html.escape(slot_obj['title'])}</b>\n"
            f"💯 कुल प्रश्न: {len(q_ids)}\n"
            f"<i>पहला प्रश्न आ रहा है...</i>",
            parse_mode=ParseMode.HTML
        )
        await send_next_question(context, user_id, chat_id)
        return

    # 4. Normal Subject Start
    if data.startswith("sub:"):
        subject_key = data.split(":")[1]
        if subject_key not in config.SUBJECTS:
            await query.message.reply_text("❌ अमान्य विषय!")
            return
        
        q_ids = vvi_engine.get_hybrid_100_vvi(subject_key)
        if not q_ids:
            await query.message.reply_text("⚠️ प्रश्न उपलब्ध नहीं हैं।")
            return
        
        if user_id in _active_auto_tasks:
            _active_auto_tasks[user_id].cancel()
            _active_auto_tasks.pop(user_id, None)
            
        database.save_session(
            user_id=user_id,
            subject=subject_key,
            question_ids=q_ids,
            current_index=0,
            score=0,
            is_live=0,
            slot_id=0
        )
        
        sub_info = config.SUBJECTS[subject_key]
        await query.message.reply_text(
            f"🚀 <b>{sub_info['emoji']} {html.escape(sub_info['title'])} 100 VVI टेस्ट प्रारंभ!</b>\n"
            f"कुल प्रश्न: {len(q_ids)}\n"
            f"<i>पहला प्रश्न आ रहा है...</i>",
            parse_mode=ParseMode.HTML
        )
        await send_next_question(context, user_id, chat_id)
        return

    # 5. Next Question manual button
    if data == "action:next":
        if user_id in _active_auto_tasks:
            _active_auto_tasks[user_id].cancel()
            _active_auto_tasks.pop(user_id, None)
        await send_next_question(context, user_id, chat_id)
        return

    # 6. Answer selection
    if data.startswith("ans:"):
        parts = data.split(":")
        if len(parts) != 3:
            return
        
        q_id = int(parts[1])
        selected_opt = parts[2]
        
        session = database.get_session(user_id)
        if not session:
            await query.message.reply_text("⚠️ आपकी क्विज़ समाप्त हो चुकी है। नई क्विज़ के लिए /start दबाएँ।")
            return
        
        curr_idx = session["current_index"]
        q_ids = session["question_ids"]
        if curr_idx >= len(q_ids) or q_ids[curr_idx] != q_id:
            await query.answer("यह प्रश्न पहले ही उत्तरित किया जा चुका है!", show_alert=False)
            return
        
        sub_key = session["subject"]
        q_data = questions.get_question_by_id(sub_key, q_id)
        if not q_data:
            return
        
        correct_opt = q_data["correct"]
        is_correct = (selected_opt.strip().upper() == correct_opt.strip().upper())
        
        new_score = session["score"] + (1 if is_correct else 0)
        curr_question_step = curr_idx + 1
        
        database.record_answer_stat(user_id, sub_key, is_correct)
        
        next_idx = curr_idx + 1
        database.update_session_progress(user_id, next_idx, new_score, last_message_id=query.message.message_id)
        
        correct_title = q_data["options"].get(correct_opt, "")
        selected_title = q_data["options"].get(selected_opt, "")
        explanation = q_data.get("explanation", "बिहार बोर्ड 12th के पाठ्यक्रम पर आधारित।")
        
        if is_correct:
            feedback_text = (
                f"✅ <b>सही जवाब!</b>\n\n"
                f"🎯 <b>सही उत्तर:</b> {correct_opt}. {html.escape(correct_title)}\n\n"
                f"💡 <b>Explanation:</b> {html.escape(explanation)}\n\n"
                f"📊 <b>आपका स्कोर:</b> {new_score}/{curr_question_step}"
            )
        else:
            feedback_text = (
                f"❌ <b>गलत जवाब!</b>\n\n"
                f"आपने चुना: <b>{selected_opt}. {html.escape(selected_title)}</b>\n"
                f"🎯 <b>सही उत्तर:</b> <b>{correct_opt}. {html.escape(correct_title)}</b>\n\n"
                f"💡 <b>Explanation:</b> {html.escape(explanation)}\n\n"
                f"📊 <b>आपका स्कोर:</b> {new_score}/{curr_question_step}"
            )
            
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        
        is_last = (next_idx >= len(q_ids))
        next_btn_label = "🏁 परिणाम देखें (View Result)" if is_last else "➡️ अगला प्रश्न (Next Question)"
        
        response_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(next_btn_label, callback_data="action:next")],
            [InlineKeyboardButton("⏹️ टेस्ट समाप्त करें", callback_data="cmd:stop")]
        ])
        
        await query.message.reply_text(
            text=feedback_text,
            reply_markup=response_kb,
            parse_mode=ParseMode.HTML
        )
        
        if user_id in _active_auto_tasks:
            _active_auto_tasks[user_id].cancel()
            _active_auto_tasks.pop(user_id, None)
            
        async def auto_advance():
            try:
                await asyncio.sleep(config.AUTO_NEXT_DELAY_SECONDS)
                sess = database.get_session(user_id)
                if sess and sess["current_index"] == next_idx:
                    await send_next_question(context, user_id, chat_id)
            except asyncio.CancelledError:
                pass
            finally:
                _active_auto_tasks.pop(user_id, None)
                
        task = asyncio.create_task(auto_advance())
        _active_auto_tasks[user_id] = task

async def chat_tracker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tracks group/channel registrations automatically."""
    chat = update.effective_chat
    if chat and chat.type in [ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL]:
        database.register_chat(chat.id, chat.type, chat.title or "Study Group")

def main():
    """Starts the bot application with JobQueue."""
    database.init_db()
    
    # Start keep-alive web server for 24x7 hosting
    keep_alive.start_keep_alive()
    
    token = config.BOT_TOKEN
    if not token or token == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("❌ त्रुटि: TELEGRAM BOT TOKEN नहीं मिला! .env फ़ाइल में सेट करें।")
        return
    
    app = Application.builder().token(token).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("menu", start_command))
    app.add_handler(CommandHandler("live", live_command))
    app.add_handler(CommandHandler("schedule", schedule_command))
    app.add_handler(CommandHandler("vvi", vvi_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("leaderboard", leaderboard_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("admin_live", admin_live_command))
    app.add_handler(CommandHandler("ai_predict", ai_predict_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, chat_tracker))
    
    # Schedule the 5 daily live slots
    scheduler.setup_live_jobs(app.job_queue)
    
    print("🚀 12th Bihar Board Highly Advanced 5-Slot VVI Live Quiz Bot Started!")
    print("Listening for messages and scheduled live slots...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
