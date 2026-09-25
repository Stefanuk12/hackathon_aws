from shared.http import ok


def handler(event, context):
    # TODO person 3: put ROUND#<n>#<playerId> {s3Key}, publish "submission_in".
    # If every player has submitted: end_round.start_judging(code).
    return ok({"ok": True})
