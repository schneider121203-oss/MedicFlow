from functools import lru_cache

import boto3
from botocore.exceptions import ClientError

from backend.config import settings


@lru_cache
def get_s3_client():
    kwargs = {"region_name": settings.aws_region}
    if settings.s3_endpoint_url:
        kwargs["endpoint_url"] = settings.s3_endpoint_url
    if settings.s3_access_key and settings.s3_secret_key:
        kwargs["aws_access_key_id"] = settings.s3_access_key
        kwargs["aws_secret_access_key"] = settings.s3_secret_key
    return boto3.client("s3", **kwargs)


def ensure_bucket() -> None:
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=settings.s3_bucket)
    except ClientError:
        client.create_bucket(Bucket=settings.s3_bucket)


def upload_file(path: str, object_key: str, content_type: str) -> None:
    ensure_bucket()
    get_s3_client().upload_file(
        path,
        settings.s3_bucket,
        object_key,
        ExtraArgs={"ContentType": content_type, "ServerSideEncryption": "AES256"}
        if not settings.s3_endpoint_url
        else {"ContentType": content_type},
    )


def download_file(object_key: str, path: str) -> None:
    get_s3_client().download_file(settings.s3_bucket, object_key, path)


def delete_file(object_key: str) -> None:
    get_s3_client().delete_object(Bucket=settings.s3_bucket, Key=object_key)
