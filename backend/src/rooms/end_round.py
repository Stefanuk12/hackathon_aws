import json
import os

import boto3

from shared.db import META, room_pk, table
from shared.events import publish
from shared.http import ok, room_code

sfn = boto3.client("stepfunctions")


def _set_state(code, new, expected):
    """Conditional state change; returns the updated META, or None if the state wasn't `expected`."""
    try:
        return table.update_item(
            Key={"PK": room_pk(code), "SK": META},
            UpdateExpression="SET #s = :new",
            ConditionExpression="#s = :expected",
            ExpressionAttributeNames={"#s": "state"},
            ExpressionAttributeValues={":new": new, ":expected": expected},
            ReturnValues="ALL_NEW",
        )["Attributes"]
    except table.meta.client.exceptions.ConditionalCheckFailedException:
        return None


def start_judging(code):
    """Move drawing -> judging exactly once, then start the judge state machine.

    Safe to call twice (last submit and the host's /end can race): only the call
    whose conditional update wins starts the state machine.
    """
    meta = _set_state(code, "judging", "drawing")
    if not meta:
        return  # already judging (or room gone)

    round_no = int(meta["round"])
    try:
        sfn.start_execution(
            stateMachineArn=os.environ["JUDGE_STATE_MACHINE_ARN"],
            input=json.dumps({"code": code, "round": round_no}),
        )
    except Exception:
        # Nothing will ever finish this round, so undo, or the room is stuck in "judging".
        # The host's next /end retries.
        _set_state(code, "drawing", "judging")
        raise
    publish(code, "judging", round=round_no)


def handler(event, context):
    # Called by the host screen when the timer hits 0.
    start_judging(room_code(event))
    return ok({"ok": True})
