import os

import boto3

table = boto3.resource("dynamodb").Table(os.environ.get("TABLE_NAME", "local"))


def room_pk(code):
    return f"ROOM#{code}"


META = "META"


def player_sk(player_id):
    return f"PLAYER#{player_id}"


def entry_sk(round_no, player_id):
    return f"ROUND#{round_no}#{player_id}"
