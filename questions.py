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
    questions = load_subject_questions(subject)
    for q in questions:
        if q["id"] == q_id:
            return q
    return None

def generate_quiz_ids(subject: str, count: int = 10, shuffle: bool = True) -> List[int]:
    questions = load_subject_questions(subject)
    ids = [q["id"] for q in questions]
    if shuffle:
        random.shuffle(ids)
    return ids[:count] if count < len(ids) else ids

def get_total_question_count(subject: str) -> int:
    return len(load_subject_questions(subject))
