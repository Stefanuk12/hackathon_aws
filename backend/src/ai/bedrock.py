"""Shared Bedrock client and helpers for the AI modules."""

import os

import boto3

# The hackathon account blocks Bedrock in eu-west-2, so text calls go to TEXT_REGION (us-west-2).
bedrock = boto3.client("bedrock-runtime", region_name=os.environ.get("TEXT_REGION") or None)


def reply_text(resp):
    """Return the answer text from a Converse response.

    Newer Claude models send a "thinking" block before the answer, so the answer
    is not always content[0]. Take the first block that actually has text.
    """
    return next(b["text"] for b in resp["output"]["message"]["content"] if "text" in b)
