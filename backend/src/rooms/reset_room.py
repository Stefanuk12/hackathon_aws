from shared.http import ok


def handler(event, context):
    # TODO person 3: "Play again". META -> {state: "lobby", round: 0, prompt/roundMode/results cleared, mode kept},
    # every PLAYER# -> score 0, alive true, streak 0 (keep the players), publish "room_reset".
    return ok({"ok": True})
