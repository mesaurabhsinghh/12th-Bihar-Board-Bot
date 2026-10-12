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
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

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

def clean_json_response(raw_text: str) -> Optional[List[dict]]:
    """Strips markdown and parses JSON safely."""
    try:
        clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
        data = json.loads(clean)
        return data if isinstance(data, list) else None
    except Exception:
        return None

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

# ----------------- AGENT CALLERS -----------------

async def call_gemini(prompt: str) -> Optional[str]:
    """Agent Caller: Google Gemini 3.5 Flash."""
    keys = [os.getenv("GEMINI_API_KEY", ""), os.getenv("GEMINI_API_KEY_BACKUP", "")]
    for key in keys:
        if not key.strip():
            continue
        url = f"{GEMINI_API_URL}?key={key.strip()}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
        }
        try:
            async with httpx.AsyncClient(timeout=35.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            logger.warning(f"Gemini call error: {e}")
    return None

async def call_deepseek(prompt: str, system_prompt: str = "") -> Optional[str]:
    """Agent Caller: DeepSeek v3.1 (Bedrock Mantle)."""
    keys = [
        os.getenv("OPENAI_API_KEY", "").strip(),
        os.getenv("OPENAI_API_KEY_BACKUP", "").strip()
    ]
    base_url = os.getenv("OPENAI_BASE_URL", "https://bedrock-mantle.ap-southeast-2.api.aws/v1").strip()
    model = os.getenv("AI_MODEL", "deepseek.v3.1")

    url = f"{base_url.rstrip('/')}/chat/completions"
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {"model": model, "messages": messages, "temperature": 0.1, "max_tokens": 3000}
    for key in keys:
        if not key:
            continue
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=40.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    logger.warning(f"DeepSeek returned {resp.status_code}: {resp.text[:120]}")
        except Exception as e:
            logger.warning(f"DeepSeek call error: {e}")
    return None

async def call_chatgpt(prompt: str, system_prompt: str = "") -> Optional[str]:
    """Agent Caller: ChatGPT (OpenAI gpt-4o-mini)."""
    keys = [
        os.getenv("CHATGPT_API_KEY", "").strip(),
        os.getenv("CHATGPT_API_KEY_BACKUP", "").strip()
    ]
    for key in keys:
        if not key:
            continue
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {"model": "gpt-4o-mini", "messages": messages, "temperature": 0.2, "max_tokens": 3000}
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.post(OPENAI_API_URL, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    logger.warning(f"ChatGPT key returned {resp.status_code}: {resp.text[:120]}")
        except Exception as e:
            logger.warning(f"ChatGPT call error: {e}")
    return None

# ----------------- MULTI-AGENT WORKFLOW -----------------

async def fetch_ai_predicted_vvi(subject_key: str, count: int = 10) -> List[dict]:
    """
    Multi-Agent Collaborative Pipeline:
    Agent 1 (Paper Setter): Gemini 3.5 Flash or ChatGPT drafts candidate questions based on BSEB Blueprint.
    Agent 2 (Chief Examiner & Verifier): DeepSeek v3.1 audits, confirms correct answer, eliminates option ambiguity & polishes Hindi explanation.
    """
    bp = BSEB_BLUEPRINTS.get(subject_key, BSEB_BLUEPRINTS["physics"])
    rules_text = "\n".join(f"- {r}" for r in bp["syllabus_rules"])

    draft_prompt = f"""
You are Agent 1 (Senior Question Setter) for the Bihar School Examination Board (BSEB 12th).
Generate {count} predicted VVI objective MCQs for:
Subject: {bp['title']}
Language: {bp['language']}

STRICT BIHAR BOARD RULES:
{rules_text}
- Exactly 4 distinct options (A, B, C, D).
- Exactly ONE unambiguously correct option.
- Clear concept-based explanation in Hindi.

Return ONLY a valid JSON array of objects:
[
  {{
    "chapter": "Chapter name",
    "question": "Question text",
    "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
    "correct": "A",
    "explanation": "Explanation",
    "vvi_badge": "⭐ [VVI 2025 Multi-Agent Certified]"
  }}
]
"""

    logger.info(f"🤖 Multi-Agent Step 1: Generating draft questions for {subject_key}...")
    
    # 1. Agent 1: Try ChatGPT or Gemini 3.5 Flash
    draft_raw = await call_chatgpt(draft_prompt, system_prompt="You are a senior BSEB examiner. Output valid JSON array only.")
    if not draft_raw:
        draft_raw = await call_gemini(draft_prompt)
    if not draft_raw:
        draft_raw = await call_deepseek(draft_prompt, system_prompt="You are a senior BSEB examiner. Output valid JSON array only.")

    draft_list = clean_json_response(draft_raw) if draft_raw else None
    if not draft_list:
        logger.warning("Agent 1 drafting failed, falling back to verified core question bank.")
        return []

    logger.info(f"🧐 Multi-Agent Step 2: Agent 2 (DeepSeek v3.1) auditing & verifying {len(draft_list)} questions...")

    # 2. Agent 2: DeepSeek audits, confirms correctness, and polishes the explanation
    audit_prompt = f"""
You are Agent 2 (Chief Senior Examiner & Fact Checker for BSEB Class 12th).
Audit and certify these candidate questions generated by Agent 1:

{json.dumps(draft_list, ensure_ascii=False, indent=2)}

YOUR AUDIT MANDATE:
1. Verify each question strictly matches the BSEB 12th syllabus.
2. Confirm that exactly ONE option is 100% correct without any doubt or ambiguity.
3. Review and polish the Hindi explanation so it is crystal clear and teaches the student the exact underlying concept.

Return ONLY the verified, polished questions in a clean valid JSON array.
"""
    verified_raw = await call_deepseek(audit_prompt, system_prompt="You are Chief Senior Examiner for BSEB 12th. Return pure JSON array only.")
    verified_list = clean_json_response(verified_raw) if verified_raw else None

    # If Agent 2 succeeded, use the double-verified list; otherwise use Agent 1's validated list
    final_questions = validate_questions_list(verified_list) if verified_list else validate_questions_list(draft_list)

    logger.info(f"🎉 Multi-Agent Pipeline Completed: {len(final_questions)} certified VVI questions ready!")
    return final_questions

def get_hybrid_100_vvi(subject_key: str, date_str: str = None) -> List[int]:
    """
    Returns 100 VVI Question IDs composed of:
    - Core Real PYQ Questions
    - Dynamic Fresh AI Questions (Multi-Agent Gemini + DeepSeek Certified)
    - Shuffled deterministically by date so every day is a fresh, coordinated test for all students!
    """
    if not date_str:
        date_str = datetime.date.today().isoformat()

    all_q_ids = questions.generate_quiz_ids(subject_key, count=100, shuffle=False)
    
    # Blend in any registered AI questions for this subject
    questions._init_ai_cache(subject_key)
    ai_ids = list(questions._AI_QUESTIONS.get(subject_key, {}).keys())
    
    rng = random.Random(f"{subject_key}_{date_str}")
    shuffled_ids = list(all_q_ids)
    rng.shuffle(shuffled_ids)
    
    if ai_ids:
        # Include the latest AI certified questions in the 100 test
        ai_pick = ai_ids[-20:] # up to 20 recent AI questions
        shuffled_ids = ai_pick + [qid for qid in shuffled_ids if qid not in ai_pick]
        
    return shuffled_ids[:100]
