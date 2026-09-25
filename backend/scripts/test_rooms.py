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

from ai import judge  # noqa: E402
from rooms import (  # noqa: E402
    create_room, end_round, get_room, join_room, reset_room, save_results, start_round, submit, upload_url,
)
from shared import storage  # noqa: E402

events, executions = [], []
for mod in (join_room, start_round, submit, end_round, reset_room, save_results):
    mod.publish = lambda code, type, **p: events.append(type)
end_round.sfn.start_execution = lambda **kw: executions.append(json.loads(kw["input"]))
start_round.generate_prompt = lambda used: f"prompt {len(used) + 1}"
# Fake Bedrock: a PNG reference (like Nova Canvas returns) and a judge that ranks in order.
PNG = b"\x89PNG fake"
judge._references_or_none = lambda prompt: [PNG]
judge.judge = lambda prompt, images, refs: [
    {"drawing": i, "rank": i, "score": 10 - i, "roast": f"roast {i}"} for i in range(1, len(images) + 1)
]


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
    assert up["url"].startswith("https://drawings.s3.eu-west-2.amazonaws.com/") and "X-Amz-Signature" in up["url"], up
    storage.put(up["key"], b"jpeg", "image/jpeg")  # what the phone's PUT does
    assert call(submit, code, playerId=p["playerId"], key="rooms/evil.jpg")[0] == 400
    assert call(submit, code, playerId=p["playerId"], key=up["key"])[0] == 200
assert executions == [{"code": code, "round": 1}], executions
call(end_round, code)  # host timer fires too late: must not judge twice
assert len(executions) == 1
assert call(submit, code, playerId=alex["playerId"], key=up["key"])[0] == 409
assert call(reset_room, code)[0] == 409, "can't reset mid-judging"

judged = judge.handler(executions[0], None)  # Step Functions: Judge -> (HostVoice) -> SaveResults
assert len(judged["results"]) == 2 and len(judged["references"]) == 1
ref = storage.s3.get_object(Bucket="drawings", Key=f"rooms/{code}/1/reference0.png")
assert ref["ContentType"] == "image/png", "Nova Canvas PNGs must not be labelled JPEG"
step = {**executions[0], "judge": judged, "voice": {"audioUrl": "https://audio"}}
assert save_results.handler(step, None) == {"ok": True}
save_results.handler(step, None)  # a Step Functions retry must not double the scores

_, room = call(get_room, code)
assert room["state"] == "results" and room["audioUrl"] == "https://audio", room
assert [r["score"] for r in room["results"]] == [9, 8]
assert room["results"][0]["imageUrl"].startswith("https://drawings.s3.eu-west-2.amazonaws.com/")
assert sorted(p["score"] for p in room["players"]) == [8, 9]
assert isinstance(room["totalRounds"], int), "Decimals must serialise as numbers"

# Round 2: nobody submits, host ends it. Then the game is over.
call(start_round, code)
call(end_round, code)
save_results.handler({"code": code, "round": 2, "judge": {"results": []}}, None)
assert call(start_round, code)[0] == 409, "game over after totalRounds"
assert sorted(p["score"] for p in call(get_room, code)[1]["players"]) == [8, 9], "empty round adds nothing"

# Play again: scores and entries cleared, players kept.
assert call(reset_room, code)[0] == 200
_, room = call(get_room, code)
assert room["state"] == "lobby" and room["round"] == 0
assert all(p["score"] == 0 and not p["submitted"] for p in room["players"]) and len(room["players"]) == 2
status, r1 = call(start_round, code)
assert status == 200 and r1["prompt"] == "prompt 3", "no repeated prompts after reset"
_, room = call(get_room, code)
assert not any(p["submitted"] for p in room["players"]), "old round-1 entries must not count"

assert events.count("results_ready") == 2 and events.count("judging") == 2 and "room_reset" in events

# If Step Functions can't start, the room must go back to drawing instead of sticking in judging.
def broken(**kw):
    raise RuntimeError("sfn down")
end_round.sfn.start_execution = broken
try:
    call(end_round, code)
except RuntimeError:
    pass
assert call(get_room, code)[1]["state"] == "drawing"

# Nonsense bodies are rejected, not 500s.
assert submit.handler({"pathParameters": {"code": code}, "body": "not json"}, None)["statusCode"] == 403
print("OK: full game passed")

# Image models: Nova Canvas and Stability take different request bodies.
import base64, io  # noqa: E401, E402
from ai import reference  # noqa: E402

sent = []
def fake_invoke(modelId, body):
    sent.append((modelId, json.loads(body)))
    n = json.loads(body).get("imageGenerationConfig", {}).get("numberOfImages", 1)
    return {"body": io.BytesIO(json.dumps({"images": [base64.b64encode(PNG).decode()] * n}).encode())}
reference.bedrock_images.invoke_model = fake_invoke

os.environ["IMAGE_MODEL_ID"] = "amazon.nova-canvas-v1:0"
assert reference.generate_references("a cat") == [PNG, PNG] and len(sent) == 1, "Nova: one call for both"
assert sent[0][1]["taskType"] == "TEXT_IMAGE" and "a cat" in sent[0][1]["textToImageParams"]["text"]
os.environ["IMAGE_MODEL_ID"] = "stability.stable-image-core-v1:1"
assert len(reference.generate_references("a cat")) == 2 and "prompt" in sent[-1][1]
print("OK: image model bodies")
