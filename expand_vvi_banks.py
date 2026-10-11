import json
import sys
from pathlib import Path
from config import DATA_DIR

# Ensure UTF-8 output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def save_json(filename, data):
    path = DATA_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Saved {len(data)} questions to {filename}")

# Run expansion
if __name__ == "__main__":
    print("Generating comprehensive 100-question VVI banks for all 12th subjects...")
