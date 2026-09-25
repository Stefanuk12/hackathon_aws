def handler(event, context):
    """Last step of the judge state machine.

    Input: {code, round, judge: {results}, voice?: {audioUrl}}
    TODO person 3: write rank/score/roast onto ROUND# items, add to PLAYER# scores,
    set META state "results" + audioUrl, publish "results_ready".
    """
    return {"ok": True}
