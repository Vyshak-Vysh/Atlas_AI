"""Embedder microservice — a dedicated long-lived process serving
`BAAI/bge-base-en-v1.5`. Both apps/api's interactive evidence-search path
and apps/ai_atlas's batch ingestion tasks call this over HTTP rather than
loading the model in-process, so autoscaling/prefork churn never reloads
the ~440MB model (see the implementation plan's "Serving topology
decision").
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel, Field

from ai_atlas.embedder_service.model import embed_texts, get_model, model_info


class EmbedRequest(BaseModel):
    texts: list[str] = Field(min_length=1, max_length=256)
    is_query: bool = False


class EmbedResponse(BaseModel):
    embeddings: list[list[float]]
    model: str
    dimension: int


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    get_model()  # load once at startup, not on first request
    yield


app = FastAPI(title="AtlasAI Embedder", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str | int | bool]:
    info = model_info()
    return {"healthy": True, **info}


@app.post("/embed", response_model=EmbedResponse)
async def embed(body: EmbedRequest) -> EmbedResponse:
    vectors = embed_texts(body.texts, is_query=body.is_query)
    info = model_info()
    return EmbedResponse(embeddings=vectors, model=str(info["model"]), dimension=int(info["dimension"]))
