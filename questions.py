import json
import random
from typing import Dict, List, Optional
from config import DATA_DIR, SUBJECTS

_CACHE: Dict[str, List[dict]] = {}

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
