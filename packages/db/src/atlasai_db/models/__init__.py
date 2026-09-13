"""Import every model module so `Base.metadata` is fully populated before
Alembic (or `create_all` in tests) inspects it. Order matters only for
readability here — SQLAlchemy resolves FK references across modules at
mapper-configuration time, not import time.
"""

from atlasai_db.models import (  # noqa: F401
    actions,
    agent,
    audit,
    auth,
    connectors,
    evidence,
    findings,
    requirements,
    tenancy,
)

__all__ = [
    "actions",
    "agent",
    "audit",
    "auth",
    "connectors",
    "evidence",
    "findings",
    "requirements",
    "tenancy",
]
