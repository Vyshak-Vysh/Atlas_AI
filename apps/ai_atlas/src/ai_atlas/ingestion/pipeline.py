"""The async ingestion pipeline: read a stored raw file, parse it, chunk
it, embed each chunk, persist evidence_chunks, then mark the source_record
"ready" by pointing current_version_id at the version that just finished
(ERD_FINAL.md has no separate ingestion-status column, so readiness is
signaled the ERD-native way — see the implementation plan's ingestion
design).

Exposed as a plain async function (not only as a Celery task body) so both
the Celery task (ingestion/tasks.py) and tests can call it directly without
needing a running worker.
"""

from __future__ import annotations

import uuid

from atlasai_connectors.manual_upload.parsers import parse_document
from atlasai_db.engine import get_async_sessionmaker
from atlasai_db.models.evidence import EvidenceChunk
from atlasai_db.object_store import ObjectStoreClient
from atlasai_db.repositories.evidence import EvidenceChunkRepository, SourceRecordRepository, SourceVersionRepository
from atlasai_retrieval.embedder_client import EmbedderClient, get_embedder_settings


async def ingest_source_version(
    *, tenant_id: uuid.UUID, source_record_id: uuid.UUID, source_version_id: uuid.UUID
) -> int:
    """Returns the number of evidence_chunks written."""
    session_factory = get_async_sessionmaker()
    object_store = ObjectStoreClient()
    embedder = EmbedderClient()
    embedder_settings = get_embedder_settings()

    async with session_factory() as session:
        source_repo = SourceRecordRepository(session, tenant_id=tenant_id)
        version_repo = SourceVersionRepository(session)
        chunk_repo = EvidenceChunkRepository(session, tenant_id=tenant_id)

        source_record = await source_repo.get_by_id(source_record_id)
        versions = await version_repo.list_for_source_record(source_record_id)
        version = next(v for v in versions if v.id == source_version_id)

        _, raw_key = object_store.parse_uri(version.raw_object_uri)
        raw_bytes = object_store.get_raw_bytes(raw_key)
        mime_type = version.metadata_.get("mime_type", "text/plain")
        parsed = parse_document(raw_bytes, mime_type)

        extracted_key = f"{tenant_id}/{source_record_id}/{version.version_key}/extracted.txt"
        stored_text = object_store.put_extracted_text(key=extracted_key, text=parsed.full_text)
        version.extracted_text_uri = stored_text.uri

        if not parsed.chunks:
            await session.commit()
            return 0

        try:
            vectors = await embedder.embed_documents([c.content for c in parsed.chunks])
        finally:
            await embedder.aclose()

        rows = [
            EvidenceChunk(
                tenant_id=tenant_id,
                source_version_id=source_version_id,
                chunk_index=index,
                content=chunk.content,
                page_number=chunk.page_number,
                section_path=chunk.section_path,
                sheet_name=chunk.sheet_name,
                cell_range=chunk.cell_range,
                speaker=chunk.speaker,
                start_ms=chunk.start_ms,
                end_ms=chunk.end_ms,
                embedding_model=embedder_settings.embedding_model_name,
                embedding=vector,
            )
            for index, (chunk, vector) in enumerate(zip(parsed.chunks, vectors, strict=True))
        ]
        await chunk_repo.bulk_create(rows)

        source_record.current_version_id = source_version_id
        await session.commit()
        return len(rows)
