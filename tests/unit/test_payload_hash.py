"""Unit tests for action payload hashing (BD_v2.md §7 approval rules)."""

from __future__ import annotations

import uuid

from atlasai_domain.contracts.actions import ActionPayload
from atlasai_domain.enums import ActionType
from atlasai_security.payload_hash import hash_payload


def test_hash_is_stable_regardless_of_dict_key_order() -> None:
    project_id = uuid.uuid4()
    payload_a = ActionPayload(
        action_type=ActionType.DRAFT_CLIENT_RESPONSE,
        project_id=project_id,
        payload={"to": "client@example.com", "body": "hello"},
    )
    payload_b = ActionPayload(
        action_type=ActionType.DRAFT_CLIENT_RESPONSE,
        project_id=project_id,
        payload={"body": "hello", "to": "client@example.com"},
    )
    assert hash_payload(payload_a) == hash_payload(payload_b)


def test_hash_changes_when_payload_changes() -> None:
    """BD_v2.md §7: "Any payload change invalidates prior approval" — the
    hash is exactly the mechanism that makes that true."""
    project_id = uuid.uuid4()
    original = ActionPayload(
        action_type=ActionType.SEND_EMAIL, project_id=project_id, payload={"body": "Approved text."}
    )
    edited = ActionPayload(
        action_type=ActionType.SEND_EMAIL, project_id=project_id, payload={"body": "Approved text, edited."}
    )
    assert hash_payload(original) != hash_payload(edited)


def test_hash_is_a_sha256_hex_digest() -> None:
    payload = ActionPayload(
        action_type=ActionType.EXPORT_REPORT, project_id=uuid.uuid4(), payload={"format": "pdf"}
    )
    digest = hash_payload(payload)
    assert len(digest) == 64
    assert all(c in "0123456789abcdef" for c in digest)
