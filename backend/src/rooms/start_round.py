import random
import time

from ai.prompt_gen import generate_prompt
from shared.db import META, load_room, room_pk, table
from shared.events import publish
from shared.http import body, error, ok, room_code
from shared.themes import INTRO_SECONDS, is_themed, pick_theme, prompt_theme, public

ROUND_SECONDS = 60

MODES = ("draw", "survive", "wit")
# "mixed" cycles these, so a 3-round game shows all three.
MIXED_ORDER = ("draw", "survive", "wit")

# Used only if Bedrock is down, so the game keeps going.
FALLBACK_PROMPTS = {
    "draw": [
        "A penguin running a lemonade stand",
        "A cat who just got fired",
        "Dracula at the dentist",
        "A snowman on a beach holiday",
        "A dog driving a bus",
        "A shark afraid of water",
    ],
    "survive": [
        "You wake up in a lift with a hungry bear.",
        "The floor is lava and you're wearing socks.",
        "Zombies burst into your 9am lecture.",
        "A goose has declared war on you personally.",
    ],
    "wit": [
        "The worst thing to say in a job interview",
        "A terrible name for a pet goldfish",
        "The most useless superpower",
        "A rejected AWS service name",
    ],
}


def _settings(meta, req):
    """Lobby settings from the request; later rounds keep what the room already has.

    Returns (settings dict, error response or None).
    """
    # .get with defaults so a room created before these settings existed still starts.
    defaults = {"totalRounds": 3, "mode": "mixed", "elimination": False, "reviveAfter": 2, "themeEvery": 2}
    current = {k: meta.get(k, d) for k, d in defaults.items()}
    if meta["state"] != "lobby":
        return current, None

    try:
        if req.get("totalRounds") is not None:
            current["totalRounds"] = min(10, max(1, int(req["totalRounds"])))
        if req.get("reviveAfter") is not None:
            current["reviveAfter"] = min(5, max(1, int(req["reviveAfter"])))
        if req.get("themeEvery") is not None:
            current["themeEvery"] = min(10, max(0, int(req["themeEvery"])))
    except (TypeError, ValueError):
        return current, error("Round settings must be numbers")

    if req.get("mode") is not None:
        if req["mode"] not in MODES + ("mixed",):
            return current, error(f"mode must be one of: mixed, {', '.join(MODES)}")
        current["mode"] = req["mode"]
    if req.get("elimination") is not None:
        current["elimination"] = bool(req["elimination"])
    return current, None


def _new_prompt(mode, used, theme):
    """Ask Bedrock for a prompt in this mode (and theme); fall back to a canned one if it's down."""
    try:
        return generate_prompt(used, theme=prompt_theme(theme, mode) if theme else None, mode=mode)
    except Exception as e:
        print("Prompt generation failed, using a fallback:", e)
        options = FALLBACK_PROMPTS[mode]
        return random.choice([p for p in options if p not in used] or options)


def handler(event, context):
    code = room_code(event)
    meta, _, _ = load_room(code)
    if not meta:
        return error(f"Room {code} not found", 404)
    if meta["state"] not in ("lobby", "results"):
        return error("Round already in progress", 409)

    settings, bad = _settings(meta, body(event))
    if bad:
        return bad
    if meta["round"] >= settings["totalRounds"]:
        return error("Game over! Press Play again.", 409)

    round_no = int(meta["round"]) + 1
    mode = settings["mode"]
    round_mode = MIXED_ORDER[(round_no - 1) % len(MIXED_ORDER)] if mode == "mixed" else mode

    used_prompts = list(meta.get("usedPrompts", []))
    used_themes = list(meta.get("usedThemes", []))
    theme = pick_theme(used_themes) if is_themed(round_no, settings["themeEvery"]) else None
    prompt = _new_prompt(round_mode, used_prompts, theme)

    now = int(time.time() * 1000)
    # A themed round opens with the AWS intro; begin_round starts the drawing/typing after it.
    if theme:
        state, timings = "theme", {"themeEndsAt": now + INTRO_SECONDS * 1000}
        used_themes.append(theme["id"])
    else:
        state, timings = "drawing", {"endsAt": now + ROUND_SECONDS * 1000}

    values = {
        ":state": state,
        ":round": round_no,
        ":prompt": prompt,
        ":roundMode": round_mode,
        ":usedPrompts": used_prompts + [prompt],
        ":usedThemes": used_themes,
        ":theme": public(theme) if theme else None,
        **{f":{k}": v for k, v in settings.items()},
        **{f":{k}": v for k, v in timings.items()},
    }
    # Whichever of endsAt / themeEndsAt this round doesn't use must go, or the screens
    # would still see the previous round's deadline.
    stale = "endsAt" if theme else "themeEndsAt"
    try:
        # The condition stops a double-click from starting two rounds.
        table.update_item(
            Key={"PK": room_pk(code), "SK": META},
            UpdateExpression=(
                "SET #s = :state, #r = :round, prompt = :prompt, roundMode = :roundMode, #th = :theme, "
                "totalRounds = :totalRounds, #md = :mode, elimination = :elimination, reviveAfter = :reviveAfter, "
                "themeEvery = :themeEvery, usedPrompts = :usedPrompts, usedThemes = :usedThemes, "
                + ", ".join(f"{k} = :{k}" for k in timings)
                + f" REMOVE {stale}, outcome, audioUrl, hostScript, referenceUrls"
            ),
            ConditionExpression="#r = :old AND #s = :oldState",
            ExpressionAttributeNames={"#s": "state", "#r": "round", "#md": "mode", "#th": "theme"},
            ExpressionAttributeValues={**values, ":old": meta["round"], ":oldState": meta["state"]},
        )
    except table.meta.client.exceptions.ConditionalCheckFailedException:
        return error("Round already in progress", 409)

    if theme:
        publish(code, "theme_intro", round=round_no, roundMode=round_mode, theme=public(theme), themeEndsAt=timings["themeEndsAt"])
    else:
        publish(code, "round_started", round=round_no, roundMode=round_mode, prompt=prompt, endsAt=timings["endsAt"])
    return ok({"round": round_no, "prompt": prompt, "endsAt": timings.get("endsAt", timings.get("themeEndsAt"))})
