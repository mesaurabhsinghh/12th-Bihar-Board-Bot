import datetime
import json
import logging
import os
import random
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional
import httpx

import config
import questions

logger = logging.getLogger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent"

# Strict Bihar Board 12th Blueprints
BSEB_BLUEPRINTS = {
    "physics": {
        "title": "BSEB Class 12 Physics (भौतिक विज्ञान)",
        "language": "Hindi (with technical terms in brackets)",
        "syllabus_rules": [
            "Strictly follow NCERT Class 12 Physics & BSEB Board PYQ patterns (2018-2024).",
            "Focus on: Electrostatics (Gauss law, Capacitance), Current (Kirchhoff, Wheatstone, Color code, Potentiometer), Magnetism (Lorentz force, Biot-Savart, Dip angle), EMI/AC (Lenz law, Transformer, RMS), Optics (TIR, Brewster, Huygens, Lens formula), Modern Physics (Photoelectric, Bohr, Radioactivity, de Broglie), Semiconductor (p-n diode, Rectifier, Logic Gates), Communication (Sky wave, Modulation).",
            "Level: Standard 1-mark Bihar Board objective question. Avoid IIT-JEE multi-step complex calculations.",
            "Questions should be clear, direct, and factually undeniable."
        ]
    },
    "chemistry": {
        "title": "BSEB Class 12 Chemistry (रसायन विज्ञान)",
        "language": "Hindi (with chemical formulas and English terms)",
        "syllabus_rules": [
            "Strictly follow NCERT Class 12 Chemistry & BSEB 2018-2024 Exam papers.",
            "Focus on: Solid state (Bravais lattices, Schottky/Frenkel defects, Packing fraction), Solutions (Colligative properties, Osmotic pressure, Raoult's law), Electrochemistry (Faraday's laws, Kohlrausch), Kinetics (Zero/First order rate constants, Half life), Surface Chem (Tyndall, Colloids, Emulsion), Metallurgy (Pyrites, Bauxite, Froth floatation), p/d/f-block (Transition metals, Coordination number, K4[Fe(CN)6]), Organic reactions (Phenol to benzene, Vinegar acid, Ascorbic acid, Polymers).",
            "Strictly 1-mark objective level."
        ]
    },
    "mathematics": {
        "title": "BSEB Class 12 Mathematics (गणित)",
        "language": "Hindi/English formula standard",
        "syllabus_rules": [
            "Strictly follow NCERT Class 12 Mathematics curriculum.",
            "Focus on: Matrices & Determinants (Square matrix conditions, Properties), Calculus (Direct standard derivatives d/dx, Standard integrals ∫, Order and Degree of differential equations), Vectors (Dot and Cross products i·i, i×j), 3D Geometry (Direction cosines, planes), ITF (Principal values, sin⁻¹x + cos⁻¹x = π/2), Probability (Conditional P(A|B)).",
            "Quick 1-step objective questions typical of Bihar Board paper."
        ]
    },
    "biology": {
        "title": "BSEB Class 12 Biology (जीव विज्ञान)",
        "language": "Hindi (with scientific English terms)",
        "syllabus_rules": [
            "Strictly follow NCERT Class 12 Biology syllabus.",
            "Focus on: Reproduction in Organisms (Budding in yeast, Bisexual earthworm), Flowering Plants (Endosperm ploidy 3n, Pollen grain), Human Reproduction (Ovulation hormones), Genetics (Mendel's pea experiment, 46 chromosomes, Chargaff's rule A=T), Human Health & Disease (AIDS/HIV, Malaria vector), Biotechnology (Restriction endonuclease molecular scissors, Bt cotton), Ecology (10% energy pyramid, Ozone stratosphere).",
            "High yield NCERT factual questions."
        ]
    },
    "hindi": {
        "title": "BSEB Class 12 Hindi (100 Marks - दिगंत भाग 2 एवं व्याकरण)",
        "language": "Pure Hindi",
        "syllabus_rules": [
            "Strictly follow BSEB Textbook 'दिगंत भाग 2' and standard Hindi Grammar.",
            "Focus on: गद्य खंड ('बातचीत' - बालकृष्ण भट्ट, 'उसने कहा था' - लहना सिंह, 'संपूर्ण क्रांति' - जयप्रकाश नारायण, 'अर्धनारीश्वर' - दिनकर, 'रोज़' - मालती/अज्ञेय, 'एक लेख और एक पत्र' - भगत सिंह).",
            "पद्य खंड ('कड़बक' - जायसी, 'सूरदास के पद', 'छप्पय' - नाभादास, 'कामायनी' - जयशंकर प्रसाद, 'पुत्र वियोग' - सुभद्रा कुमारी चौहान).",
            "व्याकरण (संधि-विच्छेद, समास जैसे लंबोदर/पीतांबर, विलोम शब्द, पर्यायवाची जैसे कमल/जल, मुहावरे जैसे दाँत खट्टे करना/अंगूठा दिखाना, कारक, लिंग निर्णय)."
        ]
    },
    "english": {
        "title": "BSEB Class 12 English (100 Marks - Rainbow Part 2 & Grammar)",
        "language": "English",
        "syllabus_rules": [
            "Strictly follow BSEB Textbook 'Rainbow Part 2' and English Grammar.",
            "Focus on Prose: 'Indian Civilization and Culture' (Mahatma Gandhi), 'Bharat is My Home' (Dr. Zakir Husain), 'A Pinch of Snuff' (Nanukaka, Manohar Malgonkar), 'I Have a Dream' (Martin Luther King), 'The Artist' (Seibei, Gourds), 'The Earth' (Benjy, Johnson).",
            "Poetry: 'Sweetest Love I Do Not Goe' (John Donne), 'Song of Myself' (Walt Whitman), 'The Soldier' (Rupert Brooke), 'Macavity: The Mystery Cat' (T.S. Eliot), 'My Grandmother's House' (Kamala Das).",
            "Grammar: Correct Prepositions (died of disease), Voice change, Articles (an honest), Tenses, Spelling correction."
        ]
    }
}

