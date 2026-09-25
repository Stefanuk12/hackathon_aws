from shared.db import load_room
from shared.http import body, error, ok, room_code
from shared.storage import drawing_key, presign_put


def handler(event, context):
    code = room_code(event)
    player_id = body(event).get("playerId")
    meta, players, _ = load_room(code)
    if not meta:
        return error(f"Room {code} not found", 404)
    if player_id not in players:
        return error("Unknown player", 403)
    if meta["state"] != "drawing":
        return error("Too late! The round is over.", 409)
    if meta.get("roundMode", "draw") != "draw":
        return error("This round is typed, not drawn", 409)

    key = drawing_key(code, meta["round"], player_id)
    return ok({"url": presign_put(key, "image/jpeg"), "key": key})
