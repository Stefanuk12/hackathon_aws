from shared.http import ok


def handler(event, context):
    # TODO person 3: "Play again". META -> {state: "lobby", round: 0, prompt/results cleared},
    # every PLAYER# score -> 0 (keep the players), publish "room_reset".
    return ok({"ok": True})
