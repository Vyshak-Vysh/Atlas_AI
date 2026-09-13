"""evidence chunks embedding hnsw index

Revision ID: be387e2b8fd0
Revises: 8f514b96a119
Create Date: 2026-09-12 19:58:09.151714
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'be387e2b8fd0'
down_revision: Union[str, None] = '8f514b96a119'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # docs/ERD_FINAL.md §4 explicitly warns not to build this index before
    # corpus size justifies it, and to benchmark HNSW against IVFFlat for
    # your own data. It is still included in the default `upgrade head`
    # path (a single linear migration history is far simpler to operate
    # than branching migrations gated on a runtime flag) — an operator with
    # a very small corpus can simply stop one revision short of this one,
    # or drop the index afterwards, until it's worth the build/maintenance
    # cost. HNSW (not IVFFlat) is used because unlike IVFFlat it needs no
    # pre-built-list-count tuning and its recall/latency tradeoff is
    # controlled at query time via `hnsw.ef_search`, which suits a corpus
    # that grows continuously rather than being bulk-loaded once.
    op.execute(
        "CREATE INDEX ix_evidence_chunks_embedding_hnsw "
        "ON evidence_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_evidence_chunks_embedding_hnsw")
