"""AWS-service themes for themed rounds. The catalogue lives in themes.json (the
frontend mock reads the same file). The room sends the chosen theme to clients,
minus the prompt-writing fields."""

import json
import random
from pathlib import Path

THEMES = json.loads((Path(__file__).parent / "themes.json").read_text())
INTRO_SECONDS = 20
# Only the backend needs these; everything else is shown on the theme intro screen.
_PRIVATE = ("promptHint", "examples")


def is_themed(round_no, theme_every):
    """theme_every: 0 = off, 1 = every round, 2 = every 2nd round (1, 3, 5...)."""
    return theme_every > 0 and (round_no - 1) % theme_every == 0


def pick_theme(used_ids=()):
    fresh = [t for t in THEMES if t["id"] not in used_ids]
    return random.choice(fresh or THEMES)


def public(theme):
    """The theme as sent to clients in room.theme."""
    return {k: v for k, v in theme.items() if k not in _PRIVATE}


def prompt_theme(theme, mode):
    """The `theme` string for ai.prompt_gen.generate_prompt()."""
    return f"{theme['service']} ({theme['promptHint']}). Example of the style: \"{theme['examples'][mode]}\""
