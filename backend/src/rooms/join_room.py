import secrets

from shared.db import load_room, player_sk, room_pk, table
from shared.events import publish
from shared.http import body, error, ok, room_code


def handler(event, context):
    code = room_code(event)
    name = str(body(event).get("name", "")).strip()[:20]
    if not name:
        return error("Enter a name")

    meta, _, _ = load_room(code)
    if not meta:
        return error(f"Room {code} not found", 404)

    player_id = f"p_{secrets.token_hex(3)}"
    table.put_item(Item={"PK": room_pk(code), "SK": player_sk(player_id), "name": name, "score": 0})
    publish(code, "player_joined", playerId=player_id, name=name)
    return ok({"playerId": player_id})
