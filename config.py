import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# Load environment variables
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0")) if os.getenv("ADMIN_ID", "").isdigit() else 0
DEFAULT_QUESTIONS_PER_QUIZ = int(os.getenv("DEFAULT_QUESTIONS_PER_QUIZ", "100"))
LIVE_QUIZ_QUESTION_COUNT = 100
AUTO_NEXT_DELAY_SECONDS = int(os.getenv("AUTO_NEXT_DELAY_SECONDS", "3"))

DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "quiz_bot.db"

# IST Timezone for Live Quizzes
TIMEZONE = "Asia/Kolkata"

# 5 Daily Live Slots (Indian Standard Time)
LIVE_SLOTS = [
    {
        "slot_id": 1,
        "time_str": "11:00 AM",
        "hour": 11,
        "minute": 0,
        "alert_hour": 10,
        "alert_minute": 50,
        "subject": "physics",
        "title": "🔬 भौतिक विज्ञान (Physics) — 100 VVI Board Questions",
        "badge": "11:00 AM Morning Mega Test"
    },
    {
        "slot_id": 2,
        "time_str": "02:00 PM",
        "hour": 14,
        "minute": 0,
        "alert_hour": 13,
        "alert_minute": 50,
        "subject": "chemistry",
        "title": "🧪 रसायन विज्ञान (Chemistry) — 100 VVI Board Questions",
        "badge": "02:00 PM Afternoon Master Test"
    },
    {
        "slot_id": 3,
        "time_str": "07:00 PM",
        "hour": 19,
        "minute": 0,
        "alert_hour": 18,
        "alert_minute": 50,
        "subject": "biology_math",
        "title": "🧬 जीव विज्ञान एवं 📐 गणित — 100 VVI Daily Challenge",
        "badge": "07:00 PM Evening Power Test"
    },
    {
        "slot_id": 4,
        "time_str": "09:00 PM",
        "hour": 21,
        "minute": 0,
        "alert_hour": 20,
        "alert_minute": 50,
        "subject": "hindi",
        "title": "📖 हिंदी 100 अंक (Hindi) — 100 VVI Board Questions",
        "badge": "09:00 PM Night Prime Test"
    },
    {
        "slot_id": 5,
        "time_str": "11:00 PM",
        "hour": 23,
        "minute": 0,
        "alert_hour": 22,
        "alert_minute": 50,
        "subject": "english_mega",
        "title": "🇬🇧 English 100M & All-Subject Mega VVI Mix",
        "badge": "11:00 PM Midnight Topper Challenge"
    }
]

# Available subjects configuration
SUBJECTS = {
    "physics": {
        "title": "भौतिक विज्ञान (Physics)",
        "emoji": "🔬",
        "file": "physics.json",
        "description": "BSEB 12th Physics - विद्युत, प्रकाशिकी, परमाणु एवं नाभिक, चुंबकत्व"
    },
    "chemistry": {
        "title": "रसायन विज्ञान (Chemistry)",
        "emoji": "🧪",
        "file": "chemistry.json",
        "description": "BSEB 12th Chemistry - ठोस अवस्था, विलयन, कार्बनिक रसायन"
    },
    "biology": {
        "title": "जीव विज्ञान (Biology)",
        "emoji": "🧬",
        "file": "biology.json",
        "description": "BSEB 12th Biology - जनन, आनुवंशिकी, जैव प्रौद्योगिकी"
    },
    "mathematics": {
        "title": "गणित (Mathematics)",
        "emoji": "📐",
        "file": "mathematics.json",
        "description": "BSEB 12th Maths - आव्यूह, सारणिक, अवकलन, समाकलन, सदिश"
    },
    "hindi": {
        "title": "हिंदी 100 अंक (Hindi 100M)",
        "emoji": "📖",
        "file": "hindi.json",
        "description": "BSEB 12th Hindi - बातचीत, उसने कहा था, व्याकरण एवं साहित्य"
    },
    "english": {
        "title": "English 100 Marks",
        "emoji": "🇬🇧",
        "file": "english.json",
        "description": "BSEB 12th English - Prose, Poetry, Grammar & Story of English"
    }
}
