"""Rank all entries of a round against the prompt in ONE Bedrock call."""

import json
import os
from pathlib import Path

import boto3

bedrock = boto3.client("bedrock-runtime")
PROMPTS = Path(__file__).parent / "prompts"


def _converse(system, content, max_tokens=1500):
    resp = bedrock.converse(
        modelId=os.environ["TEXT_MODEL_ID"],
        system=[{"text": system}],
        messages=[{"role": "user", "content": content}],
        inferenceConfig={"maxTokens": max_tokens, "temperature": 0.7},
    )
    text = resp["output"]["message"]["content"][0]["text"]
    # TODO person 4: harden parsing (strip ``` fences, validate every entry is ranked).
    return json.loads(text[text.index("{") : text.rindex("}") + 1])["results"]


def judge(prompt, images):
    """Draw rounds. images: list of JPEG bytes.
    Returns [{drawing, rank, score, roast}] (drawing is 1-based)."""
    content = []
    for i, img in enumerate(images, start=1):
        content.append({"text": f"Drawing {i}"})
        content.append({"image": {"format": "jpeg", "source": {"bytes": img}}})
    content.append({"text": "Judge now. JSON only."})
    system = (PROMPTS / "judge_draw.txt").read_text().format(prompt=prompt, n=len(images))
    return _converse(system, content)


def judge_text(mode, prompt, answers):
    """Survive / Quick Wit rounds. answers: list of strings.
    Returns [{answer, rank, score, roast}] (answer is 1-based), plus "survived" for mode "survive"."""
    listing = "\n".join(f'Answer {i}: "{a or "(no answer)"}"' for i, a in enumerate(answers, start=1))
    system = (PROMPTS / f"judge_{mode}.txt").read_text().format(prompt=prompt, n=len(answers))
    return _converse(system, [{"text": f"{listing}\n\nJudge now. JSON only."}])


def handler(event, context):
    """Step Functions task. Input: {code, round}.
    Output: {results: [{playerId, rank, score, roast, survived?}]}.

    TODO person 4: load META (prompt, roundMode) + ROUND#<n># entries from DynamoDB.
      - roundMode "draw": fetch each s3Key from S3, call judge(prompt, images).
      - "survive" / "wit": call judge_text(roundMode, prompt, [entry["text"], ...]).
    Map the 1-based drawing/answer numbers back to playerIds.
    """
    return {"results": []}
