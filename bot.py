import asyncio
import html
import logging
import sys
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
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

import config
import database
import questions

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Active auto-advance tasks tracker to avoid multiple triggers per user
_active_auto_tasks = {}

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Returns the main subject selection inline keyboard."""
    keyboard = []
    # 2 buttons per row for subjects
    items = list(config.SUBJECTS.items())
    for i in range(0, len(items), 2):
        row = []
        for key, info in items[i:i+2]:
            row.append(InlineKeyboardButton(f"{info['emoji']} {info['title']}", callback_data=f"sub:{key}"))
        keyboard.append(row)
    
    # Extra feature buttons
    keyboard.append([
        InlineKeyboardButton("📊 मेरा स्कोर (My Stats)", callback_data="cmd:stats"),
        InlineKeyboardButton("🏆 लीडरबोर्ड (Leaderboard)", callback_data="cmd:leaderboard"),
    ])
    keyboard.append([
        InlineKeyboardButton("ℹ️ सहायता (Help)", callback_data="cmd:help"),
    ])
    return InlineKeyboardMarkup(keyboard)

def format_question_message(subject_key: str, q_data: dict, current_q_num: int, total_q_num: int) -> str:
    """Formats the question message text with HTML styling."""
    sub_info = config.SUBJECTS.get(subject_key, {"emoji": "📝", "title": subject_key})
    
    chapter_text = ""
    if q_data.get("chapter"):
        chapter_text = f"📌 <i>पाठ: {html.escape(q_data['chapter'])}</i>\n\n"
    
    q_text = html.escape(q_data["question"])
    
    options_text = ""
    for opt_key in ["A", "B", "C", "D"]:
        if opt_key in q_data["options"]:
            options_text += f"🔘 <b>{opt_key}.</b> {html.escape(q_data['options'][opt_key])}\n"
            
    message_text = (
        f"{sub_info['emoji']} <b>{html.escape(sub_info['title'])} — Question {current_q_num}/{total_q_num}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"{chapter_text}"
        f"❓ <b>{q_text}</b>\n\n"
        f"<b>Options:</b>\n"
        f"{options_text}\n"
        f"<i>नीचे दिए गए बटनों में से सही विकल्प चुनें 👇</i>"
    )
    return message_text

def get_question_keyboard(q_id: int, q_data: dict) -> InlineKeyboardMarkup:
    """Builds inline buttons for question options."""
    keyboard = []
    # Put full option text on separate buttons for easy mobile tapping
    for opt_key in ["A", "B", "C", "D"]:
        if opt_key in q_data["options"]:
            opt_title = q_data["options"][opt_key]
            # Truncate if label is too long for inline button
            if len(opt_title) > 28:
                opt_title = opt_title[:25] + "..."
            button_label = f"🔘 {opt_key}. {opt_title}"
            keyboard.append([InlineKeyboardButton(button_label, callback_data=f"ans:{q_id}:{opt_key}")])
            
    keyboard.append([
        InlineKeyboardButton("⏹️ क्विज़ समाप्त करें (End Quiz)", callback_data="cmd:stop")
    ])
    return InlineKeyboardMarkup(keyboard)

async def send_next_question(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int):
    """Sends the next question in the current active session."""
    session = database.get_session(user_id)
    if not session:
        return
    
    sub_key = session["subject"]
    q_ids = session["question_ids"]
    curr_idx = session["current_index"]
    total = len(q_ids)
    
    if curr_idx >= total:
        # Quiz completed
        await finish_quiz(context, user_id, chat_id, session)
        return
    
    q_id = q_ids[curr_idx]
    q_data = questions.get_question_by_id(sub_key, q_id)
    if not q_data:
        # If question missing, advance
        database.update_session_progress(user_id, curr_idx + 1, session["score"])
        await send_next_question(context, user_id, chat_id)
        return
    
    msg_text = format_question_message(sub_key, q_data, curr_idx + 1, total)
    kb = get_question_keyboard(q_id, q_data)
    
    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=msg_text,
        reply_markup=kb,
        parse_mode=ParseMode.HTML
    )
    database.update_session_progress(user_id, curr_idx, session["score"], last_message_id=msg.message_id)

async def finish_quiz(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int, session: dict):
    """Displays quiz final score and performance overview."""
    score = session["score"]
    total = len(session["question_ids"])
    sub_key = session["subject"]
    sub_info = config.SUBJECTS.get(sub_key, {"title": sub_key, "emoji": "📝"})
    
    accuracy = (score / total * 100) if total > 0 else 0
    database.record_quiz_completed(user_id, sub_key)
    database.clear_session(user_id)
    
    # Custom feedback message based on performance
    if accuracy >= 80:
        feedback = "🌟 <b>शानदार प्रदर्शन!</b> आप बिहार बोर्ड 12th टॉपर बनने की राह पर हैं! 🥇"
    elif accuracy >= 60:
        feedback = "👍 <b>बहुत अच्छा प्रयास!</b> थोड़ा और अभ्यास करें, आपका स्कोर 90%+ हो जाएगा! 🥈"
    else:
        feedback = "💪 <b>नियमित अभ्यास जारी रखें!</b> एनसीईआरटी और मॉडल पेपर का पुनरावलोकन करें। 🎯"
        
    summary_text = (
        f"🎉 <b>क्विज़ समाप्त (Quiz Completed)!</b>\n\n"
        f"📚 <b>विषय:</b> {sub_info['emoji']} {html.escape(sub_info['title'])}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"✅ <b>सही उत्तर (Correct):</b> {score} / {total}\n"
        f"❌ <b>गलत उत्तर (Wrong):</b> {total - score} / {total}\n"
        f"📈 <b>सटीकता (Accuracy):</b> {accuracy:.1f}%\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"{feedback}\n\n"
        f"<i>अगला कदम चुनें:</i>"
    )
    
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 फिर से खेलें (Restart)", callback_data=f"sub:{sub_key}"),
            InlineKeyboardButton("📚 मुख्य मेन्यू (Menu)", callback_data="cmd:menu")
        ],
        [
            InlineKeyboardButton("🏆 लीडरबोर्ड देखें", callback_data="cmd:leaderboard"),
            InlineKeyboardButton("📊 मेरा स्कोर", callback_data="cmd:stats")
        ]
    ])
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=summary_text,
        reply_markup=kb,
        parse_mode=ParseMode.HTML
    )

# ----------------- Command Handlers -----------------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /start command."""
    user = update.effective_user
    database.register_user(user.id, user.username or "", user.first_name or "Student")
    
    welcome_text = (
        f"👋 नमस्ते, <b>{html.escape(user.first_name or 'विद्यार्थी')}!</b>\n\n"
        f"🎓 <b>बिहार बोर्ड (BSEB) 12th Objective Quiz Bot</b> में आपका स्वागत है!\n\n"
        f"यहाँ आप कक्षा 12वीं के सभी महत्वपूर्ण विषयों के <b>वस्तुनिष्ठ प्रश्न (MCQ)</b> का अभ्यास कर सकते हैं।\n\n"
        f"✨ <b>विशेषताएँ:</b>\n"
        f"• सभी प्रश्न बिहार बोर्ड परीक्षा पैटर्न और PYQ पर आधारित\n"
        f"• प्रत्येक प्रश्न के साथ तुरंत उत्तर और विस्तृत व्याख्या (Explanation)\n"
        f"• लाइव स्कोर ट्रैकिंग और लीडरबोर्ड\n\n"
        f"👇 <b>अभ्यास शुरू करने के लिए अपना विषय चुनें:</b>"
    )
    
    await update.message.reply_text(
        text=welcome_text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode=ParseMode.HTML
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /help command."""
    help_text = (
        f"ℹ️ <b>बिहार बोर्ड 12th क्विज़ बॉट - सहायता निर्देशिका</b>\n\n"
        f"<b>1. क्विज़ कैसे खेलें?</b>\n"
        f"• /start दबाएँ और अपना पसंदीदा विषय चुनें।\n"
        f"• बॉट आपके सामने 4 विकल्पों वाला प्रश्न प्रस्तुत करेगा।\n"
        f"• सही विकल्प वाले बटन पर टैप करें।\n"
        f"• बॉट तुरंत बताएगा कि उत्तर सही है या गलत और साथ में व्याख्या देगा।\n"
        f"• इसके बाद अगला प्रश्न स्वतः आ जाएगा!\n\n"
        f"<b>2. मुख्य कमांड:</b>\n"
        f"• /start या /menu - मुख्य विषय मेन्यू खोलें\n"
        f"• /stats - अपना प्रदर्शन और आँकड़े देखें\n"
        f"• /leaderboard - शीर्ष छात्रों की सूची देखें\n"
        f"• /stop - चालू क्विज़ को रोकें\n"
        f"• /help - यह सहायता संदेश देखें\n\n"
        f"<i>शुभकामनाएँ! आपकी बोर्ड परीक्षा की तैयारी शानदार हो! 🌟</i>"
    )
    if update.callback_query:
        await update.callback_query.message.reply_text(help_text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📚 मुख्य मेन्यू (Back to Menu)", callback_data="cmd:menu")]
        ]), parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /stats command."""
    user = update.effective_user
    stats = database.get_user_stats(user.id)
    
    if not stats:
        text = (
            f"📊 <b>आपका स्कोर रिकॉर्ड:</b>\n\n"
            f"आपने अभी तक कोई क्विज़ नहीं खेला है।\n"
            f"शुरू करने के लिए /start दबाएँ और विषय चुनें!"
        )
    else:
        text = f"📊 <b>विद्यार्थी रिपोर्ट: {html.escape(user.first_name)}</b>\n"
        text += "━━━━━━━━━━━━━━━━━━━\n"
        total_att = 0
        total_corr = 0
        for s in stats:
            sub_key = s["subject"]
            sub_title = config.SUBJECTS.get(sub_key, {}).get("title", sub_key)
            emoji = config.SUBJECTS.get(sub_key, {}).get("emoji", "📝")
            att = s["total_attempted"]
            corr = s["total_correct"]
            total_att += att
            total_corr += corr
            acc = (corr / att * 100) if att > 0 else 0
            text += f"{emoji} <b>{html.escape(sub_title)}:</b>\n"
            text += f"   • हल किए गए: {att} | सही: {corr} | सटीकता: {acc:.1f}%\n"
            
        total_acc = (total_corr / total_att * 100) if total_att > 0 else 0
        text += "━━━━━━━━━━━━━━━━━━━\n"
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
        text = "🏆 <b>बिहार बोर्ड क्विज़ — टॉप 10 छात्र (Leaderboard)</b>\n"
        text += "━━━━━━━━━━━━━━━━━━━\n"
        medals = ["🥇", "🥈", "🥉"]
        for rank, r in enumerate(rows, 1):
            badge = medals[rank - 1] if rank <= 3 else f"#{rank}"
            name = html.escape(r["first_name"] or r["username"] or "Student")
            corr = r["correct_sum"] or 0
            att = r["attempted_sum"] or 0
            acc = (corr / att * 100) if att > 0 else 0
            text += f"{badge} <b>{name}</b> — {corr} सही ({acc:.0f}% सटीकता)\n"
        text += "━━━━━━━━━━━━━━━━━━━\n"
        text += "<i>नियमित रूप से खेलें और शीर्ष पर बने रहें! 🔥</i>"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 मुख्य मेन्यू (Menu)", callback_data="cmd:menu")]
    ])
    
    if update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stops the current quiz session."""
    user = update.effective_user
    session = database.get_session(user.id)
    if session:
        database.clear_session(user.id)
        msg = "⏹️ <b>आपकी चालू क्विज़ समाप्त कर दी गई है।</b>\n\nनया विषय चुनने के लिए /start दबाएँ।"
    else:
        msg = "आपके पास कोई चालू क्विज़ नहीं है। /start दबाकर शुरू करें।"
        
    if update.callback_query:
        await update.callback_query.message.reply_text(msg, reply_markup=get_main_menu_keyboard(), parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(msg, reply_markup=get_main_menu_keyboard(), parse_mode=ParseMode.HTML)

# ----------------- Callback Handlers -----------------

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes all inline button clicks."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user = update.effective_user
    user_id = user.id
    chat_id = query.message.chat_id
    
    # 1. Navigation Commands
    if data == "cmd:menu":
        await query.message.reply_text(
            "📚 <b>अपना विषय चुनें:</b>",
            reply_markup=get_main_menu_keyboard(),
            parse_mode=ParseMode.HTML
        )
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
    
    # 2. Subject Selection (Start Quiz)
    if data.startswith("sub:"):
        subject_key = data.split(":")[1]
        if subject_key not in config.SUBJECTS:
            await query.message.reply_text("❌ अमान्य विषय! कृपया पुनः प्रयास करें।")
            return
        
        # Load questions
        q_ids = questions.generate_quiz_ids(subject_key, count=config.DEFAULT_QUESTIONS_PER_QUIZ, shuffle=True)
        if not q_ids:
            await query.message.reply_text("⚠️ इस विषय के लिए अभी प्रश्न उपलब्ध नहीं हैं।")
            return
        
        # Cancel any active auto timer
        if user_id in _active_auto_tasks:
            _active_auto_tasks[user_id].cancel()
            _active_auto_tasks.pop(user_id, None)
            
        # Initialize session in DB
        database.save_session(
            user_id=user_id,
            subject=subject_key,
            question_ids=q_ids,
            current_index=0,
            score=0,
            last_message_id=None
        )
        
        sub_info = config.SUBJECTS[subject_key]
        await query.message.reply_text(
            f"🚀 <b>{sub_info['emoji']} {html.escape(sub_info['title'])} क्विज़ प्रारंभ!</b>\n"
            f"कुल प्रश्न: {len(q_ids)}\n"
            f"<i>पहला प्रश्न आ रहा है...</i>",
            parse_mode=ParseMode.HTML
        )
        
        await send_next_question(context, user_id, chat_id)
        return

    # 3. Next Question manual button (skip delay)
    if data == "action:next":
        if user_id in _active_auto_tasks:
            _active_auto_tasks[user_id].cancel()
            _active_auto_tasks.pop(user_id, None)
        await send_next_question(context, user_id, chat_id)
        return

    # 4. Answer Choice Selected
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
        
        # Validate that this is the current question
        curr_idx = session["current_index"]
        q_ids = session["question_ids"]
        if curr_idx >= len(q_ids) or q_ids[curr_idx] != q_id:
            # Already answered or stale button tap
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
        
        # Record statistics
        database.record_answer_stat(user_id, sub_key, is_correct)
        
        # Advance session index
        next_idx = curr_idx + 1
        database.update_session_progress(user_id, next_idx, new_score, last_message_id=query.message.message_id)
        
        # Build Feedback text according to user format
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
            
        # Edit previous question message to show final selection & remove active options
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        
        # Provide immediate "Next Question" button + schedule automatic advance
        is_last = (next_idx >= len(q_ids))
        next_btn_label = "🏁 परिणाम देखें (View Result)" if is_last else "➡️ अगला प्रश्न (Next Question)"
        
        response_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(next_btn_label, callback_data="action:next")],
            [InlineKeyboardButton("⏹️ क्विज़ समाप्त करें", callback_data="cmd:stop")]
        ])
        
        await query.message.reply_text(
            text=feedback_text,
            reply_markup=response_kb,
            parse_mode=ParseMode.HTML
        )
        
        # Cancel any previous task
        if user_id in _active_auto_tasks:
            _active_auto_tasks[user_id].cancel()
            _active_auto_tasks.pop(user_id, None)
            
        # As requested: "Uske baad agla question automatically aa jayega."
        # Automatically advance after delay (e.g., 3 seconds)
        async def auto_advance():
            try:
                await asyncio.sleep(config.AUTO_NEXT_DELAY_SECONDS)
                # Check if session is still on this step
                sess = database.get_session(user_id)
                if sess and sess["current_index"] == next_idx:
                    await send_next_question(context, user_id, chat_id)
            except asyncio.CancelledError:
                pass
            finally:
                _active_auto_tasks.pop(user_id, None)
                
        task = asyncio.create_task(auto_advance())
        _active_auto_tasks[user_id] = task


import keep_alive


def main():
    """Starts the bot application."""
    database.init_db()
    
    # Start background web server for 24x7 hosting (Render/Koyeb)
    keep_alive.start_keep_alive()
    
    token = config.BOT_TOKEN
    if not token or token == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("=" * 60)
        print("❌ त्रुटि: TELEGRAM BOT TOKEN नहीं मिला!")
        print("कृपया .env फ़ाइल में अपना BOT_TOKEN सेट करें।")
        print("निर्देश:")
        print("1. Telegram पर @BotFather के पास जाएँ")
        print("2. /newbot कमांड चलाकर अपना बॉट बनाएँ")
        print("3. मिले टोकन को .env फ़ाइल में BOT_TOKEN=यहाँ_पेस्ट_करें")
        print("4. फिर 'python bot.py' रन करें")
        print("=" * 60)
        return
    
    app = Application.builder().token(token).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("menu", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("leaderboard", leaderboard_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    print("🚀 12th Bihar Board Telegram Bot सफलता पूर्वक प्रारंभ हो रहा है...")
    print("Listening for messages...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
