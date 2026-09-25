import random
import time

from ai.prompt_gen import generate_prompt
from shared.db import META, load_room, room_pk, table
from shared.events import publish
from shared.http import body, error, ok, room_code

ROUND_SECONDS = 60

# Used only if Bedrock is down, so the game keeps going.
FALLBACK_PROMPTS = [
    "A penguin running a lemonade stand",
    "A cat who just got fired",
    "Dracula at the dentist",
    "A snowman on a beach holiday",
    "A dog driving a bus",
    "A shark afraid of water",
]


def handler(event, context):
    code = room_code(event)
    meta, _, _ = load_room(code)
    if not meta:
        return error(f"Room {code} not found", 404)
    if meta["state"] not in ("lobby", "results"):
        return error("Round already in progress", 409)

    total = meta["totalRounds"]
    if meta["state"] == "lobby":
        try:
            total = min(10, max(1, int(body(event).get("totalRounds") or 3)))
        except (TypeError, ValueError):
            return error("totalRounds must be a number")
    if meta["round"] >= total:
        return error("Game over! Press Play again.", 409)

    used = list(meta.get("usedPrompts", []))
    try:
        prompt = generate_prompt(used)
    except Exception as e:
        print("Prompt generation failed, using a fallback:", e)
        prompt = random.choice([p for p in FALLBACK_PROMPTS if p not in used] or FALLBACK_PROMPTS)

    round_no = meta["round"] + 1
    ends_at = int(time.time() * 1000) + ROUND_SECONDS * 1000
    try:
        # The condition stops a double-click from starting two rounds.
        table.update_item(
            Key={"PK": room_pk(code), "SK": META},
            UpdateExpression=(
                "SET #s = :drawing, #r = :round, totalRounds = :total, prompt = :prompt, "
                "endsAt = :ends, usedPrompts = :used REMOVE audioUrl"
            ),
            ConditionExpression="#r = :old AND #s = :state",
            ExpressionAttributeNames={"#s": "state", "#r": "round"},
            ExpressionAttributeValues={
                ":drawing": "drawing",
                ":round": round_no,
                ":total": total,
                ":prompt": prompt,
                ":ends": ends_at,
                ":used": used + [prompt],
                ":old": meta["round"],
                ":state": meta["state"],
            },
        )
    except table.meta.client.exceptions.ConditionalCheckFailedException:
        return error("Round already in progress", 409)

    publish(code, "round_started", round=round_no, prompt=prompt, endsAt=ends_at)
    return ok({"round": round_no, "prompt": prompt, "endsAt": ends_at})
