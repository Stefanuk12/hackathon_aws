import os

import boto3
from boto3.dynamodb.conditions import Key

table = boto3.resource("dynamodb").Table(os.environ.get("TABLE_NAME", "local"))


def room_pk(code):
    return f"ROOM#{code}"


META = "META"


def player_sk(player_id):
    return f"PLAYER#{player_id}"


def entry_sk(round_no, player_id):
    return f"ROUND#{round_no}#{player_id}"


def load_room(code):
    """All of a room's rows in one query: (META or None, {playerId: player row}, [ROUND# rows])."""
    # Consistent, so the "has everyone submitted?" check sees writes made a moment ago.
    items = table.query(KeyConditionExpression=Key("PK").eq(room_pk(code)), ConsistentRead=True)["Items"]
    meta = next((i for i in items if i["SK"] == META), None)
    players = {i["SK"].split("#", 1)[1]: i for i in items if i["SK"].startswith("PLAYER#")}
    entries = [i for i in items if i["SK"].startswith("ROUND#")]
    return meta, players, entries


def round_entries(entries, round_no):
    """{playerId: entry row} for one round."""
    prefix = f"ROUND#{round_no}#"
    return {e["SK"][len(prefix):]: e for e in entries if e["SK"].startswith(prefix)}
