"""Alembic environment.

Imports Base.metadata from the installed packages/db package rather than
duplicating model definitions here. sqlalchemy.url is deliberately blank in
alembic.ini — it is always resolved at runtime from DATABASE_URL_SYNC (never
committed, never defaulted), so `alembic upgrade head` fails loudly instead
of silently targeting the wrong database if the env var is missing.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure packages/db (and packages/domain, which it depends on) are
# importable when Alembic is invoked from the repo root without the
# workspace having been `uv sync`-installed in editable mode.
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for pkg in ("db", "domain"):
    src = REPO_ROOT / "packages" / pkg / "src"
    if src.exists() and str(src) not in sys.path:
        sys.path.insert(0, str(src))

from atlasai_db.base import Base  # noqa: E402
from atlasai_db.models import *  # noqa: E402,F401,F403 — populates Base.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = os.environ.get("DATABASE_URL_SYNC")
if not database_url:
    raise RuntimeError(
        "DATABASE_URL_SYNC is not set. Alembic will not fall back to a "
        "hardcoded connection string — set it in the environment (see .env.example)."
    )
config.set_main_option("sqlalchemy.url", database_url)

target_metadata = Base.metadata

# Used only while hand-authoring the initial migration set, to generate one
# reviewable migration per table group in ERD dependency order instead of a
# single monolithic autogenerate diff (see docs/ADR for the migration list).
# Not used at normal migration-authoring time once the schema is stable —
# ALEMBIC_INCLUDE_TABLES is unset in every normal `alembic revision
# --autogenerate` run from that point on, so target_metadata is compared in
# full.
_include_tables_env = os.environ.get("ALEMBIC_INCLUDE_TABLES")
_include_tables = set(_include_tables_env.split(",")) if _include_tables_env else None


def _include_object(object_, name, type_, reflected, compare_to):  # noqa: ANN001
    if _include_tables is None:
        return True
    if type_ == "table":
        return name in _include_tables
    if hasattr(object_, "table"):
        return object_.table.name in _include_tables
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_object=_include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_object=_include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
