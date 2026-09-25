import json
import os

import boto3

from shared.db import META, room_pk, table
from shared.events import publish
from shared.http import ok, room_code

sfn = boto3.client("stepfunctions")


def start_judging(code):
    """Move drawing -> judging exactly once, then start the judge state machine.

    Safe to call twice (last submit and the host's /end can race): only the call
    whose conditional update wins starts the state machine.
    """
    try:
        meta = table.update_item(
            Key={"PK": room_pk(code), "SK": META},
            UpdateExpression="SET #s = :judging",
            ConditionExpression="#s = :drawing",
            ExpressionAttributeNames={"#s": "state"},
            ExpressionAttributeValues={":judging": "judging", ":drawing": "drawing"},
            ReturnValues="ALL_NEW",
        )["Attributes"]
    except table.meta.client.exceptions.ConditionalCheckFailedException:
        return  # already judging (or room gone)

    round_no = int(meta["round"])
    publish(code, "judging", round=round_no)
    sfn.start_execution(
        stateMachineArn=os.environ["JUDGE_STATE_MACHINE_ARN"],
        input=json.dumps({"code": code, "round": round_no}),
    )


def handler(event, context):
    # Called by the host screen when the timer hits 0.
    start_judging(room_code(event))
    return ok({"ok": True})
