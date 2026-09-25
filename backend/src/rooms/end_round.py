from shared.http import ok


def start_judging(code):
    """Move drawing -> judging exactly once, then start the judge state machine.

    TODO person 3: conditional update on META (state = "drawing"); if it succeeds,
    publish "judging" and sfn.start_execution(JUDGE_STATE_MACHINE_ARN, {code, round}).
    """


def handler(event, context):
    # Called by the host screen when the timer hits 0.
    return ok({"ok": True})
