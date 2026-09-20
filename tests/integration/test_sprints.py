"""Integration tests for the Sprints API and its intersection with
Requirements (tasks): CRUD lifecycle, plus the correctness fixes made
alongside the launch-readiness audit — a nonexistent sprint must 404
(not 500), a duplicate sprint_number must 409 (not 500), an invalid
status must 422, and a task cannot be linked to another project's
sprint."""

from __future__ import annotations

import uuid

import pytest
from _helpers import create_project, register
from httpx import AsyncClient

pytestmark = pytest.mark.integration


async def _create_sprint(
    client: AsyncClient, *, token: str, project_id: str, name: str = "Sprint 1", sprint_number: int = 1
) -> dict:
    resp = await client.post(
        f"/api/v1/projects/{project_id}/sprints",
        json={"name": name, "sprint_number": sprint_number},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_create_list_and_get_sprint_detail(client: AsyncClient, unique_email: str) -> None:
    owner = await register(client, email=unique_email)
    project = await create_project(client, owner=owner)
    headers = {"Authorization": f"Bearer {owner['access_token']}"}
    sprint = await _create_sprint(client, token=owner["access_token"], project_id=project["id"])

    listed = await client.get(f"/api/v1/projects/{project['id']}/sprints", headers=headers)
    assert listed.status_code == 200
    assert [s["id"] for s in listed.json()] == [sprint["id"]]

    detail = await client.get(f"/api/v1/projects/{project['id']}/sprints/{sprint['id']}", headers=headers)
    assert detail.status_code == 200, detail.text
    assert detail.json() == {"sprint": sprint, "task_count": 0, "done_count": 0}


async def test_task_lifecycle_within_a_sprint(client: AsyncClient, unique_email: str) -> None:
    owner = await register(client, email=unique_email)
    project = await create_project(client, owner=owner)
    headers = {"Authorization": f"Bearer {owner['access_token']}"}
    sprint = await _create_sprint(client, token=owner["access_token"], project_id=project["id"])

    task = await client.post(
        f"/api/v1/requirements?project_id={project['id']}",
        json={"key": "T-1", "title": "Ship it", "status": "PROPOSED", "sprint_id": sprint["id"]},
        headers=headers,
    )
    assert task.status_code == 201, task.text
    assert task.json()["sprint_id"] == sprint["id"]

    filtered = await client.get(
        f"/api/v1/requirements?project_id={project['id']}&sprint_id={sprint['id']}", headers=headers
    )
    assert [r["id"] for r in filtered.json()] == [task.json()["id"]]

    await client.patch(
        f"/api/v1/requirements/{task.json()['id']}?project_id={project['id']}",
        json={"task_status": "DONE"},
        headers=headers,
    )
    detail = await client.get(f"/api/v1/projects/{project['id']}/sprints/{sprint['id']}", headers=headers)
    assert detail.json()["task_count"] == 1
    assert detail.json()["done_count"] == 1

    cleared = await client.patch(
        f"/api/v1/requirements/{task.json()['id']}?project_id={project['id']}",
        json={"sprint_id": None},
        headers=headers,
    )
    assert cleared.status_code == 200
    assert cleared.json()["sprint_id"] is None


async def test_update_sprint_status(client: AsyncClient, unique_email: str) -> None:
    owner = await register(client, email=unique_email)
    project = await create_project(client, owner=owner)
    headers = {"Authorization": f"Bearer {owner['access_token']}"}
    sprint = await _create_sprint(client, token=owner["access_token"], project_id=project["id"])

    resp = await client.patch(
        f"/api/v1/projects/{project['id']}/sprints/{sprint['id']}", json={"status": "ACTIVE"}, headers=headers
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "ACTIVE"


async def test_nonexistent_sprint_404s_instead_of_500(client: AsyncClient, unique_email: str) -> None:
    owner = await register(client, email=unique_email)
    project = await create_project(client, owner=owner)
    headers = {"Authorization": f"Bearer {owner['access_token']}"}
    fake_id = str(uuid.uuid4())

    assert (await client.get(f"/api/v1/projects/{project['id']}/sprints/{fake_id}", headers=headers)).status_code == 404
    assert (
        await client.patch(f"/api/v1/projects/{project['id']}/sprints/{fake_id}", json={"name": "X"}, headers=headers)
    ).status_code == 404


async def test_duplicate_sprint_number_conflicts(client: AsyncClient, unique_email: str) -> None:
    owner = await register(client, email=unique_email)
    project = await create_project(client, owner=owner)
    await _create_sprint(client, token=owner["access_token"], project_id=project["id"], sprint_number=1)

    dup = await client.post(
        f"/api/v1/projects/{project['id']}/sprints",
        json={"name": "Also sprint 1", "sprint_number": 1},
        headers={"Authorization": f"Bearer {owner['access_token']}"},
    )
    assert dup.status_code == 409


async def test_update_sprint_rejects_invalid_status(client: AsyncClient, unique_email: str) -> None:
    owner = await register(client, email=unique_email)
    project = await create_project(client, owner=owner)
    headers = {"Authorization": f"Bearer {owner['access_token']}"}
    sprint = await _create_sprint(client, token=owner["access_token"], project_id=project["id"])

    resp = await client.patch(
        f"/api/v1/projects/{project['id']}/sprints/{sprint['id']}",
        json={"status": "NOT_A_REAL_STATUS"},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_task_cannot_link_to_another_projects_sprint(client: AsyncClient, unique_email: str) -> None:
    owner = await register(client, email=unique_email)
    headers = {"Authorization": f"Bearer {owner['access_token']}"}
    project1 = await create_project(client, owner=owner, name="P1")
    project2 = await create_project(client, owner=owner, name="P2")
    sprint_in_p1 = await _create_sprint(client, token=owner["access_token"], project_id=project1["id"])

    create = await client.post(
        f"/api/v1/requirements?project_id={project2['id']}",
        json={"key": "T-1", "title": "x", "status": "PROPOSED", "sprint_id": sprint_in_p1["id"]},
        headers=headers,
    )
    assert create.status_code == 400

    task = await client.post(
        f"/api/v1/requirements?project_id={project2['id']}",
        json={"key": "T-2", "title": "y", "status": "PROPOSED"},
        headers=headers,
    )
    assert task.status_code == 201

    update = await client.patch(
        f"/api/v1/requirements/{task.json()['id']}?project_id={project2['id']}",
        json={"sprint_id": sprint_in_p1["id"]},
        headers=headers,
    )
    assert update.status_code == 400

    garbage = await client.post(
        f"/api/v1/requirements?project_id={project2['id']}",
        json={"key": "T-3", "title": "z", "status": "PROPOSED", "sprint_id": str(uuid.uuid4())},
        headers=headers,
    )
    assert garbage.status_code == 400
