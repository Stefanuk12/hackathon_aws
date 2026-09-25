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
start_round.generate_prompt = lambda used, theme=None, mode="draw": (
    f"prompt {len(used) + 1} [{mode}]" + (f" [{theme.split(' (')[0]}]" if theme else "")
)
# Fake Bedrock: a PNG reference (like Nova Canvas returns) and a judge that ranks in order.
PNG = b"\x89PNG fake"
JPEG = b"\xff\xd8\xff fake"  # the judge skips uploads that aren't real JPEG/PNG
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
status, r1 = call(start_round, code, totalRounds=2, mode="draw", themeEvery=0)
assert status == 200 and r1["round"] == 1 and r1["prompt"].startswith("prompt 1"), r1
assert call(start_round, code)[0] == 409, "double start must fail"

for p in (alex, sam):
    _, up = call(upload_url, code, playerId=p["playerId"])
    assert up["url"].startswith("https://drawings.s3.eu-west-2.amazonaws.com/") and "X-Amz-Signature" in up["url"], up
    storage.put(up["key"], JPEG, "image/jpeg")  # what the phone's PUT does
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
step = {**executions[0], "judge": judged, "voice": {"audioUrl": "https://audio", "script": "The results are in!"}}
assert save_results.handler(step, None) == {"ok": True}
save_results.handler(step, None)  # a Step Functions retry must not double the scores

_, room = call(get_room, code)
assert room["state"] == "results" and room["audioUrl"] == "https://audio", room
assert [r["score"] for r in room["results"]] == [9, 8]
assert room["results"][0]["imageUrl"].startswith("https://drawings.s3.eu-west-2.amazonaws.com/")
assert sorted(p["score"] for p in room["players"]) == [8, 9]
assert isinstance(room["totalRounds"], int), "Decimals must serialise as numbers"
assert room["hostScript"] == "The results are in!", "script is the fallback when Polly fails"
assert room["references"] == judged["references"] and len(room["references"]) == 1

# Round 2: nobody submits, host ends it. Then the game is over.
call(start_round, code)
_, room = call(get_room, code)
assert room["hostScript"] is None and room["references"] == [], "last round's voice/references cleared"
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
assert status == 200 and r1["prompt"].startswith("prompt 3"), "no repeated prompts after reset"
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
# ...and the last submit still succeeds for the player: their drawing is saved, /end retries.
for p in (alex, sam):
    key = call(upload_url, code, playerId=p["playerId"])[1]["key"]
    storage.put(key, JPEG, "image/jpeg")
    assert call(submit, code, playerId=p["playerId"], key=key)[0] == 200
assert call(get_room, code)[1]["state"] == "drawing"

# Nonsense bodies are rejected, not 500s.
assert submit.handler({"pathParameters": {"code": code}, "body": "not json"}, None)["statusCode"] == 403
print("OK: full game passed")

from shared.db import META, room_pk, table  # noqa: E402

end_round.sfn.start_execution = lambda **kw: executions.append(json.loads(kw["input"]))


def new_game(*names, **settings):
    code = call(create_room)[1]["code"]
    ids = [call(join_room, code, name=n)[1]["playerId"] for n in names]
    call(start_round, code, mode=settings.pop("mode", "draw"), themeEvery=settings.pop("themeEvery", 0), **settings)
    return code, ids


# One bad upload must not sink the round: the judge skips it and ranks the rest.
code, (good, bad) = new_game("Good", "Bad")
for pid, data in ((good, JPEG), (bad, b"not an image")):
    key = call(upload_url, code, playerId=pid)[1]["key"]
    storage.put(key, data, "image/jpeg")
    call(submit, code, playerId=pid, key=key)
assert [r["playerId"] for r in judge.handler(executions[-1], None)["results"]] == [good]

# Host screen dropped: a submit after the timer (+ grace) starts judging without everyone.
code, (early, _) = new_game("Early", "Asleep")
table.update_item(Key={"PK": room_pk(code), "SK": META}, UpdateExpression="SET endsAt = :t", ExpressionAttributeValues={":t": 0})
key = call(upload_url, code, playerId=early)[1]["key"]
storage.put(key, JPEG, "image/jpeg")
call(submit, code, playerId=early, key=key)
assert call(get_room, code)[1]["state"] == "judging"

