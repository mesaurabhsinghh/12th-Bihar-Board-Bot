import json
import sys
from pathlib import Path
from config import DATA_DIR, SUBJECTS

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def validate_all_subjects():
    print("🔍 बिहार बोर्ड 12th प्रश्न बैंक सत्यापन (Validating Question Bank)...")
    total_q_count = 0
    errors_found = False

    for sub_key, sub_info in SUBJECTS.items():
        file_path = DATA_DIR / sub_info["file"]
        if not file_path.exists():
            print(f"❌ [फ़ाइल नहीं मिली] {sub_info['file']} मौजूद नहीं है!")
            errors_found = True
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"❌ [JSON त्रुटि] {sub_info['file']} में त्रुटि है: {e}")
            errors_found = True
            continue

        if not isinstance(data, list):
            print(f"❌ {sub_info['file']} एक List/Array होनी चाहिए!")
            errors_found = True
            continue

        seen_ids = set()
        sub_errors = 0

        for idx, item in enumerate(data, 1):
            q_id = item.get("id")
            if not q_id or q_id in seen_ids:
                print(f"  ⚠️ {sub_key} प्रश्न #{idx}: अमान्य या दोहराई गई id: {q_id}")
                sub_errors += 1
            seen_ids.add(q_id)

            if not item.get("question"):
                print(f"  ⚠️ {sub_key} ID {q_id}: प्रश्न वाक्य (question) खाली है!")
                sub_errors += 1

            options = item.get("options", {})
            if not isinstance(options, dict) or not all(k in options for k in ["A", "B", "C", "D"]):
                print(f"  ⚠️ {sub_key} ID {q_id}: ऑप्शंस A, B, C, D पूरे नहीं हैं!")
                sub_errors += 1

            correct = item.get("correct", "").strip().upper()
            if correct not in ["A", "B", "C", "D"]:
                print(f"  ⚠️ {sub_key} ID {q_id}: सही उत्तर ('correct') A, B, C, D में से होना चाहिए, मिला: {correct}")
                sub_errors += 1

            if not item.get("explanation"):
                print(f"  ℹ️ {sub_key} ID {q_id}: व्याख्या (explanation) खाली है।")

        if sub_errors == 0:
            print(f"✅ {sub_info['emoji']} {sub_info['title']} ({sub_info['file']}): {len(data)} प्रश्न सही हैं।")
        else:
            errors_found = True
            print(f"❌ {sub_info['title']} में {sub_errors} त्रुटियाँ मिलीं!")

        total_q_count += len(data)

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    if not errors_found:
        print(f"🎉 सभी विषय सत्यापित हैं! कुल प्रश्न संख्या: {total_q_count}")
    else:
        print("⚠️ कुछ त्रुटियाँ मिलीं, कृपया सुधारें।")

if __name__ == "__main__":
    validate_all_subjects()
