"""Run the real API on your laptop, against real AWS.

The hackathon account can't deploy: CloudFormation and IAM are both denied, so there are
no Lambda roles and no stack. But DynamoDB, S3 and Bedrock all work, so this serves the
same rooms/ handlers over HTTP instead of API Gateway, using the real tables and models.

What changes compared with the deployed stack:
  * Step Functions -> the judge pipeline runs here, in a thread (same order as judge_round.asl.json).
  * AppSync Events -> nothing to publish to; the screens already fall back to polling.
  * Polly          -> denied in this account, so host_voice returns a script and the host
                      screen reads it aloud with the browser's own speech.

Usage:
    python scripts/serve_local.py                 # http://0.0.0.0:8000, phones on the LAN can reach it
    python scripts/serve_local.py --port 9000
Point the frontend at it with VITE_API_URL, then `npm run dev`.
"""

import argparse
import json
import os
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Real resources in the regions this account allows (see README: no CloudFormation/IAM here).
os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("TABLE_NAME", "amacide")
os.environ.setdefault("BUCKET_NAME", "amacide-985539753760")
os.environ.setdefault("TEXT_REGION", "us-west-2")
os.environ.setdefault("TEXT_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
os.environ.setdefault("IMAGE_REGION", "us-west-2")
os.environ.setdefault("IMAGE_MODEL_ID", "stability.stable-image-core-v1:1")
os.environ.setdefault("JUDGE_STATE_MACHINE_ARN", "local")  # end_round reads it; never used here

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai import host_voice, judge  # noqa: E402
from rooms import (  # noqa: E402
    begin_round, create_room, end_round, get_room, join_room, reset_room, save_results, start_round, submit, upload_url,
)

ROUTES = [
    ("POST", r"^/rooms$", create_room),
    ("POST", r"^/rooms/(?P<code>[A-Za-z]{4})/join$", join_room),
    ("GET", r"^/rooms/(?P<code>[A-Za-z]{4})$", get_room),
    ("POST", r"^/rooms/(?P<code>[A-Za-z]{4})/start$", start_round),
    ("POST", r"^/rooms/(?P<code>[A-Za-z]{4})/upload-url$", upload_url),
    ("POST", r"^/rooms/(?P<code>[A-Za-z]{4})/submit$", submit),
    ("POST", r"^/rooms/(?P<code>[A-Za-z]{4})/end$", end_round),
    ("POST", r"^/rooms/(?P<code>[A-Za-z]{4})/begin$", begin_round),
    ("POST", r"^/rooms/(?P<code>[A-Za-z]{4})/reset$", reset_room),
]
ROUTES = [(method, re.compile(pattern), mod) for method, pattern, mod in ROUTES]


def judge_round(code, round_no):
    """What judge_round.asl.json does: Judge -> HostVoice (failures tolerated) -> SaveResults."""
    try:
        judged = judge.handler({"code": code, "round": round_no}, None)
        try:
            voice = host_voice.handler({"code": code, "round": round_no, "judge": judged}, None)
        except Exception as e:  # the state machine has a Catch here too
            print(f"[{code}] host voice failed:", e)
            voice = {}
        save_results.handler({"code": code, "round": round_no, "judge": judged, "voice": voice}, None)
        print(f"[{code}] round {round_no} judged: {len(judged['results'])} results")
    except Exception as e:
        # Put the room back so the host's "End round now" can retry, like the real stack does.
        print(f"[{code}] judging failed:", e)
        end_round._set_state(code, "drawing", "judging")


class _LocalStepFunctions:
    """Stands in for the Step Functions client: runs the pipeline in a thread instead."""

    def start_execution(self, **kw):
        event = json.loads(kw["input"])
        threading.Thread(
            target=judge_round, args=(event["code"], event["round"]), daemon=True
        ).start()
        return {"executionArn": "local"}


end_round.sfn = _LocalStepFunctions()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, status, body=b"", content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        # The phones load the page from Vite/S3, so every response needs CORS.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(204)

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def _handle(self, method):
        path = self.path.split("?", 1)[0].rstrip("/") or "/rooms"
        for route_method, pattern, mod in ROUTES:
            match = pattern.match(path)
            if not match:
                continue
            if route_method != method:
                return self._send(405, b'{"error":"Method not allowed"}')

            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length).decode() if length else ""
            params = {k: v.upper() for k, v in match.groupdict().items()}
            event = {"pathParameters": params, "body": raw}
            try:
                resp = mod.handler(event, None)
            except Exception as e:
                print(f"!! {method} {path} raised:", e)
                return self._send(500, json.dumps({"error": str(e)}).encode())
            return self._send(resp["statusCode"], resp["body"].encode())
        self._send(404, b'{"error":"No such route"}')

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} {fmt % args}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    print(f"Amacide API on http://{args.host}:{args.port}")
    print(f"  table {os.environ['TABLE_NAME']} / bucket {os.environ['BUCKET_NAME']} ({os.environ['AWS_REGION']})")
    print(f"  Bedrock {os.environ['TEXT_MODEL_ID']} ({os.environ['TEXT_REGION']})")
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
