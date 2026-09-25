from shared.http import ok


def handler(event, context):
    # TODO person 3: generate a 4-letter code, put META {state: "lobby", round: 0}.
    return ok({"code": "WXYZ"})
