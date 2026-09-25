from shared.db import META, load_room, room_pk, table
from shared.events import publish
from shared.http import error, ok, room_code


def handler(event, context):
    """Play again: back to the lobby, scores to 0, players kept."""
    code = room_code(event)
    meta, players, entries = load_room(code)
    if not meta:
        return error(f"Room {code} not found", 404)
    if meta["state"] == "judging":
        return error("Wait for the results first", 409)

    table.update_item(
        Key={"PK": room_pk(code), "SK": META},
        UpdateExpression="SET #s = :lobby, #r = :zero REMOVE prompt, endsAt, audioUrl",
        ExpressionAttributeNames={"#s": "state", "#r": "round"},
        ExpressionAttributeValues={":lobby": "lobby", ":zero": 0},
    )
    with table.batch_writer() as batch:
        # Old entries must go: round numbers restart at 1, so they'd count as new submissions.
        for e in entries:
            batch.delete_item(Key={"PK": e["PK"], "SK": e["SK"]})
        for p in players.values():
            batch.put_item(Item={**p, "score": 0})

    publish(code, "room_reset")
    return ok({"ok": True})
