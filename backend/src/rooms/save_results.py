def handler(event, context):
    """Last step of the judge state machine.

    Input: {code, round, judge: {results}, voice?: {audioUrl}}
    TODO person 3: write rank/score/roast (+ survived) onto ROUND# items.
    If META.elimination: run shared.elimination.apply_elimination(players, scores, META.reviveAfter)
    (non-submitters score 0), save alive/streak on PLAYER# items, points + ghost on ROUND# items,
    and META.outcome = {eliminated, revived}. Otherwise points = score.
    Add points to PLAYER# scores,
    set META state "results" + audioUrl, publish "results_ready".
    """
    return {"ok": True}
