import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# Load environment variables
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DEFAULT_QUESTIONS_PER_QUIZ = int(os.getenv("DEFAULT_QUESTIONS_PER_QUIZ", "10"))
AUTO_NEXT_DELAY_SECONDS = int(os.getenv("AUTO_NEXT_DELAY_SECONDS", "3"))

DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "quiz_bot.db"

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
