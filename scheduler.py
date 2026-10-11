import asyncio
import datetime
import html
import logging
import pytz
from typing import Dict, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import config
import database

logger = logging.getLogger(__name__)

KOLKATA_TZ = pytz.timezone(config.TIMEZONE)

def get_current_ist_time() -> datetime.datetime:
    return datetime.datetime.now(KOLKATA_TZ)

def get_next_live_slot() -> Dict:
    """Calculates which live slot is next based on current IST time."""
    now = get_current_ist_time()
    current_minutes = now.hour * 60 + now.minute

    for slot in config.LIVE_SLOTS:
        slot_minutes = slot["hour"] * 60 + slot["minute"]
        if slot_minutes > current_minutes:
            diff = slot_minutes - current_minutes
            return {
                "slot": slot,
                "is_today": True,
                "minutes_left": diff,
                "time_str": slot["time_str"]
            }

    # If all slots passed for today, next is Slot 1 tomorrow
    first_slot = config.LIVE_SLOTS[0]
    first_minutes = first_slot["hour"] * 60 + first_slot["minute"]
    diff = (24 * 60 - current_minutes) + first_minutes
    return {
        "slot": first_slot,
        "is_today": False,
        "minutes_left": diff,
        "time_str": first_slot["time_str"]
    }

async def send_broadcast_message(context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup=None):
    """Broadcasts a message to all registered users and channels."""
    targets = database.get_broadcast_targets()
    logger.info(f"Broadcasting live alert to {len(targets)} targets...")
    
    success = 0
    for chat_id in targets:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            success += 1
            await asyncio.sleep(0.05)  # Telegram broadcast rate limit avoidance
        except Exception as e:
            logger.debug(f"Failed to send broadcast to {chat_id}: {e}")
            
    logger.info(f"Broadcast completed. Successfully sent to {success}/{len(targets)}")

async def alert_callback(context: ContextTypes.DEFAULT_TYPE):
    """10-Minute Prior Alert Callback."""
    job_data = context.job.data
    slot = job_data["slot"]
    
    alert_text = (
        f"🔔 <b>10 MINUTE LIVE QUIZ ALERT!</b> 🔔\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏰ <b>लाइव टेस्ट समय:</b> {slot['time_str']} (ठीक 10 मिनट बाद)\n"
        f"📚 <b>विषय:</b> {html.escape(slot['title'])}\n"
        f"💯 <b>प्रश्नों की संख्या:</b> 100 VVI Board Questions\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>सभी छात्र कॉपी-कलम के साथ तैयार हो जाएँ! ठीक {slot['time_str']} पर लाइव टेस्ट प्रारंभ होगा।</i>"
    )
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⏰ टाइम टेबल देखें (/schedule)", callback_data="cmd:schedule")]
    ])
    
    await send_broadcast_message(context, alert_text, reply_markup=kb)

async def live_start_callback(context: ContextTypes.DEFAULT_TYPE):
    """Live Launch Callback."""
    job_data = context.job.data
    slot = job_data["slot"]
    slot_id = slot["slot_id"]
    
    launch_text = (
        f"🚨 <b>12th बिहार बोर्ड LIVE VVI टेस्ट शुरू!</b> 🚨\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 <b>{html.escape(slot['badge'])}</b>\n"
        f"📚 <b>{html.escape(slot['title'])}</b>\n"
        f"💯 <b>100 VVI विश्लेषित प्रश्न (100 Marks Practice)</b>\n"
        f"🏆 <b>लाइव टॉपर रैंकिंग (Live Leaderboard) सक्रिय!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>अपना पूरा दम लगाएँ और आज का टॉपर बनें!</i>\n\n"
        f"👇 <b>तुरंत शुरू करने के लिए नीचे दिए गए बटन पर टैप करें:</b>"
    )
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Live Test शुरू करें (100 Questions)", callback_data=f"live_start:{slot_id}")],
        [InlineKeyboardButton("🏆 लाइव लीडरबोर्ड", callback_data=f"live_board:{slot_id}")]
    ])
    
    await send_broadcast_message(context, launch_text, reply_markup=kb)

def setup_live_jobs(job_queue):
    """Registers the 5 daily alerts and live launches with the JobQueue."""
    if not job_queue:
        logger.warning("JobQueue is not available!")
        return

    for slot in config.LIVE_SLOTS:
        # 1. 10-Minute Pre Alert Job
        alert_time = datetime.time(
            hour=slot["alert_hour"],
            minute=slot["alert_minute"],
            tzinfo=KOLKATA_TZ
        )
        job_queue.run_daily(
            alert_callback,
            time=alert_time,
            data={"slot": slot},
            name=f"alert_slot_{slot['slot_id']}"
        )

        # 2. Live Quiz Launch Job
        launch_time = datetime.time(
            hour=slot["hour"],
            minute=slot["minute"],
            tzinfo=KOLKATA_TZ
        )
        job_queue.run_daily(
            live_start_callback,
            time=launch_time,
            data={"slot": slot},
            name=f"launch_slot_{slot['slot_id']}"
        )
        
    logger.info("✅ All 5 daily IST live quiz slots successfully scheduled!")
