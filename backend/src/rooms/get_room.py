from shared.db import load_room, round_entries
from shared.http import error, ok, room_code


def handler(event, context):
    code = room_code(event)
    meta, players, entries = load_room(code)
    if not meta:
        return error(f"Room {code} not found", 404)

    # A player's score is the sum of their judged entries, so there's no running total to keep in sync.
    # "points" is what the round actually awarded: the score, or half of it while eliminated.
    scores = {}
    for e in entries:
        pid = e["SK"].split("#", 2)[2]
        scores[pid] = scores.get(pid, 0) + e.get("points", e.get("score", 0))

    elimination = bool(meta.get("elimination", False))
    this_round = round_entries(entries, meta["round"])
    room = {
        "code": code,
        "state": meta["state"],
        "round": meta["round"],
        "totalRounds": meta["totalRounds"],
        "mode": meta.get("mode", "mixed"),
        "roundMode": meta.get("roundMode"),
        "elimination": elimination,
        "reviveAfter": meta.get("reviveAfter", 2),
        "themeEvery": meta.get("themeEvery", 2),
        "theme": meta.get("theme"),
        "themeEndsAt": meta.get("themeEndsAt"),
        "prompt": meta.get("prompt"),
        "endsAt": meta.get("endsAt"),
        "players": [
            {
                "playerId": pid,
                "name": p["name"],
                "score": scores.get(pid, 0),
                "submitted": pid in this_round,
                # Only sent when elimination is on, so the screens can't show ghosts by accident.
                **({"alive": bool(p.get("alive", True)), "streak": p.get("streak", 0)} if elimination else {}),
            }
            for pid, p in players.items()
        ],
        "audioUrl": meta.get("audioUrl"),
        "hostScript": meta.get("hostScript"),  # read aloud with speechSynthesis if audioUrl is null
        "references": meta.get("referenceUrls", []),  # "what the AI drew" images for the reveal
    }
    if meta["state"] == "results":
        judged = sorted((e for e in this_round.items() if "rank" in e[1]), key=lambda e: e[1]["rank"])
        room["results"] = [
            {
                "playerId": pid,
                "name": players[pid]["name"] if pid in players else "The AI",
                "rank": e["rank"],
                "score": e["score"],
                "points": e.get("points", e["score"]),
                "roast": e["roast"],
                # Drawing rounds carry an image; Survive / Quick Wit carry the typed answer.
                **({"imageUrl": e.get("imageUrl", "")} if "s3Key" in e else {"text": e.get("text", "")}),
                **({"survived": bool(e["survived"])} if "survived" in e else {}),
                **({"ghost": True} if e.get("ghost") else {}),
            }
            for pid, e in judged
        ]
        if elimination and meta.get("outcome"):
            room["outcome"] = meta["outcome"]
    return ok(room)
