"""Generate a round prompt with Bedrock. Plain function so start_round can import it."""

import os
from pathlib import Path

import boto3

bedrock = boto3.client("bedrock-runtime")
SYSTEM = (Path(__file__).parent / "prompts" / "prompt_gen.txt").read_text()


def generate_prompt(previous_prompts=()):
    # TODO person 4: tune temperature / theme; add difficulty if time allows.
    resp = bedrock.converse(
        modelId=os.environ["TEXT_MODEL_ID"],
        system=[{"text": SYSTEM}],
        messages=[
            {
                "role": "user",
                "content": [{"text": f"Previous prompts: {list(previous_prompts)}"}],
            }
        ],
        inferenceConfig={"maxTokens": 50, "temperature": 1.0},
    )
    return resp["output"]["message"]["content"][0]["text"].strip().strip('"')
