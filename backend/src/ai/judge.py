"""Rank all drawings of a round against the prompt in ONE Bedrock call."""

import json
import os
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ai.bedrock import bedrock, reply_text
from ai.reference import generate_references, image_format
from shared import storage
from shared.db import load_room, round_entries

TEMPLATE = (Path(__file__).parent / "prompts" / "judge.txt").read_text()


def judge(prompt, images, references=()):
    """images: player drawings, references: AI reference images (JPEG or PNG bytes).

    Returns [{drawing, rank, score, roast}] where drawing is 1-based.
    """
    content = []
    for letter, ref in zip("ABCDE", references):
        content.append({"text": f"Reference {letter} (AI example, not a player)"})
        content.append({"image": {"format": image_format(ref), "source": {"bytes": ref}}})
    for i, img in enumerate(images, start=1):
        content.append({"text": f"Drawing {i}"})
        content.append({"image": {"format": image_format(img), "source": {"bytes": img}}})
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
    meta, players, entries = load_room(code)
    names = {pid: p["name"] for pid, p in players.items()}
    names["ai"] = "The AI"
    entries = [(pid, e) for pid, e in round_entries(entries, round_no).items() if e.get("s3Key")]

    if not entries:
        return {"results": [], "references": []}

    # Shuffle so whoever submitted first isn't always "Drawing 1".
    random.shuffle(entries)
    # References take a few seconds; download the drawings while they generate.
    with ThreadPoolExecutor(max_workers=8) as pool:
        refs_future = pool.submit(_references_or_none, meta["prompt"])
        images = list(pool.map(lambda e: storage.get(e[1]["s3Key"]), entries))
        references = refs_future.result()
    reference_urls = _save_references(code, round_no, references)

    results = []
    for r in judge(meta["prompt"], images, references):
        player_id = entries[r["drawing"] - 1][0]
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


def _save_references(code, round_no, references):
    """Store the references so the reveal screen can show "what the AI drew". Returns presigned GET URLs."""
    urls = []
    try:
        for i, ref in enumerate(references):
            fmt = image_format(ref)
            key = f"rooms/{code}/{round_no}/reference{i}.{'png' if fmt == 'png' else 'jpg'}"
            storage.put(key, ref, f"image/{fmt}")
            urls.append(storage.presign_get(key))
    except Exception as e:
        print("Could not save reference images:", e)
    return urls
