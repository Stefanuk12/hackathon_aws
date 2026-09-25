"""Hear the host voice locally: builds the script from fake results and plays it.

Usage: python scripts/test_voice.py
Your hackathon login may not be allowed to use Polly; if so this prints the script only.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai.host_voice import build_script, polly  # noqa: E402

fake = [
    {"name": "Alex", "rank": 1, "score": 9, "roast": "That penguin has a better business plan than most startups."},
    {"name": "Sam", "rank": 2, "score": 6, "roast": "Is that a penguin or a bowling pin with ambition?"},
    {"name": "Jo", "rank": 3, "score": 2, "roast": "Writing 'PENGUIN' in capitals is not drawing, Jo."},
]
script = build_script(fake)
print(script)

try:
    audio = polly.synthesize_speech(Text=script, Engine="neural", VoiceId="Brian", OutputFormat="mp3")
except Exception as e:
    sys.exit(f"Polly failed ({e}). The script above is what would be spoken.")
out = ROOT / "host.mp3"
out.write_bytes(audio["AudioStream"].read())
subprocess.run(["afplay", str(out)])
