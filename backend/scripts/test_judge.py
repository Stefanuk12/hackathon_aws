"""Run the judge locally against ../../samples/*.jpg without deploying.

Usage (from backend/):
    TEXT_MODEL_ID=<model id> AWS_REGION=eu-west-2 python scripts/test_judge.py "A penguin running a lemonade stand"
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai.judge import judge  # noqa: E402

samples = sorted((ROOT.parent / "samples").glob("*.jpg"))
if not samples:
    sys.exit("Put some .jpg drawings in samples/ first.")

prompt = sys.argv[1] if len(sys.argv) > 1 else "A penguin running a lemonade stand"
results = judge(prompt, [p.read_bytes() for p in samples])
for r in sorted(results, key=lambda r: r["rank"]):
    print(f"#{r['rank']} {samples[r['drawing'] - 1].name} ({r['score']}/10): {r['roast']}")
print(json.dumps(results, indent=2))
