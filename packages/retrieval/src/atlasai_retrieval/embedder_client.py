"""HTTP client for the embedder microservice (apps/ai_atlas/embedder_service).

Shared by apps/api (one query embedding per search request) and
apps/ai_atlas's ingestion tasks (batch document embeddings) — both hit the
same warm, long-lived model process rather than loading the model
themselves (see the implementation plan's "Serving topology decision").
"""

from __future__ import annotations

from functools import lru_cache

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmbedderClientSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    embedder_base_url: str
    embedding_model_name: str
    embedding_dimension: int = 768


class EmbedderClient:
    def __init__(self, *, timeout_seconds: float = 30.0) -> None:
        self._settings = EmbedderClientSettings()
        self._client = httpx.AsyncClient(base_url=self._settings.embedder_base_url, timeout=timeout_seconds)

    async def embed_query(self, text: str) -> list[float]:
        vectors = await self._embed([text], is_query=True)
        return vectors[0]

    async def embed_documents(self, texts: list[str], *, batch_size: int = 32) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            vectors.extend(await self._embed(batch, is_query=False))
        return vectors

    async def _embed(self, texts: list[str], *, is_query: bool) -> list[list[float]]:
        response = await self._client.post("/embed", json={"texts": texts, "is_query": is_query})
        response.raise_for_status()
        payload = response.json()
        return list(payload["embeddings"])

    async def aclose(self) -> None:
        await self._client.aclose()


@lru_cache
def get_embedder_settings() -> EmbedderClientSettings:
    return EmbedderClientSettings()
