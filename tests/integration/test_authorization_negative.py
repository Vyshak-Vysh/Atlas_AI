"""Negative-authorization integration tests (BR-002, ERD_FINAL.md critical
integrity rule #8, ATLASAI_MASTER_SPEC.md §15 step 12: "Attempt an
unauthorized project query and verify denial plus audit event").

Every case here follows the same shape: tenant A creates a project, tenant
B's user (no membership in tenant A at all) tries to reach it, and the
request must be denied (404, existence not revealed) with an ACCESS_DENIED
audit event recorded against the resource owner's tenant.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


async def _register_and_get_project(client: AsyncClient, email: str) -> dict:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "tenant_name": f"Owner Co {email}",
            "email": email,
            "password": "a-very-long-test-password-1",
            "display_name": "Owner",
        },
    )
    assert reg.status_code == 201, reg.text
    owner = reg.json()

    proj = await client.post(
        "/api/v1/projects",
        json={"tenant_id": owner["tenant_id"], "name": "Confidential Project"},
        headers={"Authorization": f"Bearer {owner['access_token']}"},
    )
    assert proj.status_code == 201, proj.text
    return {"owner": owner, "project": proj.json()}


async def _register_intruder(client: AsyncClient, email: str) -> dict:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "tenant_name": f"Intruder Co {email}",
            "email": email,
            "password": "another-long-test-password-1",
            "display_name": "Intruder",
        },
    )
    assert reg.status_code == 201, reg.text
    return reg.json()


@pytest.fixture
def intruder_email(unique_email: str) -> str:
    return f"intruder-{unique_email}"


async def test_cross_tenant_project_overview_is_denied(
    client: AsyncClient, unique_email: str, intruder_email: str
) -> None:
    setup = await _register_and_get_project(client, unique_email)
    intruder = await _register_intruder(client, intruder_email)

    response = await client.get(
        f"/api/v1/projects/{setup['project']['id']}/overview",
        headers={"Authorization": f"Bearer {intruder['access_token']}"},
    )
    assert response.status_code == 404  # never 403 — existence is not revealed

    audit = await client.get(
        f"/api/v1/audit-events?tenant_id={setup['owner']['tenant_id']}",
        headers={"Authorization": f"Bearer {setup['owner']['access_token']}"},
    )
    events = audit.json()
    assert any(
        e["event_type"] == "ACCESS_DENIED" and e["target_type"] == "project" for e in events
    ), "cross-tenant denial must be audited on the owning tenant"


async def test_cross_tenant_evidence_search_is_denied(
    client: AsyncClient, unique_email: str, intruder_email: str
) -> None:
    setup = await _register_and_get_project(client, unique_email)
    intruder = await _register_intruder(client, intruder_email)

    response = await client.get(
        f"/api/v1/evidence/search?project_id={setup['project']['id']}&q=anything",
        headers={"Authorization": f"Bearer {intruder['access_token']}"},
    )
    assert response.status_code == 404


async def test_cross_tenant_document_upload_is_denied(
    client: AsyncClient, unique_email: str, intruder_email: str
) -> None:
    setup = await _register_and_get_project(client, unique_email)
    intruder = await _register_intruder(client, intruder_email)

    response = await client.post(
        "/api/v1/documents/upload",
        data={"project_id": str(setup["project"]["id"])},
        files={"file": ("note.txt", b"some text", "text/plain")},
        headers={"Authorization": f"Bearer {intruder['access_token']}"},
    )
    assert response.status_code == 404


async def test_cross_tenant_agent_run_is_denied(client: AsyncClient, unique_email: str, intruder_email: str) -> None:
    setup = await _register_and_get_project(client, unique_email)
    intruder = await _register_intruder(client, intruder_email)

    response = await client.post(
        f"/api/v1/agent/runs?project_id={setup['project']['id']}",
        json={"project_id": setup["project"]["id"], "question": "Is feature X in scope?"},
        headers={"Authorization": f"Bearer {intruder['access_token']}"},
    )
    assert response.status_code == 404


async def test_cross_tenant_audit_log_is_denied(client: AsyncClient, unique_email: str, intruder_email: str) -> None:
    setup = await _register_and_get_project(client, unique_email)
    intruder = await _register_intruder(client, intruder_email)

    response = await client.get(
        f"/api/v1/audit-events?tenant_id={setup['owner']['tenant_id']}",
        headers={"Authorization": f"Bearer {intruder['access_token']}"},
    )
    assert response.status_code == 404
