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

    # Scores are summed from entries, so deleting them zeroes every score. It also stops
    # old round-1 entries counting as submissions once round numbers restart.
    with table.batch_writer() as batch:
        for e in entries:
            batch.delete_item(Key={"PK": e["PK"], "SK": e["SK"]})
        # Everyone plays the new game alive, whatever elimination did to them last time.
        for p in players.values():
            batch.put_item(Item={**p, "alive": True, "streak": 0})
    table.update_item(
        Key={"PK": room_pk(code), "SK": META},
        UpdateExpression=(
            "SET #s = :lobby, #r = :zero "
            "REMOVE prompt, roundMode, endsAt, #th, themeEndsAt, outcome, audioUrl, hostScript, referenceUrls"
        ),
        ExpressionAttributeNames={"#s": "state", "#r": "round", "#th": "theme"},
        ExpressionAttributeValues={":lobby": "lobby", ":zero": 0},
    )
    publish(code, "room_reset")
    return ok({"ok": True})
