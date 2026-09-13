"""Manual upload as a Connector-protocol-conformant adapter.

Manual upload is push-driven (a user posts a file to `POST
/api/v1/documents/upload`), not pull/cursor-driven like every other
connector, so most of the Connector protocol is a deliberate no-op here —
this class exists for registry consistency (every provider, including this
one, is reachable the same way) rather than because uploads are ever
`sync()`-ed. The real ingestion path is
apps/ai_atlas/ingestion/tasks.py:ingest_source_version, invoked directly by
the upload endpoint.
"""

from __future__ import annotations

from datetime import UTC, datetime

from atlasai_connectors.protocol import (
    AccountRef,
    AuthorizationRequest,
    AuthorizationResult,
    ExternalItem,
    HealthResult,
    NormalizedSource,
    ScopeItem,
    SyncPage,
)
from atlasai_domain.enums import ConnectorProvider


class ManualUploadConnector:
    async def authorize(self, request: AuthorizationRequest) -> AuthorizationResult:
        return AuthorizationResult(
            provider=ConnectorProvider.MANUAL_UPLOAD, external_account_id="manual", credential_ref="manual"
        )

    async def discover_scope(self, account: AccountRef) -> list[ScopeItem]:
        return []

    async def sync(self, cursor: str | None) -> SyncPage:
        return SyncPage(items=[], next_cursor=None, has_more=False)

    async def fetch_item(self, external_id: str) -> ExternalItem:
        raise NotImplementedError("manual uploads are ingested directly at upload time, never fetched by id")

    async def normalize(self, item: ExternalItem) -> NormalizedSource:
        raise NotImplementedError("manual uploads are normalized directly at upload time")

    async def revoke(self) -> None:
        return None

    async def health_check(self) -> HealthResult:
        return HealthResult(
            healthy=True, detail="manual upload has no external dependency", checked_at=datetime.now(UTC)
        )
