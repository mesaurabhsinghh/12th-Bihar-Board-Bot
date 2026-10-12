import json
import logging
import random
from pathlib import Path
from typing import Dict, List, Optional
from config import DATA_DIR, SUBJECTS

logger = logging.getLogger(__name__)

_CACHE: Dict[str, List[dict]] = {}
_AI_QUESTIONS: Dict[str, Dict[int, dict]] = {}

def _init_ai_cache(subject: str):
    """Loads any previously saved AI questions for the subject."""
    if subject in _AI_QUESTIONS:
        return
    _AI_QUESTIONS[subject] = {}
    ai_file = DATA_DIR / f"{subject}_ai.json"
    if ai_file.exists():
        try:
            with open(ai_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
                for item in saved:
                    _AI_QUESTIONS[subject][item["id"]] = item
        except Exception as e:
            logger.warning(f"Error loading AI questions for {subject}: {e}")

def register_ai_questions(subject: str, ai_q_list: List[dict]) -> List[int]:
    """Registers dynamic AI questions and returns their IDs (starting from 1001)."""
    _init_ai_cache(subject)
    start_id = 1001 + len(_AI_QUESTIONS[subject])
    new_ids = []
    
    for i, q in enumerate(ai_q_list):
        q_id = start_id + i
        q_copy = dict(q)
        q_copy["id"] = q_id
        if "vvi_badge" not in q_copy or "AI" not in q_copy.get("vvi_badge", ""):
            q_copy["vvi_badge"] = "🤖 [Gemini + DeepSeek Multi-Agent Live]"
        _AI_QUESTIONS[subject][q_id] = q_copy
        new_ids.append(q_id)
        
    # Persist to subject_ai.json
    ai_file = DATA_DIR / f"{subject}_ai.json"
    try:
        current_all = list(_AI_QUESTIONS[subject].values())
        with open(ai_file, "w", encoding="utf-8") as f:
            json.dump(current_all, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Error persisting AI questions: {e}")
        
    return new_ids

def load_subject_questions(subject: str) -> List[dict]:
    """Loads and caches questions for a subject from its JSON file."""
    if subject in _CACHE:
        return _CACHE[subject]
    
    if subject not in SUBJECTS:
        return []
    
    file_path = DATA_DIR / SUBJECTS[subject]["file"]
    if not file_path.exists():
        return []
    
    with open(file_path, "r", encoding="utf-8") as f:
        questions = json.load(f)
        _CACHE[subject] = questions
        return questions

def get_question_by_id(subject: str, q_id: int) -> Optional[dict]:
    # Check AI registered questions first
    _init_ai_cache(subject)
    if subject in _AI_QUESTIONS and q_id in _AI_QUESTIONS[subject]:
        return _AI_QUESTIONS[subject][q_id]

    # If composite subject
    if subject == "biology_math":
        q = get_question_by_id("biology", q_id)
        if q:
            return q
        return get_question_by_id("mathematics", q_id)
    elif subject == "english_mega":
        for sub in ["english", "physics", "chemistry", "biology", "mathematics", "hindi"]:
            q = get_question_by_id(sub, q_id)
            if q:
                return q
        return None
        
    questions = load_subject_questions(subject)
    for q in questions:
        if q["id"] == q_id:
            return q
    return None

def generate_quiz_ids(subject: str, count: int = 100, shuffle: bool = True) -> List[int]:
    """Generates question IDs for a quiz session (supports composite slots)."""
    if subject == "biology_math":
        bio_ids = [q["id"] for q in load_subject_questions("biology")]
        math_ids = [q["id"] for q in load_subject_questions("mathematics")]
        if shuffle:
            random.shuffle(bio_ids)
            random.shuffle(math_ids)
        combined = bio_ids[:50] + math_ids[:50]
        if shuffle:
            random.shuffle(combined)
        return combined[:count]
    
    elif subject == "english_mega":
        eng_ids = [q["id"] for q in load_subject_questions("english")]
        phy_ids = [q["id"] for q in load_subject_questions("physics")]
        chem_ids = [q["id"] for q in load_subject_questions("chemistry")]
        hindi_ids = [q["id"] for q in load_subject_questions("hindi")]
        bio_ids = [q["id"] for q in load_subject_questions("biology")]
        math_ids = [q["id"] for q in load_subject_questions("mathematics")]
        if shuffle:
            for l in [eng_ids, phy_ids, chem_ids, hindi_ids, bio_ids, math_ids]:
                random.shuffle(l)
        mega = eng_ids[:50] + phy_ids[:10] + chem_ids[:10] + hindi_ids[:10] + bio_ids[:10] + math_ids[:10]
        if shuffle:
            random.shuffle(mega)
        return mega[:count]

    questions = load_subject_questions(subject)
    ids = [q["id"] for q in questions]
    if shuffle:
        random.shuffle(ids)
    return ids[:count] if count < len(ids) else ids

def get_total_question_count(subject: str) -> int:
    if subject == "biology_math":
        return 200
    elif subject == "english_mega":
        return 600
    return len(load_subject_questions(subject))
