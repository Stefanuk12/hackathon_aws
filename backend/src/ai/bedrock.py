"""Shared Bedrock client and helpers for the AI modules."""

import boto3

bedrock = boto3.client("bedrock-runtime")


def reply_text(resp):
    """Return the answer text from a Converse response.

    Newer Claude models send a "thinking" block before the answer, so the answer
    is not always content[0]. Take the first block that actually has text.
    """
    return next(b["text"] for b in resp["output"]["message"]["content"] if "text" in b)
