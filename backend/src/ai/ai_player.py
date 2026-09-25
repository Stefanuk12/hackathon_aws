"""STRETCH: the AI draws its own entry and is judged blind alongside the humans.

Not wired in yet. To use it, call add_ai_entry(code, round_no, prompt) when a
round starts (e.g. from start_round), and add a PLAYER#ai row so it shows on
the scoreboard. The judge already names playerId "ai" as "The AI".
"""

import os

import boto3

from ai.reference import generate_image
from shared.db import entry_sk, room_pk, table

s3 = boto3.client("s3")

# Deliberately scrappy so it blends in with 60-second phone drawings.
AI_STYLE = (
    "A quick, messy doodle drawn with a finger on a phone in 60 seconds of: {prompt}. "
    "Wobbly black lines on white, childlike, a few flat colours."
)


def add_ai_entry(code, round_no, prompt):
    """Draw the prompt, upload it like a player's drawing, and record it as player "ai"."""
    image = generate_image(AI_STYLE.format(prompt=prompt))
    key = f"rooms/{code}/{round_no}/ai.jpg"
    s3.put_object(Bucket=os.environ["BUCKET_NAME"], Key=key, Body=image, ContentType="image/jpeg")
    table.put_item(Item={"PK": room_pk(code), "SK": entry_sk(round_no, "ai"), "s3Key": key})
    return key
