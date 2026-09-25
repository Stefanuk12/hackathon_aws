import os

import boto3

from shared.db import META, entry_sk, player_sk, room_pk, table
from shared.events import publish

s3 = boto3.client("s3")


def handler(event, context):
    """Last step of the judge state machine.

    Input: {code, round, judge: {results}, voice?: {audioUrl}}
    """
    code, round_no = event["code"], event["round"]
    results = event["judge"]["results"]
    audio_url = (event.get("voice") or {}).get("audioUrl")
    bucket = os.environ["BUCKET_NAME"]

    for r in results:
        # Signed once here, not on every poll, so the reveal's <img> URLs stay stable.
        # ponytail: presigned URLs die with the Lambda's credentials (a few hours); fine for one game night.
        entry = table.get_item(Key={"PK": room_pk(code), "SK": entry_sk(round_no, r["playerId"])}).get("Item", {})
        r["imageUrl"] = (
            s3.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": entry["s3Key"]}, ExpiresIn=3600)
            if entry.get("s3Key")
            else ""
        )
        table.update_item(
            Key={"PK": room_pk(code), "SK": entry_sk(round_no, r["playerId"])},
            UpdateExpression="SET #rank = :rank, score = :score, roast = :roast, imageUrl = :url",
            ExpressionAttributeNames={"#rank": "rank"},
            ExpressionAttributeValues={":rank": r["rank"], ":score": r["score"], ":roast": r["roast"], ":url": r["imageUrl"]},
        )
        try:
            table.update_item(
                Key={"PK": room_pk(code), "SK": player_sk(r["playerId"])},
                UpdateExpression="ADD score :score",
                # Skips the AI player and anyone without a PLAYER# row, instead of creating one.
                ConditionExpression="attribute_exists(SK)",
                ExpressionAttributeValues={":score": r["score"]},
            )
        except table.meta.client.exceptions.ConditionalCheckFailedException:
            pass

    try:
        # Only if this round is still being judged: a reset mid-judging wins.
        table.update_item(
            Key={"PK": room_pk(code), "SK": META},
            UpdateExpression="SET #s = :results, audioUrl = :audio",
            ConditionExpression="#s = :judging AND #r = :round",
            ExpressionAttributeNames={"#s": "state", "#r": "round"},
            ExpressionAttributeValues={":results": "results", ":audio": audio_url, ":judging": "judging", ":round": round_no},
        )
    except table.meta.client.exceptions.ConditionalCheckFailedException:
        print(f"Room {code} moved on before round {round_no} was judged; results not published")
        return {"ok": False}

    publish(code, "results_ready", round=round_no, results=results, audioUrl=audio_url)
    return {"ok": True}
