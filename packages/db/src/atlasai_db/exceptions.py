"""Repository-layer exceptions.

`NotFoundError` is deliberately the *only* thing a cross-tenant/cross-project
access attempt ever raises — never a distinct "forbidden" exception — so
that API error responses never leak whether a row exists in a tenant/project
the caller cannot see (ERD_FINAL.md critical integrity rule #8).
"""

from __future__ import annotations


class NotFoundError(Exception):
    def __init__(self, model_name: str, identifier: object) -> None:
        self.model_name = model_name
        self.identifier = identifier
        super().__init__(f"{model_name} not found: {identifier}")


class ConflictError(Exception):
    """Raised on a unique-constraint violation surfaced as a domain-level
    conflict (e.g. duplicate idempotency_key, duplicate slug)."""
