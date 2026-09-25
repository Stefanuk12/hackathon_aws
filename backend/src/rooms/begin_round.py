from shared.http import ok


def handler(event, context):
    # Themed rounds: the host screen calls this when the theme intro ends (timer or Skip).
    # TODO person 3: conditional update META state "theme" -> "drawing" (so a double call is harmless),
    # set endsAt = now + round length, publish "round_started" {round, roundMode, prompt, endsAt}.
    return ok({"ok": True})
