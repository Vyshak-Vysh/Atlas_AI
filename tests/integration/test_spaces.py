"""Integration tests for the Spaces API: CRUD lifecycle plus the
correctness fixes made alongside the launch-readiness audit — a
nonexistent space must 404 (not 500), a duplicate name must 409 (not
500), an invalid status must 422, and a project cannot be attached to
another tenant's space."""

from __future__ import annotations

import uuid

import pytest
from _helpers import register
from httpx import AsyncClient

pytestmark = pytest.mark.integration


def _tenant_params(owner: dict) -> dict:
    return {"tenant_id": owner["tenant_id"]}


async def _create_space(client: AsyncClient, *, token: str, tenant_id: str, name: str = "Engineering") -> dict:
    resp = await client.post(
        "/api/v1/spaces",
        json={"tenant_id": tenant_id, "name": name, "description": "d"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_create_list_and_get_space_overview(client: AsyncClient, unique_email: str) -> None:
    owner = await register(client, email=unique_email)
    space = await _create_space(client, token=owner["access_token"], tenant_id=owner["tenant_id"])
    headers = {"Authorization": f"Bearer {owner['access_token']}"}

    listed = await client.get("/api/v1/spaces", params={"tenant_id": owner["tenant_id"]}, headers=headers)
    assert listed.status_code == 200
    assert space["id"] in {s["id"] for s in listed.json()}

    overview = await client.get(f"/api/v1/spaces/{space['id']}", params=_tenant_params(owner), headers=headers)
    assert overview.status_code == 200, overview.text
    assert overview.json()["project_count"] == 0


async def test_project_lifecycle_within_a_space(client: AsyncClient, unique_email: str) -> None:
    owner = await register(client, email=unique_email)
    headers = {"Authorization": f"Bearer {owner['access_token']}"}
    space = await _create_space(client, token=owner["access_token"], tenant_id=owner["tenant_id"])

    project = await client.post(
        "/api/v1/projects",
        json={"tenant_id": owner["tenant_id"], "name": "Atlas Web", "space_id": space["id"]},
        headers=headers,
    )
    assert project.status_code == 201, project.text
    assert project.json()["space_id"] == space["id"]

    projects = await client.get(
        f"/api/v1/spaces/{space['id']}/projects", params=_tenant_params(owner), headers=headers
    )
    assert projects.status_code == 200
    assert [p["id"] for p in projects.json()] == [project.json()["id"]]

    overview = await client.get(f"/api/v1/spaces/{space['id']}", params=_tenant_params(owner), headers=headers)
    assert overview.json()["project_count"] == 1


async def test_update_and_delete_space(client: AsyncClient, unique_email: str) -> None:
    owner = await register(client, email=unique_email)
    headers = {"Authorization": f"Bearer {owner['access_token']}"}
    space = await _create_space(client, token=owner["access_token"], tenant_id=owner["tenant_id"])

    updated = await client.patch(
        f"/api/v1/spaces/{space['id']}",
        params=_tenant_params(owner),
        json={"description": "Updated", "status": "ON_HOLD"},
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["status"] == "ON_HOLD"

    deleted = await client.delete(f"/api/v1/spaces/{space['id']}", params=_tenant_params(owner), headers=headers)
    assert deleted.status_code == 204

    missing = await client.get(f"/api/v1/spaces/{space['id']}", params=_tenant_params(owner), headers=headers)
    assert missing.status_code == 404


async def test_delete_space_with_projects_is_blocked(client: AsyncClient, unique_email: str) -> None:
    owner = await register(client, email=unique_email)
    headers = {"Authorization": f"Bearer {owner['access_token']}"}
    space = await _create_space(client, token=owner["access_token"], tenant_id=owner["tenant_id"])
    await client.post(
        "/api/v1/projects",
        json={"tenant_id": owner["tenant_id"], "name": "Atlas Web", "space_id": space["id"]},
        headers=headers,
    )

    resp = await client.delete(f"/api/v1/spaces/{space['id']}", params=_tenant_params(owner), headers=headers)
    assert resp.status_code == 409


async def test_nonexistent_space_404s_instead_of_500(client: AsyncClient, unique_email: str) -> None:
    owner = await register(client, email=unique_email)
    headers = {"Authorization": f"Bearer {owner['access_token']}"}
    params = _tenant_params(owner)
    fake_id = str(uuid.uuid4())

    get_resp = await client.get(f"/api/v1/spaces/{fake_id}", params=params, headers=headers)
    assert get_resp.status_code == 404

    projects_resp = await client.get(f"/api/v1/spaces/{fake_id}/projects", params=params, headers=headers)
    assert projects_resp.status_code == 404

    patch_resp = await client.patch(f"/api/v1/spaces/{fake_id}", params=params, json={"name": "X"}, headers=headers)
    assert patch_resp.status_code == 404

    delete_resp = await client.delete(f"/api/v1/spaces/{fake_id}", params=params, headers=headers)
    assert delete_resp.status_code == 404


async def test_duplicate_space_name_conflicts(client: AsyncClient, unique_email: str) -> None:
    owner = await register(client, email=unique_email)
    await _create_space(client, token=owner["access_token"], tenant_id=owner["tenant_id"], name="Engineering")

    dup = await client.post(
        "/api/v1/spaces",
        json={"tenant_id": owner["tenant_id"], "name": "Engineering"},
        headers={"Authorization": f"Bearer {owner['access_token']}"},
    )
    assert dup.status_code == 409


async def test_update_space_rejects_invalid_status(client: AsyncClient, unique_email: str) -> None:
    owner = await register(client, email=unique_email)
    headers = {"Authorization": f"Bearer {owner['access_token']}"}
    space = await _create_space(client, token=owner["access_token"], tenant_id=owner["tenant_id"])

    resp = await client.patch(
        f"/api/v1/spaces/{space['id']}",
        params={"tenant_id": owner["tenant_id"]},
        json={"status": "NOT_A_REAL_STATUS"},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_project_cannot_attach_to_another_tenants_space(client: AsyncClient, unique_email: str) -> None:
    owner = await register(client, email=unique_email)
    other = await register(client, email=f"other-{unique_email}")
    other_space = await _create_space(client, token=other["access_token"], tenant_id=other["tenant_id"])

    create = await client.post(
        "/api/v1/projects",
        json={"tenant_id": owner["tenant_id"], "name": "Sneaky", "space_id": other_space["id"]},
        headers={"Authorization": f"Bearer {owner['access_token']}"},
    )
    assert create.status_code == 404

    own_project = await client.post(
        "/api/v1/projects",
        json={"tenant_id": owner["tenant_id"], "name": "Legit"},
        headers={"Authorization": f"Bearer {owner['access_token']}"},
    )
    assert own_project.status_code == 201

    move = await client.patch(
        f"/api/v1/projects/{own_project.json()['id']}",
        json={"space_id": other_space["id"]},
        headers={"Authorization": f"Bearer {owner['access_token']}"},
    )
    assert move.status_code == 404


# --- Space-level rollups (findings/actions/report aggregated across a
# space's projects) -----------------------------------------------------


async def test_space_report_aggregates_across_its_projects(client: AsyncClient, unique_email: str) -> None:
    owner = await register(client, email=unique_email)
    headers = {"Authorization": f"Bearer {owner['access_token']}"}
    space = await _create_space(client, token=owner["access_token"], tenant_id=owner["tenant_id"], name="Amazon")

    project_ids = []
    for name in ("Amazon Migration", "Amazon Pipeline"):
        proj = await client.post(
            "/api/v1/projects",
            json={"tenant_id": owner["tenant_id"], "name": name, "space_id": space["id"]},
            headers=headers,
        )
        assert proj.status_code == 201, proj.text
        project_ids.append(proj.json()["id"])
        # One delivered, one still in progress, per project.
        await client.post(
            f"/api/v1/requirements?project_id={proj.json()['id']}",
            json={"key": "T-1", "title": "Done", "status": "DELIVERED_VERIFIED"},
            headers=headers,
        )
        await client.post(
            f"/api/v1/requirements?project_id={proj.json()['id']}",
            json={"key": "T-2", "title": "Not done", "status": "PROPOSED"},
            headers=headers,
        )

    report = await client.get(f"/api/v1/spaces/{space['id']}/report", params=_tenant_params(owner), headers=headers)
    assert report.status_code == 200, report.text
    body = report.json()
    assert body["project_count"] == 2
    assert body["total_requirements"] == 4
    assert body["requirements_delivered"] == 2
    assert {p["project"]["id"] for p in body["projects"]} == set(project_ids)


async def test_space_findings_and_actions_404_on_nonexistent_space(client: AsyncClient, unique_email: str) -> None:
    owner = await register(client, email=unique_email)
    headers = {"Authorization": f"Bearer {owner['access_token']}"}
    fake_id = str(uuid.uuid4())
    params = _tenant_params(owner)

    for path in ("findings", "actions", "report"):
        resp = await client.get(f"/api/v1/spaces/{fake_id}/{path}", params=params, headers=headers)
        assert resp.status_code == 404, (path, resp.text)


async def test_space_findings_and_actions_empty_lists_for_a_fresh_space(client: AsyncClient, unique_email: str) -> None:
    owner = await register(client, email=unique_email)
    headers = {"Authorization": f"Bearer {owner['access_token']}"}
    space = await _create_space(client, token=owner["access_token"], tenant_id=owner["tenant_id"])

    findings = await client.get(f"/api/v1/spaces/{space['id']}/findings", params=_tenant_params(owner), headers=headers)
    assert findings.status_code == 200
    assert findings.json() == []

    actions = await client.get(f"/api/v1/spaces/{space['id']}/actions", params=_tenant_params(owner), headers=headers)
    assert actions.status_code == 200
    assert actions.json() == []