# Room caps at MAX_PLAYERS (Bedrock takes at most 20 images per call).
code = call(create_room)[1]["code"]
for i in range(join_room.MAX_PLAYERS):
    assert call(join_room, code, name=f"P{i}")[0] == 200
assert call(join_room, code, name="One too many")[0] == 409

# Duplicate ranks from the model are renumbered so there's exactly one winner.
reply = '{"results": [{"drawing": 1, "rank": 1, "score": 7, "roast": "a"}, {"drawing": 2, "rank": 1, "score": 5, "roast": "b"}]}'
assert sorted(r["rank"] for r in judge._parse(reply, 2)) == [1, 2]
print("OK: bad upload, late submit, room cap, rank renumbering")

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

# ---------------------------------------------------------------- game modes
from rooms import begin_round  # noqa: E402

begin_round.publish = lambda code, type, **p: events.append(type)
judge.judge_text = lambda mode, prompt, answers: [
    {"answer": i, "rank": i, "score": 10 - i, "roast": f"roast {i}", **({"survived": i == 1} if mode == "survive" else {})}
    for i in range(1, len(answers) + 1)
]


def play_text_round(code, ids, answers):
    for pid, text in zip(ids, answers):
        assert call(submit, code, playerId=pid, text=text)[0] == 200
    judged = judge.handler(executions[-1], None)
    save_results.handler({**executions[-1], "judge": judged}, None)
    return call(get_room, code)[1]


# Survive: typed answers, no upload, and the AI says who lived.
code, ids = new_game("Ann", "Bo", mode="survive")
assert call(get_room, code)[1]["roundMode"] == "survive"
assert call(upload_url, code, playerId=ids[0])[0] == 409, "typed rounds have nothing to upload"
room = play_text_round(code, ids, ["I befriend the bear", "I panic"])
assert {r["text"] for r in room["results"]} == {"I befriend the bear", "I panic"}, room["results"]
assert [r["survived"] for r in room["results"]] == [True, False]
assert "imageUrl" not in room["results"][0], "typed answers carry text, not an image"
assert sorted(p["score"] for p in room["players"]) == [8, 9]

# Quick Wit: same shape, no survived flag. Answers are capped at 200 characters.
code, ids = new_game("Ann", "Bo", mode="wit")
room = play_text_round(code, ids, ["x" * 500, "short"])
assert max(len(r["text"]) for r in room["results"]) == submit.TEXT_LIMIT, "long answers are capped"
assert all("survived" not in r for r in room["results"])

# Mixed cycles draw -> survive -> wit.
code, ids = new_game("Ann", "Bo", mode="mixed", totalRounds=3)
seen = [call(get_room, code)[1]["roundMode"]]
for _ in range(2):
    call(end_round, code)
    save_results.handler({**executions[-1], "judge": {"results": []}}, None)
    call(start_round, code)
    seen.append(call(get_room, code)[1]["roundMode"])
assert seen == ["draw", "survive", "wit"], seen
print("OK: game modes (draw, survive, wit, mixed)")

# ---------------------------------------------------------------- themed rounds
code, ids = new_game("Ann", "Bo", mode="wit", themeEvery=1)
room = call(get_room, code)[1]
assert room["state"] == "theme" and room["theme"] and room["themeEndsAt"], room
assert room["endsAt"] is None, "the round timer only starts after the intro"
assert {"service", "facts", "inAmacide"} <= set(room["theme"]), room["theme"]
assert "promptHint" not in room["theme"] and "examples" not in room["theme"], "prompt-writing fields stay server-side"
assert room["prompt"].endswith(f"[{room['theme']['service']}]"), "prompt is written for the theme"
assert call(submit, code, playerId=ids[0], text="too early")[0] == 409

# Skip (or the intro timer) starts the round; a second call is harmless.
assert call(begin_round, code)[0] == 200
room = call(get_room, code)[1]
assert room["state"] == "drawing" and room["endsAt"] and room["themeEndsAt"] is None, room
ends_at = room["endsAt"]
assert call(begin_round, code)[0] == 200
assert call(get_room, code)[1]["endsAt"] == ends_at, "a double Skip must not extend the round"
assert "theme_intro" in events and events.count("round_started") >= 1

