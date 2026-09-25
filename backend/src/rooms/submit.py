import time

from rooms.end_round import start_judging
from shared.db import entry_sk, load_room, room_pk, round_entries, table
from shared.events import publish
from shared.http import body, error, ok, room_code
from shared.storage import drawing_key

GRACE_MS = 5000


def handler(event, context):
    code = room_code(event)
    req = body(event)
    player_id = req.get("playerId")
    meta, players, _ = load_room(code)
    if not meta:
        return error(f"Room {code} not found", 404)
    if player_id not in players:
        return error("Unknown player", 403)
    if meta["state"] != "drawing":
        return error("Too late! The round is over.", 409)

    # Only accept the key upload-url handed out, so nobody can submit someone else's drawing.
    round_no = meta["round"]
    key = drawing_key(code, round_no, player_id)
    if req.get("key") != key:
        return error("Wrong upload key")

    table.put_item(Item={"PK": room_pk(code), "SK": entry_sk(round_no, player_id), "s3Key": key})

    # Re-read after writing: if the last two players submit at the same moment, whichever
    # reads second is guaranteed to see both entries, so judging always starts.
    _, players, entries = load_room(code)
    submitted = round_entries(entries, round_no)
    publish(code, "submission_in", playerId=player_id, submitted=len(submitted), total=len(players))
    # Also judge on a late submit, so the round still ends if the host screen dropped
    # and never called /end. Matches the mock backend.
    late = int(time.time() * 1000) > meta["endsAt"] + GRACE_MS
    if late or set(players) <= set(submitted):
        try:
            start_judging(code)
        except Exception as e:
            # The drawing is saved, so don't tell the player it failed; the host's /end retries judging.
            print("Could not start judging:", e)
    return ok({"ok": True})
