from shared.db import load_room, round_entries
from shared.http import error, ok, room_code


def handler(event, context):
    code = room_code(event)
    meta, players, entries = load_room(code)
    if not meta:
        return error(f"Room {code} not found", 404)

    this_round = round_entries(entries, meta["round"])
    room = {
        "code": code,
        "state": meta["state"],
        "round": meta["round"],
        "totalRounds": meta["totalRounds"],
        "prompt": meta.get("prompt"),
        "endsAt": meta.get("endsAt"),
        "players": [
            {"playerId": pid, "name": p["name"], "score": p["score"], "submitted": pid in this_round}
            for pid, p in players.items()
        ],
        "audioUrl": meta.get("audioUrl"),
    }
    if meta["state"] == "results":
        ranked = sorted((e for e in this_round.items() if "rank" in e[1]), key=lambda e: e[1]["rank"])
        room["results"] = [
            {
                "playerId": pid,
                "name": players[pid]["name"] if pid in players else "The AI",
                "rank": e["rank"],
                "score": e["score"],
                "roast": e["roast"],
                "imageUrl": e.get("imageUrl", ""),
            }
            for pid, e in ranked
        ]
    return ok(room)
