"""Generate a round prompt with Bedrock. Plain function so start_round can import it."""

import os
from pathlib import Path

import boto3

bedrock = boto3.client("bedrock-runtime")
PROMPTS = Path(__file__).parent / "prompts"
MODES = ("draw", "survive", "wit")


def generate_prompt(mode="draw", previous_prompts=()):
    """mode: "draw" | "survive" | "wit" (the round's mode, never "mixed")."""
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}")
    system = (PROMPTS / f"prompt_gen_{mode}.txt").read_text()
    # TODO person 4: tune temperature / theme; add difficulty if time allows.
    resp = bedrock.converse(
        modelId=os.environ["TEXT_MODEL_ID"],
        system=[{"text": system}],
        messages=[
            {
                "role": "user",
                "content": [{"text": f"Previous prompts: {list(previous_prompts)}"}],
            }
        ],
        inferenceConfig={"maxTokens": 80, "temperature": 1.0},
    )
    return resp["output"]["message"]["content"][0]["text"].strip().strip('"')