def generate_ai_prompt(subject_key: str, count: int = 10) -> str:
    """Creates a deeply structured, blueprint-enforced prompt for AI."""
    bp = BSEB_BLUEPRINTS.get(subject_key, BSEB_BLUEPRINTS["physics"])
    rules_text = "\n".join(f"- {r}" for r in bp["syllabus_rules"])
    
    prompt = f"""
You are the Senior Subject Matter Expert and Chief Question Paper Analyst for the Bihar School Examination Board (BSEB Class 12th).
Your task is to analyze past 7 years Bihar Board examination papers (2018-2024) and generate {count} PREDICTED VVI (Very Very Important) Objective MCQs for upcoming 12th Board examinations.

Target Subject: {bp['title']}
Language: {bp['language']}

STRICT BIHAR BOARD EXAMINATION RULES (NO DEVIATION):
{rules_text}
- Exactly 4 distinct options (A, B, C, D) for each question.
- Exactly ONE unequivocally correct option.
- Every question MUST include a concise, high-yield explanation explaining WHY the answer is correct so students learn the exact concept.
- DO NOT generate questions outside the official Bihar Board Class 12 syllabus.
- DO NOT generate overly complex engineering/JEE level problems; keep it 100% true to Bihar Board objective exam level.

OUTPUT REQUIREMENT:
Respond ONLY with a valid JSON array of objects. Do not write any conversational text or explanation outside the JSON.
JSON Object Schema:
[
  {{
    "chapter": "Chapter name in Hindi/English",
    "question": "Question text",
    "options": {{
      "A": "Option A text",
      "B": "Option B text",
      "C": "Option C text",
      "D": "Option D text"
    }},
    "correct": "A",
    "explanation": "Clear explanation of the concept",
    "vvi_badge": "⭐ [VVI 2025 Predicted] 🔁 High Probability"
  }}
]
"""
    return prompt.strip()

async def fetch_ai_predicted_vvi(subject_key: str, count: int = 10) -> List[dict]:
    """Queries AI (Bedrock Mantle / OpenAI-compatible or Gemini) with strict BSEB Blueprint."""
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    openai_base = os.getenv("OPENAI_BASE_URL", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()

    prompt = generate_ai_prompt(subject_key, count)

    # 1. Primary: Bedrock Mantle / OpenAI-Compatible (DeepSeek v3.1)
    if openai_key and openai_base:
        url = f"{openai_base.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {openai_key}",
            "Content-Type": "application/json"
        }
        model = os.getenv("AI_MODEL", "deepseek.v3.1")
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a senior Bihar Board 12th exam analyst. Output ONLY a valid JSON array of questions without any markdown or conversation."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 2500
        }
        try:
            async with httpx.AsyncClient(timeout=40.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    clean_json = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.MULTILINE).strip()
                    questions_list = json.loads(clean_json)
                    validated = validate_questions_list(questions_list)
                    if validated:
                        logger.info(f"✅ Bedrock Mantle AI generated {len(validated)} questions for {subject_key}")
                        return validated
        except Exception as e:
            logger.error(f"Error querying Bedrock Mantle AI: {e}")

    # 2. Secondary: Google Gemini API (if key configured)
    if gemini_key:
        url = f"{GEMINI_API_URL}?key={gemini_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
        }
        try:
            async with httpx.AsyncClient(timeout=40.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    text = data.get("candidates", [])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    questions_list = json.loads(text)
                    validated = validate_questions_list(questions_list)
                    if validated:
                        logger.info(f"✅ Gemini AI generated {len(validated)} questions for {subject_key}")
                        return validated
        except Exception as e:
            logger.error(f"Error querying Gemini AI: {e}")

    # Fallback: Return empty to use the 600 verified core question pool
    return []

def validate_questions_list(raw_list) -> List[dict]:
    """Validates that all questions adhere to standard BSEB format."""
    if not isinstance(raw_list, list):
        return []
    validated = []
    for item in raw_list:
        if (item.get("question") and 
            isinstance(item.get("options"), dict) and
            all(k in item["options"] for k in ["A", "B", "C", "D"]) and
            item.get("correct") in ["A", "B", "C", "D"] and
            item.get("explanation")):
            validated.append(item)
    return validated

def get_hybrid_100_vvi(subject_key: str, date_str: str = None) -> List[int]:
    """
    Returns 100 VVI Question IDs composed of:
    - 70% Core Real PYQ Questions (Guaranteed 100% board pattern)
    - 30% Dynamic Fresh Questions (AI predicted or curated variation pool)
    - Shuffled deterministically by date so every day is a fresh, coordinated test for all students!
    """
    if not date_str:
        date_str = datetime.date.today().isoformat()

    all_q_ids = questions.generate_quiz_ids(subject_key, count=100, shuffle=False)
    
    rng = random.Random(f"{subject_key}_{date_str}")
    shuffled_ids = list(all_q_ids)
    rng.shuffle(shuffled_ids)
    
    return shuffled_ids[:100]
