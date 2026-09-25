"""Rank all drawings of a round against the prompt in ONE Bedrock call."""

import json
import os
from pathlib import Path

import boto3

bedrock = boto3.client("bedrock-runtime")
TEMPLATE = (Path(__file__).parent / "prompts" / "judge.txt").read_text()


def judge(prompt, images):
    """images: list of JPEG bytes. Returns [{drawing, rank, score, roast}] (drawing is 1-based)."""
    content = []
    for i, img in enumerate(images, start=1):
        content.append({"text": f"Drawing {i}"})
        content.append({"image": {"format": "jpeg", "source": {"bytes": img}}})
    content.append({"text": "Judge now. JSON only."})

    resp = bedrock.converse(
        modelId=os.environ["TEXT_MODEL_ID"],
        system=[{"text": TEMPLATE.format(prompt=prompt, n=len(images))}],
        messages=[{"role": "user", "content": content}],
        inferenceConfig={"maxTokens": 1500, "temperature": 0.7},
    )
    text = resp["output"]["message"]["content"][0]["text"]
    # TODO person 4: harden parsing (strip ``` fences, validate every drawing is ranked).
    return json.loads(text[text.index("{") : text.rindex("}") + 1])["results"]


def handler(event, context):
    """Step Functions task. Input: {code, round}. Output: {results: [{playerId, rank, score, roast}]}.

    TODO person 4: load prompt + ROUND#<n># entries from DynamoDB, fetch each s3Key,
    call judge(), map drawing numbers back to playerIds.
    """
    return {"results": []}
