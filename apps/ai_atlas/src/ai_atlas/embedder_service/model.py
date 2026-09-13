"""BAAI/bge-base-en-v1.5 wrapper.

Two correctness details that are easy to get silently wrong with BGE models
(see the implementation plan's "Embeddings" section):

1. BGE is asymmetric — a *query* embedding needs the instruction prefix
   below; a *passage/document* embedding does not. Mixing this up doesn't
   error, it just quietly degrades retrieval quality.
2. Embeddings must be L2-normalized before storage so that pgvector's
   cosine operator (`vector_cosine_ops`) behaves as intended.

Both are enforced here, in the one place every embedding request passes
through, rather than left to each caller.
"""

from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from ai_atlas.settings import EmbedderServiceSettings

_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


class EmbeddingDimensionMismatch(Exception):
    pass


@lru_cache
def _settings() -> EmbedderServiceSettings:
    return EmbedderServiceSettings()


@lru_cache
def get_model() -> SentenceTransformer:
    """Loaded once per process (module-level cache) — see the
    implementation plan's "Serving topology decision" for why this runs as
    its own long-lived process rather than per-task in a Celery worker."""
    settings = _settings()
    model = SentenceTransformer(settings.embedding_model_name)
    actual_dim = model.get_embedding_dimension()
    if actual_dim != settings.embedding_dimension:
        raise EmbeddingDimensionMismatch(
            f"configured EMBEDDING_DIMENSION={settings.embedding_dimension} does not match "
            f"{settings.embedding_model_name}'s actual dimension {actual_dim}"
        )
    return model


def embed_texts(texts: list[str], *, is_query: bool) -> list[list[float]]:
    model = get_model()
    inputs = [f"{_QUERY_INSTRUCTION}{t}" for t in texts] if is_query else texts
    vectors = model.encode(inputs, normalize_embeddings=True, convert_to_numpy=True)
    return [vector.tolist() for vector in vectors]


def model_info() -> dict[str, str | int]:
    settings = _settings()
    return {"model": settings.embedding_model_name, "dimension": settings.embedding_dimension}
