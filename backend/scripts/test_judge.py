"""Run the judge locally on the drawings in samples/ (or another folder).

Usage:
  python scripts/test_judge.py "A penguin running a lemonade stand"
  python scripts/test_judge.py "A penguin running a lemonade stand" --no-refs
  python scripts/test_judge.py "..." --samples /path/to/folder
Needs TEXT_MODEL_ID and AWS_REGION set.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai.judge import judge  # noqa: E402
from ai.reference import generate_references  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("prompt", nargs="?", default="A penguin running a lemonade stand")
parser.add_argument("--no-refs", action="store_true", help="judge without AI reference images")
parser.add_argument("--samples", default=str(ROOT.parent / "samples"), help="folder of .jpg drawings")
args = parser.parse_args()

samples = sorted(Path(args.samples).glob("*.jpg"))
if not samples:
    sys.exit(f"Put some .jpg drawings in {args.samples} first.")

refs = [] if args.no_refs else generate_references(args.prompt)
for i, ref in enumerate(refs):
    (ROOT / f"reference{i}.jpg").write_bytes(ref)
if refs:
    print(f"Saved {len(refs)} reference images to backend/reference*.jpg")

results = judge(args.prompt, [p.read_bytes() for p in samples], refs)
for r in sorted(results, key=lambda r: r["rank"]):
    print(f"#{r['rank']} {samples[r['drawing'] - 1].name} ({r['score']}/10): {r['roast']}")
print(json.dumps(results, indent=2))
