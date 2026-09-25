"""Generate reference images of the round prompt with a Stability model on Bedrock.

The judge compares players' drawings against these to decide what the key
elements of the prompt are.
"""

import base64
import json
import os
from concurrent.futures import ThreadPoolExecutor

from ai.bedrock import bedrock

REFERENCE_STYLE = "A simple black marker doodle on a white background of: {prompt}. Few lines, no shading."
NEGATIVE = "text, letters, words, writing, photorealistic, shading"


def generate_image(text, negative=NEGATIVE):
    """One text-to-image call. Returns JPEG bytes."""
    resp = bedrock.invoke_model(
        modelId=os.environ.get("IMAGE_MODEL_ID", "stability.stable-image-core-v1:1"),
        body=json.dumps(
            {
                "prompt": text,
                "negative_prompt": negative,
                "output_format": "jpeg",
                "aspect_ratio": "1:1",
            }
        ),
    )
    return base64.b64decode(json.loads(resp["body"].read())["images"][0])


def generate_references(prompt, count=2):
    """Returns `count` reference doodles of the prompt (JPEG bytes).

    The model makes one image per call, so the calls run at the same time
    (about 4 seconds in total instead of 4 seconds each).
    """
    text = REFERENCE_STYLE.format(prompt=prompt)
    with ThreadPoolExecutor(max_workers=count) as pool:
        return list(pool.map(lambda _: generate_image(text), range(count)))
