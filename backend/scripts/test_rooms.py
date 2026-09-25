"""Play a whole game against fake AWS (moto): no deploy, no Bedrock, no cost.

Usage:
  pip install "moto[dynamodb,s3]"
  python scripts/test_rooms.py
"""

import json
import os
import sys
from pathlib import Path

os.environ.update(
    AWS_DEFAULT_REGION="eu-west-2",
    AWS_ACCESS_KEY_ID="test",
    AWS_SECRET_ACCESS_KEY="test",
    TABLE_NAME="game",
    BUCKET_NAME="drawings",
    JUDGE_STATE_MACHINE_ARN="arn:fake",
)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import boto3  # noqa: E402
from moto import mock_aws  # noqa: E402

mock_aws().start()
boto3.client("s3").create_bucket(Bucket="drawings", CreateBucketConfiguration={"LocationConstraint": "eu-west-2"})
boto3.client("dynamodb").create_table(
    TableName="game",
    BillingMode="PAY_PER_REQUEST",
    AttributeDefinitions=[{"AttributeName": k, "AttributeType": "S"} for k in ("PK", "SK")],
    KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}, {"AttributeName": "SK", "KeyType": "RANGE"}],
)

from rooms import (  # noqa: E402
    create_room, end_round, get_room, join_room, reset_room, save_results, start_round, submit, upload_url,
)

events, executions = [], []
for mod in (join_room, start_round, submit, end_round, reset_room, save_results):
    mod.publish = lambda code, type, **p: events.append(type)
end_round.sfn.start_execution = lambda **kw: executions.append(json.loads(kw["input"]))
start_round.generate_prompt = lambda used: f"prompt {len(used) + 1}"


def call(mod, code=None, **body):
    resp = mod.handler({"pathParameters": {"code": code}, "body": json.dumps(body)}, None)
    return resp["statusCode"], json.loads(resp["body"])


_, room = call(create_room)
code = room["code"]
_, alex = call(join_room, code, name="Alex")
_, sam = call(join_room, code, name="Sam")
assert call(join_room, code, name="  ")[0] == 400
assert call(join_room, "ZZZZ", name="Jo")[0] == 404

# Round 1: host picks 2 rounds; both submit, which starts judging once.
status, r1 = call(start_round, code, totalRounds=2)
assert status == 200 and r1["round"] == 1 and r1["prompt"] == "prompt 1", r1
assert call(start_round, code)[0] == 409, "double start must fail"

for p in (alex, sam):
    _, up = call(upload_url, code, playerId=p["playerId"])
    assert call(submit, code, playerId=p["playerId"], key="rooms/evil.jpg")[0] == 400
    assert call(submit, code, playerId=p["playerId"], key=up["key"])[0] == 200
assert executions == [{"code": code, "round": 1}], executions
call(end_round, code)  # host timer fires too late: must not judge twice
assert len(executions) == 1
assert call(submit, code, playerId=alex["playerId"], key=up["key"])[0] == 409
assert call(reset_room, code)[0] == 409, "can't reset mid-judging"

save_results.handler(
    {
        "code": code,
        "round": 1,
        "judge": {"results": [
            {"playerId": alex["playerId"], "name": "Alex", "rank": 1, "score": 9, "roast": "Nice"},
            {"playerId": sam["playerId"], "name": "Sam", "rank": 2, "score": 4, "roast": "Oof"},
        ]},
        "voice": {"audioUrl": "https://audio"},
    },
    None,
)
_, room = call(get_room, code)
assert room["state"] == "results" and room["audioUrl"] == "https://audio", room
assert [r["name"] for r in room["results"]] == ["Alex", "Sam"]
assert room["results"][0]["imageUrl"].startswith("https://")
assert {p["name"]: p["score"] for p in room["players"]} == {"Alex": 9, "Sam": 4}
assert isinstance(room["totalRounds"], int), "Decimals must serialise as numbers"

# Round 2: nobody submits, host ends it. Then the game is over.
call(start_round, code)
call(end_round, code)
save_results.handler({"code": code, "round": 2, "judge": {"results": []}}, None)
assert call(start_round, code)[0] == 409, "game over after totalRounds"

# Play again: scores and entries cleared, players kept.
assert call(reset_room, code)[0] == 200
_, room = call(get_room, code)
assert room["state"] == "lobby" and room["round"] == 0
assert all(p["score"] == 0 and not p["submitted"] for p in room["players"]) and len(room["players"]) == 2
status, r1 = call(start_round, code)
assert status == 200 and r1["prompt"] == "prompt 3", "no repeated prompts after reset"
_, room = call(get_room, code)
assert not any(p["submitted"] for p in room["players"]), "old round-1 entries must not count"

assert events.count("results_ready") == 2 and "room_reset" in events
print("OK: full game passed")
