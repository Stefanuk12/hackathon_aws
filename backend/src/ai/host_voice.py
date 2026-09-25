"""Game-show host voice for the reveal, via Polly."""

import os

import boto3

polly = boto3.client("polly")
s3 = boto3.client("s3")


def build_script(results):
    """Turn the ranked results into ~20 seconds of game-show patter."""
    if not results:
        return "Nobody drew anything? Tough crowd."
    ranked = sorted(results, key=lambda r: r["rank"])
    winner = ranked[0]
    lines = [
        "Ladies and gentlemen, the results are in!",
        f"Taking first place with {winner['score']} out of ten, it's {winner['name']}!",
        winner["roast"],
    ]
    for r in ranked[1:3]:  # 2nd and 3rd place only, to keep it short
        lines.append(f"In position {r['rank']}, {r['name']}. {r['roast']}")
    return " ".join(lines)


def handler(event, context):
    """Step Functions task. Input: {code, round, judge: {results}}. Output: {audioUrl, script}.

    If Polly fails, audioUrl is None and the host screen can read `script` aloud
    with the browser's own speech (window.speechSynthesis) instead.
    """
    script = build_script(event["judge"]["results"])
    try:
        audio = polly.synthesize_speech(
            Text=script, Engine="neural", VoiceId="Brian", OutputFormat="mp3"
        )["AudioStream"].read()

        bucket = os.environ["BUCKET_NAME"]
        key = f"rooms/{event['code']}/{event['round']}/host.mp3"
        s3.put_object(Bucket=bucket, Key=key, Body=audio, ContentType="audio/mpeg")
        url = s3.generate_presigned_url(
            "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=3600
        )
    except Exception as e:
        print("Polly/S3 failed, returning script only:", e)
        url = None
    return {"audioUrl": url, "script": script}
