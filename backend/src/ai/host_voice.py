"""Game-show host voice for the reveal, via Polly."""


def handler(event, context):
    """Step Functions task. Input: {code, round, judge: {results}}. Output: {audioUrl}.

    TODO person 4: build a short script (winner first, a couple of roasts),
    polly.synthesize_speech(Engine="neural", VoiceId="Brian", OutputFormat="mp3"),
    put to S3 at rooms/<code>/<round>/host.mp3, return a presigned GET URL.
    """
    return {"audioUrl": None}
