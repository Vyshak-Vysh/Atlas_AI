"""The Connector protocol (TD_v2.md §3 / ATLASAI_MASTER_SPEC.md §8), verbatim.

Types are re-exported from atlasai_domain.contracts.connectors, which is
the single source of truth for their shape — this module only defines the
callable surface every provider adapter must implement.
"""

from __future__ import annotations

from typing import Protocol

from atlasai_domain.contracts.connectors import (
    AccountRef,
    AuthorizationRequest,
    AuthorizationResult,
    ExternalItem,
    HealthResult,
    NormalizedSource,
    ScopeItem,
    SyncPage,
)

__all__ = [
    "AccountRef",
    "AuthorizationRequest",
    "AuthorizationResult",
    "Connector",
    "ExternalItem",
    "HealthResult",
    "NormalizedSource",
    "ScopeItem",
    "SyncPage",
]


class Connector(Protocol):
    async def authorize(self, request: AuthorizationRequest) -> AuthorizationResult: ...

    async def discover_scope(self, account: AccountRef) -> list[ScopeItem]: ...

    async def sync(self, cursor: str | None) -> SyncPage: ...

    async def fetch_item(self, external_id: str) -> ExternalItem: ...

    async def normalize(self, item: ExternalItem) -> NormalizedSource: ...

    async def revoke(self) -> None: ...

    async def health_check(self) -> HealthResult: ...
