"""Score a player's typed description of an AWS service, 0-10, in one Bedrock call."""

import json
import os
from pathlib import Path

from ai.bedrock import bedrock, reply_text

SYSTEM = (Path(__file__).parent / "prompts" / "text_grader.txt").read_text()


def grade(service, answer):
    """Returns {"score": 0-10, "reason": str}. Raises ValueError if the reply isn't valid JSON."""
    resp = bedrock.converse(
        modelId=os.environ["TEXT_MODEL_ID"],
        system=[{"text": SYSTEM}],
        messages=[{"role": "user", "content": [{"text": f"Service: {service}\n<answer>{answer}</answer>"}]}],
        inferenceConfig={"maxTokens": 1000},
    )
    text = reply_text(resp)
    result = json.loads(text[text.index("{") : text.rindex("}") + 1])
    return {"score": max(0, min(10, int(result["score"]))), "reason": str(result["reason"])}
