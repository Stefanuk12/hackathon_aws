from rooms.end_round import start_judging
from shared.db import drawing_key, entry_sk, load_room, room_pk, round_entries, table
from shared.events import publish
from shared.http import body, error, ok, room_code


def handler(event, context):
    code = room_code(event)
    req = body(event)
    player_id = req.get("playerId")
    meta, players, entries = load_room(code)
    if not meta:
        return error(f"Room {code} not found", 404)
    if player_id not in players:
        return error("Unknown player", 403)
    if meta["state"] != "drawing":
        return error("Too late! The round is over.", 409)

    # Only accept the key upload-url handed out, so nobody can submit someone else's drawing.
    key = drawing_key(code, meta["round"], player_id)
    if req.get("key") != key:
        return error("Wrong upload key")

    table.put_item(Item={"PK": room_pk(code), "SK": entry_sk(meta["round"], player_id), "s3Key": key})

    submitted = set(round_entries(entries, meta["round"])) | {player_id}
    publish(code, "submission_in", playerId=player_id, submitted=len(submitted), total=len(players))
    if submitted >= set(players):
        start_judging(code)
    return ok({"ok": True})
