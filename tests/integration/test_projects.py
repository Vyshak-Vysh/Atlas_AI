"""Integration tests for project deletion — there was previously no way
to delete a project at all (no endpoint existed). Deleting cascades
through the project's own tasks/findings/actions/connectors (every
child table's project_id FK is ON DELETE CASCADE) but must never touch
evidence/source records, since those live at the tenant level and can be
in scope for more than one project (ADR-0008)."""

from __future__ import annotations

import uuid

import pytest
from _helpers import add_project_member_with_role, create_project, register
from httpx import AsyncClient

pytestmark = pytest.mark.integration


async def test_delete_project_removes_it_and_its_tasks(client: AsyncClient, unique_email: str) -> None:
    owner = await register(client, email=unique_email)
    headers = {"Authorization": f"Bearer {owner['access_token']}"}
    project = await create_project(client, owner=owner)

    task = await client.post(
        f"/api/v1/requirements?project_id={project['id']}",
        json={"key": "T-1", "title": "Will be cascade-deleted", "status": "PROPOSED"},
        headers=headers,
    )
    assert task.status_code == 201, task.text

    deleted = await client.delete(f"/api/v1/projects/{project['id']}", headers=headers)
    assert deleted.status_code == 204

    # The project itself is gone — any project-scoped lookup now 404s.
    missing = await client.get(f"/api/v1/projects/{project['id']}/overview", headers=headers)
    assert missing.status_code == 404


async def test_delete_project_records_an_audit_event_that_survives_the_project(
    client: AsyncClient, unique_email: str
) -> None:
    owner = await register(client, email=unique_email)
    headers = {"Authorization": f"Bearer {owner['access_token']}"}
    project = await create_project(client, owner=owner, name="Doomed Project")

    deleted = await client.delete(f"/api/v1/projects/{project['id']}", headers=headers)
    assert deleted.status_code == 204

    audit = await client.get(
        f"/api/v1/audit-events?tenant_id={owner['tenant_id']}", headers=headers
    )
    assert audit.status_code == 200
    event_types = {e["event_type"] for e in audit.json()}
    assert "PROJECT_DELETED" in event_types


async def test_delete_project_requires_manager_role(client: AsyncClient, unique_email: str) -> None:
    owner = await register(client, email=unique_email)
    project = await create_project(client, owner=owner)
    member = await add_project_member_with_role(
        client, owner=owner, project_id=project["id"], role="DELIVERY_TEAM"
    )

    resp = await client.delete(
        f"/api/v1/projects/{project['id']}", headers={"Authorization": f"Bearer {member['access_token']}"}
    )
    assert resp.status_code == 403


async def test_delete_nonexistent_project_404s(client: AsyncClient, unique_email: str) -> None:
    owner = await register(client, email=unique_email)
    fake_id = str(uuid.uuid4())
    resp = await client.delete(
        f"/api/v1/projects/{fake_id}", headers={"Authorization": f"Bearer {owner['access_token']}"}
    )
    assert resp.status_code == 404
