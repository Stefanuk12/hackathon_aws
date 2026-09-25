from shared.http import ok


def handler(event, context):
    # TODO person 3: put PLAYER#<id> {name, score: 0}, publish "player_joined".
    return ok({"playerId": "p_1a2b3c"})
