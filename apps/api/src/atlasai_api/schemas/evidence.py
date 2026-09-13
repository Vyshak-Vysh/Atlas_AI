from __future__ import annotations

from pydantic import BaseModel

from atlasai_domain.contracts.evidence import EvidenceCandidate


class EvidenceSearchResponse(BaseModel):
    query: str
    results: list[EvidenceCandidate]
