import json
import os
import sys
from pathlib import Path

# Ensure UTF-8 output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DATA_DIR = Path(__file__).resolve().parent / "data"

def create_bank(filename, questions):
    path = DATA_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    print(f"✅ Generated {len(questions)} VVI questions for {filename}")

