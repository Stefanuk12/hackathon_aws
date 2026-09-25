from shared.http import ok


def handler(event, context):
    # TODO person 3: body is {playerId, key} in draw rounds or {playerId, text} in survive/wit
    # rounds (trim to 200 chars). Put ROUND#<n>#<playerId> {s3Key} or {text}, publish "submission_in".
    # If every player has submitted: end_round.start_judging(code).
    return ok({"ok": True})
