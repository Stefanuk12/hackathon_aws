from shared.db import META, load_room, room_pk, round_entries, table
from shared.elimination import apply_elimination
from shared.events import publish
from shared.storage import presign_get


def _run_elimination(meta, players, results):
    """Work out who dies, who revives and what each entry is actually worth.

    Returns (points by playerId, updated player rows, outcome). Players who didn't
    submit score 0, so a missed round can eliminate you.
    """
    scores = {r["playerId"]: r["score"] for r in results}
    before = [
        {"playerId": pid, "alive": bool(p.get("alive", True)), "streak": int(p.get("streak", 0))}
        for pid, p in players.items()
    ]
    out = apply_elimination(before, scores, int(meta.get("reviveAfter", 2)))
    return out["points"], out["players"], {"eliminated": out["eliminated"], "revived": out["revived"]}


def handler(event, context):
    """Last step of the judge state machine. Safe to retry: it only overwrites rows.

    Input: {code, round, judge: {results, references?}, voice?: {audioUrl, script}}
    """
    code, round_no = event["code"], event["round"]
    results = event["judge"]["results"]
    references = event["judge"].get("references", [])
    voice = event.get("voice") or {}
    # Kept even when Polly worked, so the host screen can read it aloud if audio won't play.
    audio_url, script = voice.get("audioUrl"), voice.get("script")

    meta, players, entries = load_room(code)
    if not meta or meta["state"] != "judging" or meta["round"] != round_no:
        print(f"Room {code} moved on before round {round_no} was judged; results dropped")
        return {"ok": False}

    elimination = bool(meta.get("elimination", False))
    ghosts = {pid for pid, p in players.items() if not p.get("alive", True)} if elimination else set()
    if elimination:
        points, updated_players, outcome = _run_elimination(meta, players, results)
    else:
        points, updated_players, outcome = {r["playerId"]: r["score"] for r in results}, [], None

    entries = round_entries(entries, round_no)
    with table.batch_writer() as batch:
        for r in results:
            entry = entries.get(r["playerId"])
            r["points"] = points.get(r["playerId"], r["score"])
            if r["playerId"] in ghosts:
                r["ghost"] = True
            r["imageUrl"] = ""
            if not entry:
                continue
            extra = {"rank": r["rank"], "score": r["score"], "points": r["points"], "roast": r["roast"]}
            if r["playerId"] in ghosts:
                extra["ghost"] = True
            if entry.get("s3Key"):
                # Signed once here, not on every poll, so the reveal's <img> URLs stay stable.
                r["imageUrl"] = presign_get(entry["s3Key"])
                extra["imageUrl"] = r["imageUrl"]
            else:
                r["text"] = entry.get("text", "")
            batch.put_item(Item={**entry, **extra})

        # Elimination changes who's alive, so save it before the screens read the results.
        for p in updated_players:
            row = players[p["playerId"]]
            batch.put_item(Item={**row, "alive": p["alive"], "streak": p["streak"]})

    update = "SET #s = :results, audioUrl = :audio, hostScript = :script, referenceUrls = :refs"
    values = {":results": "results", ":audio": audio_url, ":script": script, ":refs": references}
    if outcome:
        update += ", outcome = :outcome"
        values[":outcome"] = outcome
    table.update_item(
        Key={"PK": room_pk(code), "SK": META},
        UpdateExpression=update,
        ExpressionAttributeNames={"#s": "state"},
        ExpressionAttributeValues=values,
    )
    publish(
        code, "results_ready",
        round=round_no, results=results, outcome=outcome,
        audioUrl=audio_url, hostScript=script, references=references,
    )
    return {"ok": True}
