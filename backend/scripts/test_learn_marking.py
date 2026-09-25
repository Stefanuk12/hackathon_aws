"""Check the Learn round marks fairly, against real Bedrock.

Unlike test_rooms.py (which fakes the model), this calls Bedrock for real, so it costs a
few pennies and needs working credentials. Run it after changing prompts/judge_learn.txt.

    python scripts/test_learn_marking.py
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("TEXT_REGION", "us-west-2")
os.environ.setdefault("TEXT_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai.judge import judge_text  # noqa: E402

QUESTION = "What triggers an AWS Lambda function to start running your code?"
# The second one is the trap: true about S3, but it doesn't answer the question asked.
ANSWERS = [
    "An event, like an HTTP request through API Gateway, a file landing in S3, or a message on a queue",
    "It stores objects in buckets and you fetch them over HTTPS with a URL",
    "Something happens and then it runs I think",
    "A type of sandwich",
]
LABELS = ["correct", "true-but-wrong-service", "vague-but-relevant", "nonsense"]


def main():
    res = {r["answer"]: r for r in judge_text("learn", QUESTION, ANSWERS)}
    for i, label in enumerate(LABELS, start=1):
        r = res[i]
        print(f"  {label:24} {r['score']:>2}/10 (rank {r['rank']})  {r['roast'][:90]}")

    correct, wrong_service, vague, nonsense = (res[i]["score"] for i in (1, 2, 3, 4))
    checks = [
        ("correct beats the wrong-service answer", correct > wrong_service),
        ("a true answer to a different question scores <= 2", wrong_service <= 2),
        ("nonsense scores 0", nonsense == 0),
        ("vague sits between nonsense and correct", nonsense <= vague <= correct),
        ("every rank is different", len({r["rank"] for r in res.values()}) == len(ANSWERS)),
        ("feedback teaches the right answer", all("Lambda" in r["roast"] for r in res.values())),
    ]
    for label, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'} {label}")
    return all(ok for _, ok in checks)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
