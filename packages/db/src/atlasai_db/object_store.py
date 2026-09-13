"""S3-compatible object storage client (MinIO in dev, any S3-compatible
provider in production via the same env-driven endpoint_url/credentials).

Raw uploaded files and extracted text are stored as separate objects/buckets
(TD_v2.md §4 "Store original object separately from extracted text") so the
original evidence stays byte-identical and immutable regardless of what
happens to derived text.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
from typing import Any

import boto3
from botocore.client import Config as BotoConfig

from atlasai_db.settings import ObjectStoreSettings


@dataclass(frozen=True)
class StoredObject:
    bucket: str
    key: str

    @property
    def uri(self) -> str:
        return f"s3://{self.bucket}/{self.key}"


@lru_cache
def _client_and_settings() -> tuple[Any, ObjectStoreSettings]:
    # boto3 ships no type stubs (see pyproject.toml's mypy overrides); its
    # client is typed as `Any` here deliberately, rather than the too-broad
    # `object` that made every call site fail with "has no attribute".
    settings = ObjectStoreSettings()
    client = boto3.client(
        "s3",
        endpoint_url=settings.endpoint_url,
        aws_access_key_id=settings.access_key,
        aws_secret_access_key=settings.secret_key,
        region_name=settings.region,
        use_ssl=settings.use_ssl,
        config=BotoConfig(signature_version="s3v4"),
    )
    return client, settings


class ObjectStoreClient:
    """Thin wrapper kept intentionally small — callers should not reach for
    boto3-specific behavior directly, so swapping providers later (or
    injecting a fake in tests) only touches this file."""

    def __init__(self) -> None:
        self._client, self._settings = _client_and_settings()

    @property
    def bucket_raw(self) -> str:
        return self._settings.bucket_raw

    @property
    def bucket_extracted(self) -> str:
        return self._settings.bucket_extracted

    @staticmethod
    def parse_uri(uri: str | None) -> tuple[str, str]:
        """Split a `s3://bucket/key` URI (as stored in e.g.
        source_versions.raw_object_uri) back into (bucket, key)."""
        if uri is None or not uri.startswith("s3://"):
            raise ValueError(f"unexpected object storage URI: {uri!r}")
        _, _, rest = uri.partition("s3://")
        bucket, _, key = rest.partition("/")
        return bucket, key

    def get_raw_bytes(self, key: str) -> bytes:
        return self.get_bytes(bucket=self.bucket_raw, key=key)

    def put_raw(self, *, key: str, data: bytes, content_type: str) -> StoredObject:
        return self._put(bucket=self._settings.bucket_raw, key=key, data=data, content_type=content_type)

    def put_extracted_text(self, *, key: str, text: str) -> StoredObject:
        return self._put(
            bucket=self._settings.bucket_extracted, key=key, data=text.encode("utf-8"), content_type="text/plain"
        )

    def _put(self, *, bucket: str, key: str, data: bytes, content_type: str) -> StoredObject:
        self._client.put_object(Bucket=bucket, Key=key, Body=BytesIO(data), ContentType=content_type)
        return StoredObject(bucket=bucket, key=key)

    def get_bytes(self, *, bucket: str, key: str) -> bytes:
        response = self._client.get_object(Bucket=bucket, Key=key)
        return bytes(response["Body"].read())

    def get_text(self, *, key: str) -> str:
        return self.get_bytes(bucket=self._settings.bucket_extracted, key=key).decode("utf-8")

    def delete(self, *, bucket: str, key: str) -> None:
        self._client.delete_object(Bucket=bucket, Key=key)

    def presigned_get_url(self, *, bucket: str, key: str, expires_seconds: int = 900) -> str:
        return str(
            self._client.generate_presigned_url(
                "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expires_seconds
            )
        )
