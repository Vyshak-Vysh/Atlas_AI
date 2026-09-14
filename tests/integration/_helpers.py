"""Shared integration-test helpers.

`add_project_member_with_role` covers a flow several new test modules need:
inviting a second, independently-registered user into an existing owner's
tenant AND project under a specific role, then obtaining an access token
scoped to that tenant (JWTs are tenant-scoped — see auth_service.py) so the
resulting client can actually exercise that role's permissions.
"""

from __future__ import annotations

import uuid

from httpx import AsyncClient


async def register(client: AsyncClient, *, email: str, tenant_name: str | None = None) -> dict:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "tenant_name": tenant_name or f"Co {email}",
            "email": email,
            "password": "a-very-long-test-password-1",
            "display_name": email.split("@")[0],
        },
    )
    assert reg.status_code == 201, reg.text
    return reg.json()


async def create_project(client: AsyncClient, *, owner: dict, name: str = "Test Project") -> dict:
    proj = await client.post(
        "/api/v1/projects",
        json={"tenant_id": owner["tenant_id"], "name": name},
        headers={"Authorization": f"Bearer {owner['access_token']}"},
    )
    assert proj.status_code == 201, proj.text
    return proj.json()


async def add_project_member_with_role(
    client: AsyncClient, *, owner: dict, project_id: str, role: str, unique_suffix: str | None = None
) -> dict:
    """Registers a brand-new user, invites them into `owner`'s tenant and
    project under `role`, and returns a dict with an `access_token` scoped
    to that tenant — ready to use as `Authorization: Bearer ...` for
    requests exercising that role's permissions."""
    email = f"member-{role.lower()}-{unique_suffix or uuid.uuid4().hex[:12]}@atlasai-integration-tests.dev"
    member = await register(client, email=email)

    add_tenant = await client.post(
        f"/api/v1/tenants/{owner['tenant_id']}/members",
        json={"email": email, "role": role},
        headers={"Authorization": f"Bearer {owner['access_token']}"},
    )
    assert add_tenant.status_code == 201, add_tenant.text

    add_project = await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"email": email, "role": role},
        headers={"Authorization": f"Bearer {owner['access_token']}"},
    )
    assert add_project.status_code == 201, add_project.text

    switched = await client.post(
        "/api/v1/auth/switch-tenant",
        json={"tenant_id": owner["tenant_id"]},
        headers={"Authorization": f"Bearer {member['access_token']}"},
    )
    assert switched.status_code == 200, switched.text
    result = switched.json()
    result["email"] = email
    return result
