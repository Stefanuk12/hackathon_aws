"""Publish to AppSync Events channel /rooms/<code>. See contracts/events.md."""

import json
import os
import urllib.request


def publish(code, event_type, **payload):
    req = urllib.request.Request(
        f"https://{os.environ['EVENTS_HTTP_DOMAIN']}/event",
        data=json.dumps(
            {
                "channel": f"/rooms/{code}",
                "events": [json.dumps({"type": event_type, **payload}, default=str)],
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
