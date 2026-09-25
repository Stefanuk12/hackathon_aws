from shared.db import META, load_room, room_pk, round_entries, table
from shared.events import publish
from shared.storage import presign_get


def handler(event, context):
    """Last step of the judge state machine. Safe to retry: it only overwrites rows.

    Input: {code, round, judge: {results}, voice?: {audioUrl}}
    """
    code, round_no = event["code"], event["round"]
    results = event["judge"]["results"]
    audio_url = (event.get("voice") or {}).get("audioUrl")

    meta, _, entries = load_room(code)
    if not meta or meta["state"] != "judging" or meta["round"] != round_no:
        print(f"Room {code} moved on before round {round_no} was judged; results dropped")
        return {"ok": False}

    entries = round_entries(entries, round_no)
    with table.batch_writer() as batch:
        for r in results:
            entry = entries.get(r["playerId"])
            r["imageUrl"] = ""
            if not entry:
                continue
            # Signed once here, not on every poll, so the reveal's <img> URLs stay stable.
            r["imageUrl"] = presign_get(entry["s3Key"])
            batch.put_item(Item={**entry, "rank": r["rank"], "score": r["score"], "roast": r["roast"], "imageUrl": r["imageUrl"]})

    table.update_item(
        Key={"PK": room_pk(code), "SK": META},
        UpdateExpression="SET #s = :results, audioUrl = :audio",
        ExpressionAttributeNames={"#s": "state"},
        ExpressionAttributeValues={":results": "results", ":audio": audio_url},
    )
    publish(code, "results_ready", round=round_no, results=results, audioUrl=audio_url)
    return {"ok": True}
