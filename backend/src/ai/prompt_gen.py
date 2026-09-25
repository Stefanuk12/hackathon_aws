"""Generate a round prompt with Bedrock. Plain function so start_round can import it."""

import os
from pathlib import Path

from ai.bedrock import bedrock, reply_text

SYSTEM = (Path(__file__).parent / "prompts" / "prompt_gen.txt").read_text()


def generate_prompt(previous_prompts=(), theme=None):
    """Returns one short, drawable prompt that isn't in previous_prompts."""
    text = f"Previous prompts: {list(previous_prompts)}"
    if theme:
        text += f"\nTheme: {theme}"

    resp = bedrock.converse(
        modelId=os.environ["TEXT_MODEL_ID"],
        system=[{"text": SYSTEM}],
        messages=[{"role": "user", "content": [{"text": text}]}],
        inferenceConfig={"maxTokens": 1000},
    )
    return reply_text(resp).strip().strip('"').strip()
