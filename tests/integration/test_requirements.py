"""Positive-path integration tests for the requirements/task API: CRUD,
filters, comments, and history. Exercised as the registering user, who is
AI_ENGINEER_ADMIN on their own newly-created project (see
auth_service.register_tenant_and_owner + projects.create_project's
role-copy onto the first project member)."""

from __future__ import annotations

import pytest
from _helpers import create_project, register
from httpx import AsyncClient

pytestmark = pytest.mark.integration


async def _create_requirement(client: AsyncClient, *, token: str, project_id: str, **overrides: object) -> dict:
    body = {
        "key": overrides.pop("key", "REQ-1"),
        "title": overrides.pop("title", "Ship the thing"),
        "status": overrides.pop("status", "CAPTURED"),
        **overrides,
    }
    resp = await client.post(
        f"/api/v1/requirements?project_id={project_id}",
        json=body,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_create_requirement_defaults_task_fields(client: AsyncClient, unique_email: str) -> None:
    owner = await register(client, email=unique_email)
    project = await create_project(client, owner=owner)

    requirement = await _create_requirement(client, token=owner["access_token"], project_id=project["id"])
    assert requirement["task_status"] == "TO_DO"
    assert requirement["priority"] == "NORMAL"
    assert requirement["assignee_id"] is None


async def test_create_requirement_with_explicit_task_fields(client: AsyncClient, unique_email: str) -> None:
    owner = await register(client, email=unique_email)
    project = await create_project(client, owner=owner)

    requirement = await _create_requirement(
        client,
        token=owner["access_token"],
        project_id=project["id"],
        key="REQ-2",
        task_status="IN_PROGRESS",
        priority="URGENT",
        assignee_id=owner["user_id"],
    )
    assert requirement["task_status"] == "IN_PROGRESS"
    assert requirement["priority"] == "URGENT"
    assert requirement["assignee_id"] == owner["user_id"]


async def test_patch_requirement_updates_task_fields_and_records_history(
    client: AsyncClient, unique_email: str
) -> None:
    owner = await register(client, email=unique_email)
    project = await create_project(client, owner=owner)
    requirement = await _create_requirement(client, token=owner["access_token"], project_id=project["id"])

    patch = await client.patch(
        f"/api/v1/requirements/{requirement['id']}?project_id={project['id']}",
        json={"task_status": "DONE", "priority": "HIGH"},
        headers={"Authorization": f"Bearer {owner['access_token']}"},
    )
    assert patch.status_code == 200, patch.text
    updated = patch.json()
    assert updated["task_status"] == "DONE"
    assert updated["priority"] == "HIGH"

    history = await client.get(
        f"/api/v1/requirements/{requirement['id']}/history?project_id={project['id']}",
        headers={"Authorization": f"Bearer {owner['access_token']}"},
    )
    assert history.status_code == 200, history.text
    entries = history.json()
    event_types = {e["event_type"] for e in entries}
    assert "REQUIREMENT_CREATED" in event_types
    fields_changed = {e["field"] for e in entries}
    assert {"task_status", "priority"} <= fields_changed
    task_status_entry = next(e for e in entries if e["field"] == "task_status")
    assert task_status_entry["old_value"] == "TO_DO"
    assert task_status_entry["new_value"] == "DONE"
    assert task_status_entry["actor_display_name"] == unique_email.split("@")[0]
    assert task_status_entry["actor_email"] == unique_email


async def test_patch_can_clear_assignee_explicitly(client: AsyncClient, unique_email: str) -> None:
    owner = await register(client, email=unique_email)
    project = await create_project(client, owner=owner)
    requirement = await _create_requirement(
        client, token=owner["access_token"], project_id=project["id"], assignee_id=owner["user_id"]
    )
    assert requirement["assignee_id"] == owner["user_id"]

    patch = await client.patch(
        f"/api/v1/requirements/{requirement['id']}?project_id={project['id']}",
        json={"assignee_id": None},
        headers={"Authorization": f"Bearer {owner['access_token']}"},
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["assignee_id"] is None


async def test_patch_rejects_non_member_assignee(client: AsyncClient, unique_email: str) -> None:
    owner = await register(client, email=unique_email)
    project = await create_project(client, owner=owner)
    requirement = await _create_requirement(client, token=owner["access_token"], project_id=project["id"])

    outsider = await register(client, email=f"outsider-{unique_email}")
    patch = await client.patch(
        f"/api/v1/requirements/{requirement['id']}?project_id={project['id']}",
        json={"assignee_id": outsider["user_id"]},
        headers={"Authorization": f"Bearer {owner['access_token']}"},
    )
    assert patch.status_code == 400


async def test_filter_requirements_by_task_status_priority_assignee(client: AsyncClient, unique_email: str) -> None:
    owner = await register(client, email=unique_email)
    project = await create_project(client, owner=owner)
    await _create_requirement(
        client, token=owner["access_token"], project_id=project["id"], key="REQ-A",
        task_status="TO_DO", priority="LOW",
    )
    await _create_requirement(
        client, token=owner["access_token"], project_id=project["id"], key="REQ-B",
        task_status="DONE", priority="URGENT", assignee_id=owner["user_id"],
    )

    resp = await client.get(
        f"/api/v1/requirements?project_id={project['id']}&task_status=DONE",
        headers={"Authorization": f"Bearer {owner['access_token']}"},
    )
    assert resp.status_code == 200
    keys = {r["key"] for r in resp.json()}
    assert keys == {"REQ-B"}

    resp = await client.get(
        f"/api/v1/requirements?project_id={project['id']}&assignee_id={owner['user_id']}",
        headers={"Authorization": f"Bearer {owner['access_token']}"},
    )
    assert {r["key"] for r in resp.json()} == {"REQ-B"}


async def test_comment_crud_lifecycle(client: AsyncClient, unique_email: str) -> None:
    owner = await register(client, email=unique_email)
    project = await create_project(client, owner=owner)
    requirement = await _create_requirement(client, token=owner["access_token"], project_id=project["id"])
    headers = {"Authorization": f"Bearer {owner['access_token']}"}

    created = await client.post(
        f"/api/v1/requirements/{requirement['id']}/comments?project_id={project['id']}",
        json={"body": "Looks good to me"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    comment = created.json()
    assert comment["author_email"] == unique_email
    assert comment["body"] == "Looks good to me"

    listed = await client.get(
        f"/api/v1/requirements/{requirement['id']}/comments?project_id={project['id']}", headers=headers
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    edited = await client.patch(
        f"/api/v1/requirements/{requirement['id']}/comments/{comment['id']}?project_id={project['id']}",
        json={"body": "Actually, one more thing"},
        headers=headers,
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["body"] == "Actually, one more thing"

    deleted = await client.delete(
        f"/api/v1/requirements/{requirement['id']}/comments/{comment['id']}?project_id={project['id']}",
        headers=headers,
    )
    assert deleted.status_code == 204

    listed_after = await client.get(
        f"/api/v1/requirements/{requirement['id']}/comments?project_id={project['id']}", headers=headers
    )
    assert listed_after.json() == []


async def test_delete_requirement_without_evidence_succeeds(client: AsyncClient, unique_email: str) -> None:
    owner = await register(client, email=unique_email)
    project = await create_project(client, owner=owner)
    requirement = await _create_requirement(client, token=owner["access_token"], project_id=project["id"])

    resp = await client.delete(
        f"/api/v1/requirements/{requirement['id']}?project_id={project['id']}",
        headers={"Authorization": f"Bearer {owner['access_token']}"},
    )
    assert resp.status_code == 204

    resp = await client.get(
        f"/api/v1/requirements/{requirement['id']}?project_id={project['id']}",
        headers={"Authorization": f"Bearer {owner['access_token']}"},
    )
    assert resp.status_code == 404
