from shared.http import ok


def handler(event, context):
    # TODO person 3: query PK=ROOM#<code>, assemble contracts/fixtures/room.json shape.
    # Presign GET URLs for result images (imageUrl).
    return ok({"code": "WXYZ", "state": "lobby", "round": 0, "players": []})
