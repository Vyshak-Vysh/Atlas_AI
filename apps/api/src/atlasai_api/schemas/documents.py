from __future__ import annotations

import uuid

from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    source_record_id: uuid.UUID
    source_version_id: uuid.UUID
    content_hash: str
    status: str  # "PROCESSING" — ingestion runs asynchronously
