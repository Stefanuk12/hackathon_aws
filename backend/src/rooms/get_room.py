from shared.http import ok


def handler(event, context):
    # TODO person 3: query PK=ROOM#<code>, assemble contracts/fixtures/room.json shape
    # (incl. mode, roundMode). Results: presigned GET imageUrl for draw rounds, text for
    # survive/wit rounds, and survived for survive rounds.
    return ok({"code": "WXYZ", "state": "lobby", "round": 0, "players": []})
