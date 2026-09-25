"""Generate a round prompt with Bedrock. Plain function so start_round can import it."""

import os
from pathlib import Path

from ai.bedrock import bedrock, reply_text

PROMPTS = Path(__file__).parent / "prompts"
# Draw keeps the original prompt_gen.txt; text modes have their own templates.
SYSTEM = {
    "draw": (PROMPTS / "prompt_gen.txt").read_text(),
    "survive": (PROMPTS / "prompt_gen_survive.txt").read_text(),
    "wit": (PROMPTS / "prompt_gen_wit.txt").read_text(),
}


def generate_prompt(previous_prompts=(), theme=None, mode="draw"):
    """Returns one short prompt for the round's mode ("draw" | "survive" | "wit") that isn't in previous_prompts."""
    text = f"Previous prompts: {list(previous_prompts)}"
    if theme:
        text += f"\nTheme: {theme}"

    resp = bedrock.converse(
        modelId=os.environ["TEXT_MODEL_ID"],
        system=[{"text": SYSTEM[mode]}],
        messages=[{"role": "user", "content": [{"text": text}]}],
        inferenceConfig={"maxTokens": 1000},
    )
    return reply_text(resp).strip().strip('"').strip()
