"""Same-tenant, same-project, per-role authorization matrix for the task
API. This is a different test category from test_authorization_negative.py,
which only covers CROSS-tenant lockout (a user with no membership at all).
Here every user is a legitimate member of the SAME project under a
DIFFERENT role, and CLIENT_VIEWER must be read-only while every other role
gets full read/write — per the product decision that "everyone except the
client" can manage tasks.
"""

from __future__ import annotations

import pytest
from _helpers import add_project_member_with_role, create_project, register
from httpx import AsyncClient

pytestmark = pytest.mark.integration

_WRITER_ROLES = ["PROJECT_MANAGER", "CEO_SALES", "DELIVERY_TEAM", "WORKER", "AI_ENGINEER_ADMIN"]


async def _create_requirement(client: AsyncClient, *, token: str, project_id: str, key: str) -> dict:
    resp = await client.post(
        f"/api/v1/requirements?project_id={project_id}",
        json={"key": key, "title": "Task", "status": "CAPTURED"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.parametrize("role", _WRITER_ROLES)
async def test_non_client_role_has_full_task_read_write(client: AsyncClient, unique_email: str, role: str) -> None:
    owner = await register(client, email=unique_email)
    project = await create_project(client, owner=owner)
    member = await add_project_member_with_role(client, owner=owner, project_id=project["id"], role=role)
    headers = {"Authorization": f"Bearer {member['access_token']}"}

    created = await client.post(
        f"/api/v1/requirements?project_id={project['id']}",
        json={"key": "REQ-1", "title": "Ship it", "status": "CAPTURED"},
        headers=headers,
    )
    assert created.status_code == 201, f"{role} should be able to create a task: {created.text}"
    requirement_id = created.json()["id"]

    patched = await client.patch(
        f"/api/v1/requirements/{requirement_id}?project_id={project['id']}",
        json={"task_status": "IN_PROGRESS"},
        headers=headers,
    )
    assert patched.status_code == 200, f"{role} should be able to edit a task: {patched.text}"

    commented = await client.post(
        f"/api/v1/requirements/{requirement_id}/comments?project_id={project['id']}",
        json={"body": "on it"},
        headers=headers,
    )
    assert commented.status_code == 201, f"{role} should be able to comment: {commented.text}"

    deleted = await client.delete(
        f"/api/v1/requirements/{requirement_id}?project_id={project['id']}", headers=headers
    )
    assert deleted.status_code == 204, f"{role} should be able to delete a task: {deleted.text}"


async def test_client_viewer_is_read_only(client: AsyncClient, unique_email: str) -> None:
    owner = await register(client, email=unique_email)
    project = await create_project(client, owner=owner)
    requirement = await _create_requirement(
        client, token=owner["access_token"], project_id=project["id"], key="REQ-1"
    )
    client_viewer = await add_project_member_with_role(
        client, owner=owner, project_id=project["id"], role="CLIENT_VIEWER"
    )
    headers = {"Authorization": f"Bearer {client_viewer['access_token']}"}

    # Reads succeed.
    for resp in (
        await client.get(f"/api/v1/requirements?project_id={project['id']}", headers=headers),
        await client.get(f"/api/v1/requirements/{requirement['id']}?project_id={project['id']}", headers=headers),
        await client.get(
            f"/api/v1/requirements/{requirement['id']}/comments?project_id={project['id']}", headers=headers
        ),
        await client.get(
            f"/api/v1/requirements/{requirement['id']}/history?project_id={project['id']}", headers=headers
        ),
    ):
        assert resp.status_code == 200, resp.text

    # Every write is refused.
    create = await client.post(
        f"/api/v1/requirements?project_id={project['id']}",
        json={"key": "REQ-2", "title": "Should not work", "status": "CAPTURED"},
        headers=headers,
    )
    assert create.status_code == 403

    patch = await client.patch(
        f"/api/v1/requirements/{requirement['id']}?project_id={project['id']}",
        json={"task_status": "DONE"},
        headers=headers,
    )
    assert patch.status_code == 403

    comment = await client.post(
        f"/api/v1/requirements/{requirement['id']}/comments?project_id={project['id']}",
        json={"body": "should not work"},
        headers=headers,
    )
    assert comment.status_code == 403

    delete = await client.delete(
        f"/api/v1/requirements/{requirement['id']}?project_id={project['id']}", headers=headers
    )
    assert delete.status_code == 403
