import json


def ok(body, status=200):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, default=str),
    }


def error(message, status=400):
    return ok({"error": message}, status)


def body(event):
    return json.loads(event.get("body") or "{}")


def room_code(event):
    return event["pathParameters"]["code"].upper()
