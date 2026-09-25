"""One S3 client for every Lambda, set up so presigned URLs work from a browser."""

import os

import boto3
from botocore.config import Config

# The default client signs URLs for the global s3.amazonaws.com host. For a bucket in
# eu-west-2 that answers with a redirect, which breaks the phones' CORS upload.
# A regional endpoint + SigV4 gives URLs that work first time.
s3 = boto3.client(
    "s3",
    endpoint_url=f"https://s3.{os.environ.get('AWS_REGION', 'eu-west-2')}.amazonaws.com",
    config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
)


def bucket():
    return os.environ["BUCKET_NAME"]


def drawing_key(code, round_no, player_id):
    return f"rooms/{code}/{round_no}/{player_id}.jpg"


def put(key, data, content_type):
    s3.put_object(Bucket=bucket(), Key=key, Body=data, ContentType=content_type)


def get(key):
    return s3.get_object(Bucket=bucket(), Key=key)["Body"].read()


def presign_get(key, expires=3600):
    return s3.generate_presigned_url("get_object", Params={"Bucket": bucket(), "Key": key}, ExpiresIn=expires)


def presign_put(key, content_type, expires=300):
    return s3.generate_presigned_url(
        "put_object", Params={"Bucket": bucket(), "Key": key, "ContentType": content_type}, ExpiresIn=expires
    )
