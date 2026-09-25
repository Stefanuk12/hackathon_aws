"""Generate reference images of the round prompt with a Bedrock image model.

The judge compares players' drawings against these to decide what the key
elements of the prompt are.

Works with Stability models (the template default) and Amazon Nova Canvas, which
take different request bodies. The hackathon account blocks Bedrock in eu-west-2 and
Nova Canvas is legacy, so images come from Stability Image Core in IMAGE_REGION (us-west-2).
"""

import base64
import json
import os
from concurrent.futures import ThreadPoolExecutor

import boto3

bedrock_images = boto3.client("bedrock-runtime", region_name=os.environ.get("IMAGE_REGION") or None)

REFERENCE_STYLE = "A simple black marker doodle on a white background of: {prompt}. Few lines, no shading."
NEGATIVE = "text, letters, words, writing, photorealistic, shading"


def _model():
    return os.environ.get("IMAGE_MODEL_ID", "stability.stable-image-core-v1:1")


def _invoke(body):
    resp = bedrock_images.invoke_model(modelId=_model(), body=json.dumps(body))
    return [base64.b64decode(img) for img in json.loads(resp["body"].read())["images"]]


def generate_images(text, count=1, negative=NEGATIVE):
    """Returns `count` images (bytes: PNG from Nova Canvas, JPEG from Stability)."""
    if "nova-canvas" in _model():
        # Nova Canvas makes several images in one call.
        return _invoke(
            {
                "taskType": "TEXT_IMAGE",
                "textToImageParams": {"text": text, "negativeText": negative},
                "imageGenerationConfig": {"numberOfImages": count, "width": 512, "height": 512, "quality": "standard"},
            }
        )
    # Stability makes one image per call, so run the calls at the same time.
    body = {"prompt": text, "negative_prompt": negative, "output_format": "jpeg", "aspect_ratio": "1:1"}
    with ThreadPoolExecutor(max_workers=count) as pool:
        return list(pool.map(lambda _: _invoke(body)[0], range(count)))


def generate_image(text, negative=NEGATIVE):
    """One image (bytes)."""
    return generate_images(text, 1, negative)[0]


def generate_references(prompt, count=2):
    """Returns `count` reference doodles of the prompt (image bytes)."""
    return generate_images(REFERENCE_STYLE.format(prompt=prompt), count)


def image_format(data):
    """Return "png" or "jpeg", from the file's first bytes. Bedrock and browsers need the real type."""
    return "png" if data[:4] == b"\x89PNG" else "jpeg"
