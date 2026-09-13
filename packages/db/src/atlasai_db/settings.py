"""Database, object-store, and embedding-dimension configuration.

EMBEDDING_DIMENSION is read once at import time (not via pydantic-settings)
because it fixes the width of the `evidence_chunks.embedding` pgvector
column at class-definition time — changing it is a schema change requiring
its own migration, not a runtime toggle (see docs/ADR/0002). It still comes
from the environment, never a value baked into a call site.
"""

from __future__ import annotations

import os

from pydantic_settings import BaseSettings, SettingsConfigDict

EMBEDDING_DIMENSION: int = int(os.environ.get("EMBEDDING_DIMENSION", "768"))


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    database_url: str
    database_url_sync: str


class ObjectStoreSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="object_store_", extra="ignore")

    endpoint_url: str
    region: str = "us-east-1"
    access_key: str
    secret_key: str
    bucket_raw: str
    bucket_extracted: str
    use_ssl: bool = False
