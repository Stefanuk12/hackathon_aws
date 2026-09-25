"""Rank all drawings of a round against the prompt in ONE Bedrock call."""

import json
import os
import random
from pathlib import Path

import boto3
from boto3.dynamodb.conditions import Key

from ai.bedrock import bedrock, reply_text
from ai.reference import generate_references
from shared.db import META, room_pk, table

s3 = boto3.client("s3")
TEMPLATE = (Path(__file__).parent / "prompts" / "judge.txt").read_text()


def judge(prompt, images, references=()):
    """images: player drawings, references: AI reference images (both JPEG bytes).

    Returns [{drawing, rank, score, roast}] where drawing is 1-based.
    """
    content = []
    for letter, ref in zip("ABCDE", references):
        content.append({"text": f"Reference {letter} (AI example, not a player)"})
        content.append({"image": {"format": "jpeg", "source": {"bytes": ref}}})
    for i, img in enumerate(images, start=1):
        content.append({"text": f"Drawing {i}"})
        content.append({"image": {"format": "jpeg", "source": {"bytes": img}}})
    content.append({"text": "Judge now. JSON only."})

    # .replace, not .format: the template contains literal JSON braces.
    system = TEMPLATE.replace("{prompt}", prompt).replace("{n}", str(len(images)))
    resp = bedrock.converse(
        modelId=os.environ["TEXT_MODEL_ID"],
        system=[{"text": system}],
        messages=[{"role": "user", "content": content}],
        inferenceConfig={"maxTokens": 4000},
    )
    return _parse(reply_text(resp), len(images))


def _parse(text, n):
    """Pull the JSON out of Claude's reply and check every drawing got ranked.

    Raises ValueError if not; the state machine then retries the Judge step.
    """
    text = text.replace("```json", "").replace("```", "")
    results = json.loads(text[text.index("{") : text.rindex("}") + 1])["results"]

    drawings = sorted(r["drawing"] for r in results)
    if drawings != list(range(1, n + 1)):
        raise ValueError(f"Judge ranked drawings {drawings}, expected 1..{n}")

    for r in results:
        r["score"] = max(0, min(10, int(r["score"])))
    return results


def _references_or_none(prompt):
    """Reference images make judging better but aren't essential, so never fail the round over them."""
    try:
        return generate_references(prompt)
    except Exception as e:
        print("Reference generation failed, judging without:", e)
        return []


def handler(event, context):
    """Step Functions task. Input: {code, round}.

    Output: {results: [{playerId, name, rank, score, roast}], references: [url, ...]}
    """
    code, round_no = event["code"], event["round"]
    bucket = os.environ["BUCKET_NAME"]

    # One query gets the room's META, PLAYER# and ROUND# rows.
    items = table.query(KeyConditionExpression=Key("PK").eq(room_pk(code)))["Items"]
    meta = next(i for i in items if i["SK"] == META)
    names = {i["SK"].split("#", 1)[1]: i["name"] for i in items if i["SK"].startswith("PLAYER#")}
    names["ai"] = "The AI"
    entries = [i for i in items if i["SK"].startswith(f"ROUND#{round_no}#") and i.get("s3Key")]

    if not entries:
        return {"results": [], "references": []}

    # Shuffle so whoever submitted first isn't always "Drawing 1".
    random.shuffle(entries)
    images = [s3.get_object(Bucket=bucket, Key=e["s3Key"])["Body"].read() for e in entries]

    references = _references_or_none(meta["prompt"])
    reference_urls = _save_references(bucket, code, round_no, references)

    results = []
    for r in judge(meta["prompt"], images, references):
        player_id = entries[r["drawing"] - 1]["SK"].split("#", 2)[2]  # "ROUND#1#p_abc" -> "p_abc"
        results.append(
            {
                "playerId": player_id,
                "name": names.get(player_id, "Mystery artist"),
                "rank": r["rank"],
                "score": r["score"],
                "roast": r["roast"],
            }
        )
    return {"results": results, "references": reference_urls}


def _save_references(bucket, code, round_no, references):
    """Store the references so the reveal screen can show "what the AI drew". Returns presigned GET URLs."""
    urls = []
    try:
        for i, ref in enumerate(references):
            key = f"rooms/{code}/{round_no}/reference{i}.jpg"
            s3.put_object(Bucket=bucket, Key=key, Body=ref, ContentType="image/jpeg")
            urls.append(
                s3.generate_presigned_url(
                    "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=3600
                )
            )
    except Exception as e:
        print("Could not save reference images:", e)
    return urls
