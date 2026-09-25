import json
from decimal import Decimal


def to_json(obj):
    """json.dumps that turns DynamoDB's Decimals back into ints (every number we store is whole)."""
    return json.dumps(obj, default=lambda o: int(o) if isinstance(o, Decimal) else str(o))


def ok(body, status=200):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": to_json(body),
    }


def error(message, status=400):
    return ok({"error": message}, status)


def body(event):
    """The request's JSON object, or {} if it's missing or not valid JSON (handlers validate fields)."""
    try:
        parsed = json.loads(event.get("body") or "{}")
    except ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def room_code(event):
    return event["pathParameters"]["code"].upper()
