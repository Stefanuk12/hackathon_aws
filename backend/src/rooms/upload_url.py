import os

import boto3

from shared.db import drawing_key, load_room
from shared.http import body, error, ok, room_code

s3 = boto3.client("s3")


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

    key = drawing_key(code, meta["round"], player_id)
    url = s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": os.environ["BUCKET_NAME"], "Key": key, "ContentType": "image/jpeg"},
        ExpiresIn=300,
    )
    return ok({"url": url, "key": key})