# themeEvery=2 themes rounds 1 and 3 but not 2, and never repeats a theme.
code, ids = new_game("Ann", "Bo", mode="wit", themeEvery=2, totalRounds=3)
themes, states = [], []
for i in range(3):
    room = call(get_room, code)[1]
    states.append(room["state"])
    if room["theme"]:
        themes.append(room["theme"]["id"])
        call(begin_round, code)
    call(end_round, code)
    save_results.handler({**executions[-1], "judge": {"results": []}}, None)
    if i < 2:
        call(start_round, code)
assert states == ["theme", "drawing", "theme"], states
assert len(themes) == 2 and len(set(themes)) == 2, themes
print("OK: themed rounds")

# ---------------------------------------------------------------- elimination
def judge_scores(scores):
    """Make the judge hand back exactly these scores, ranked best first."""
    order = sorted(scores, key=lambda pid: -scores[pid])
    judge.handler = lambda event, ctx: {
        "results": [
            {"playerId": pid, "name": pid, "rank": i, "score": scores[pid], "roast": "r"}
            for i, pid in enumerate(order, start=1)
        ],
        "references": [],
    }


def play_round(code, scores, ids):
    for pid in ids:
        call(submit, code, playerId=pid, text="answer")
    call(end_round, code)  # the host's timer; a no-op if the last submit already started judging
    judge_scores(scores)
    save_results.handler({**executions[-1], "judge": judge.handler(executions[-1], None)}, None)
    return call(get_room, code)[1]


code, (ann, bo, cy) = new_game("Ann", "Bo", "Cy", mode="wit", totalRounds=4, elimination=True, reviveAfter=2)
room = call(get_room, code)[1]
assert room["elimination"] and room["reviveAfter"] == 2
assert all(p["alive"] and p["streak"] == 0 for p in room["players"]), room["players"]

# Round 1: Cy scores lowest and is eliminated.
room = play_round(code, {ann: 9, bo: 7, cy: 2}, [ann, bo, cy])
assert room["outcome"] == {"eliminated": [cy], "revived": []}, room["outcome"]
alive = {p["playerId"]: p["alive"] for p in room["players"]}
assert alive == {ann: True, bo: True, cy: False}, alive
assert {p["playerId"]: p["score"] for p in room["players"]} == {ann: 9, bo: 7, cy: 2}, "the fatal round still scores"

# Round 2: Cy plays on as a ghost for half points and starts a revive streak.
call(start_round, code)
room = play_round(code, {ann: 9, bo: 8, cy: 7}, [ann, bo, cy])
cy_result = next(r for r in room["results"] if r["playerId"] == cy)
assert cy_result["score"] == 7 and cy_result["points"] == 3 and cy_result["ghost"] is True, cy_result
assert next(p for p in room["players"] if p["playerId"] == cy)["score"] == 2 + 3, "ghost points are halved"
assert next(p for p in room["players"] if p["playerId"] == cy)["streak"] == 1
assert room["outcome"]["eliminated"] == [bo], "lowest living player dies; ghosts are safe"

# Round 3: a second good round brings Cy back to life.
call(start_round, code)
room = play_round(code, {ann: 9, bo: 8, cy: 8}, [ann, bo, cy])
assert cy in room["outcome"]["revived"], room["outcome"]
cy_player = next(p for p in room["players"] if p["playerId"] == cy)
assert cy_player["alive"] and cy_player["streak"] == 0, cy_player

# Not submitting scores 0, so it can get you eliminated.
code, (ann, bo) = new_game("Ann", "Bo", mode="wit", totalRounds=2, elimination=True)
room = play_round(code, {ann: 6}, [ann])  # Bo says nothing
assert room["outcome"]["eliminated"] == [bo], room["outcome"]

# Play again clears elimination: everyone is alive with a clean streak.
assert call(reset_room, code)[0] == 200
room = call(get_room, code)[1]
assert all(p["alive"] and p["streak"] == 0 and p["score"] == 0 for p in room["players"]), room["players"]
assert room["theme"] is None and room["roundMode"] is None and "outcome" not in room, room

# With elimination off, nobody dies and the room keeps the flags to itself.
code, (ann, bo) = new_game("Ann", "Bo", mode="wit", totalRounds=2)
room = play_round(code, {ann: 9, bo: 1}, [ann, bo])
assert "outcome" not in room and not room["elimination"]
assert all("alive" not in p for p in room["players"]), "alive/streak only appear in elimination games"
assert all(r["points"] == r["score"] for r in room["results"]), "no halving without elimination"
print("OK: elimination (death, ghost points, revival, reset)")
