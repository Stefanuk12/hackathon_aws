import secrets

from shared.db import META, room_pk, table
from shared.http import error, ok

# No I or O, so codes can't be misread as 1 or 0.
LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ"


def handler(event, context):
    for _ in range(5):
        code = "".join(secrets.choice(LETTERS) for _ in range(4))
        try:
            table.put_item(
                Item={"PK": room_pk(code), "SK": META, "state": "lobby", "round": 0, "totalRounds": 3, "usedPrompts": []},
                ConditionExpression="attribute_not_exists(PK)",
            )
            return ok({"code": code})
        except table.meta.client.exceptions.ConditionalCheckFailedException:
            continue  # code already taken, roll again
    return error("Could not create a room, try again", 503)
