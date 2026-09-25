"""Publish to AppSync Events channel /rooms/<code>. See contracts/events.md."""

import json
import os
import urllib.request

from shared.http import to_json


def publish(code, event_type, **payload):
    """Best effort: clients also poll GET /rooms/{code}, so a failed publish must never fail the request."""
    try:
        return _post(code, event_type, payload)
    except Exception as e:
        print(f"Publish {event_type} to {code} failed:", e)


def _post(code, event_type, payload):
    req = urllib.request.Request(
        f"https://{os.environ['EVENTS_HTTP_DOMAIN']}/event",
        data=json.dumps(
            {
                "channel": f"/rooms/{code}",
                "events": [to_json({"type": event_type, **payload})],
            }
        ).encode(),
        headers={
            "Content-Type": "application/json",
            "x-api-key": os.environ["EVENTS_API_KEY"],
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.status
