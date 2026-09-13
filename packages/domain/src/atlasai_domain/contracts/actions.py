"""Action/approval contracts (BD_v2.md §7 approval rules).

An action's payload is frozen and hashed at PROPOSE_ACTION time; an
approval is only valid for the exact payload hash it was granted against,
and only before it expires. `packages/security` provides the hashing
helper (`hash_payload`) that both apps/api and apps/ai_atlas use so the two
sides of a hash comparison are always computed the same way.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from atlasai_domain.enums import ActionType


class ActionPayload(BaseModel):
    """The immutable content an approval binds to via its hash."""

    action_type: ActionType
    project_id: UUID
    payload: dict[str, Any]

    def canonical_json(self) -> str:
        """Deterministic JSON used as the hash input — sorted keys, no
        whitespace, so semantically identical payloads always hash equal
        regardless of dict insertion order."""
        import json

        return json.dumps(
            {"action_type": self.action_type.value, "project_id": str(self.project_id), "payload": self.payload},
            sort_keys=True,
            separators=(",", ":"),
        )


class ApprovalRequest(BaseModel):
    action_id: UUID
    approver_id: UUID
    decision: str  # ApprovalDecision, kept as str to mirror the DB check constraint
    reason: str | None = None
    payload_hash: str = Field(min_length=64, max_length=64)
    expires_at: datetime
