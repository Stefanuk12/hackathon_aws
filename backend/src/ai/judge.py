"""Rank all entries of a round against the prompt in ONE Bedrock call.

Draw rounds are judged on images (with AI reference drawings); Survive and Quick Wit rounds on text.
"""

import json
import os
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ai.bedrock import bedrock, reply_text
from ai.reference import generate_references, image_format
from shared import storage
from shared.db import load_room, round_entries

PROMPTS = Path(__file__).parent / "prompts"
TEMPLATE = (PROMPTS / "judge.txt").read_text()
TEXT_TEMPLATES = {m: (PROMPTS / f"judge_{m}.txt").read_text() for m in ("survive", "wit")}


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


def judge_text(mode, prompt, answers):
    """Survive / Quick Wit rounds. answers: list of strings.

    Returns [{answer, rank, score, roast}] where answer is 1-based, plus "survived" for mode "survive".
    """
    listing = "\n".join(f'Answer {i}: "{a or "(no answer)"}"' for i, a in enumerate(answers, start=1))
    system = TEXT_TEMPLATES[mode].replace("{prompt}", prompt).replace("{n}", str(len(answers)))
    resp = bedrock.converse(
        modelId=os.environ["TEXT_MODEL_ID"],
        system=[{"text": system}],
        messages=[{"role": "user", "content": [{"text": f"{listing}\n\nJudge now. JSON only."}]}],
        inferenceConfig={"maxTokens": 4000},
    )
    results = _parse(reply_text(resp), len(answers), key="answer")
    if mode == "survive":
        for r in results:
            r["survived"] = bool(r.get("survived", r["score"] >= 6))
    return results


def _parse(text, n, key="drawing"):
    """Pull the JSON out of Claude's reply and check every entry got ranked.

    Raises ValueError if not; the state machine then retries the Judge step.
    """
    text = text.replace("```json", "").replace("```", "")
    results = json.loads(text[text.index("{") : text.rindex("}") + 1])["results"]

    numbers = sorted(r[key] for r in results)
    if numbers != list(range(1, n + 1)):
        raise ValueError(f"Judge ranked {key}s {numbers}, expected 1..{n}")

    for r in results:
        r["score"] = max(0, min(10, int(r["score"])))
    # The model sometimes repeats a rank; renumber 1..n in its order so there's one winner.
    for rank, r in enumerate(sorted(results, key=lambda r: r["rank"]), start=1):
        r["rank"] = rank
    return results


MAX_IMAGE_BYTES = 3_750_000  # Bedrock's per-image limit


def _fetch(key):
    """Drawing bytes, or None if missing, too big or not an image, so one bad upload can't sink the round."""
    try:
        data = storage.get(key)
    except Exception as e:
        print(f"Skipping {key}:", e)
        return None
    is_image = data[:3] == b"\xff\xd8\xff" or data[:4] == b"\x89PNG"
    if not is_image or len(data) > MAX_IMAGE_BYTES:
        print(f"Skipping {key}: not a JPEG/PNG or over {MAX_IMAGE_BYTES} bytes")
        return None
    return data


def _references_or_none(prompt):
    """Reference images make judging better but aren't essential, so never fail the round over them."""
    try:
        return generate_references(prompt)
    except Exception as e:
        print("Reference generation failed, judging without:", e)
        return []


def handler(event, context):
    """Step Functions task. Input: {code, round}.

    Output: {results: [{playerId, name, rank, score, roast, survived?}], references: [url, ...]}
    """
    code, round_no = event["code"], event["round"]
    meta, players, entries = load_room(code)
    names = {pid: p["name"] for pid, p in players.items()}
    names["ai"] = "The AI"
    mode = meta.get("roundMode", "draw")
    if mode != "draw":
        return _handle_text_round(mode, meta, entries, names, round_no)

    entries = [(pid, e) for pid, e in round_entries(entries, round_no).items() if e.get("s3Key")]

    if not entries:
        return {"results": [], "references": []}

    # Shuffle so whoever submitted first isn't always "Drawing 1".
    random.shuffle(entries)
    # References take a few seconds; download the drawings while they generate.
    with ThreadPoolExecutor(max_workers=8) as pool:
        refs_future = pool.submit(_references_or_none, meta["prompt"])
        images = list(pool.map(lambda e: _fetch(e[1]["s3Key"]), entries))
        references = refs_future.result()

    kept = [(e, img) for e, img in zip(entries, images) if img]
    if not kept:
        return {"results": [], "references": []}
    entries, images = map(list, zip(*kept))
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


def _handle_text_round(mode, meta, entries, names, round_no):
    """Survive / Quick Wit: entries carry "text" instead of "s3Key", and there are no reference images."""
    entries = [(pid, e) for pid, e in round_entries(entries, round_no).items() if "text" in e]
    if not entries:
        return {"results": [], "references": []}

    random.shuffle(entries)
    results = []
    for r in judge_text(mode, meta["prompt"], [e[1]["text"] for e in entries]):
        player_id = entries[r["answer"] - 1][0]
        result = {
            "playerId": player_id,
            "name": names.get(player_id, "Mystery player"),
            "rank": r["rank"],
            "score": r["score"],
            "roast": r["roast"],
        }
        if "survived" in r:
            result["survived"] = r["survived"]
        results.append(result)
    return {"results": results, "references": []}
