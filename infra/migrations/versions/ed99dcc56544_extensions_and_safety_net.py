"""extensions and safety net

Revision ID: ed99dcc56544
Revises: 
Create Date: 2026-09-12 19:48:18.900475
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'ed99dcc56544'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Idempotent safety net — infra/migrations/docker-initdb/001_extensions.sql
    # already runs these against a brand-new container, but a restored
    # backup or a managed cloud Postgres instance may skip that init path.
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    # Extensions are left in place on downgrade — dropping pgcrypto/citext/
    # vector could break other schemas/roles sharing the same database and
    # is not required to reverse this migration's own effect.
    pass
