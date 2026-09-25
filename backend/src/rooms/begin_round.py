import time

from rooms.start_round import ROUND_SECONDS
from shared.db import META, room_pk, table
from shared.events import publish
from shared.http import ok, room_code


def start_drawing(code):
    """Themed rounds: end the intro and start the round. Returns the new META, or None if it
    wasn't in "theme" (the host's Skip and the intro timer race, so only the first call counts).
    """
    ends_at = int(time.time() * 1000) + ROUND_SECONDS * 1000
    try:
        meta = table.update_item(
            Key={"PK": room_pk(code), "SK": META},
            # themeEndsAt goes: the intro is over, and only endsAt drives the round timer now.
            UpdateExpression="SET #s = :drawing, endsAt = :ends REMOVE themeEndsAt",
            ConditionExpression="#s = :theme",
            ExpressionAttributeNames={"#s": "state"},
            ExpressionAttributeValues={":drawing": "drawing", ":ends": ends_at, ":theme": "theme"},
            ReturnValues="ALL_NEW",
        )["Attributes"]
    except table.meta.client.exceptions.ConditionalCheckFailedException:
        return None

    publish(
        code, "round_started",
        round=int(meta["round"]), roundMode=meta.get("roundMode", "draw"), prompt=meta.get("prompt"), endsAt=ends_at,
    )
    return meta


def handler(event, context):
    # Called by the host screen when the theme intro's timer ends, or the host presses Skip.
    start_drawing(room_code(event))
    return ok({"ok": True})
