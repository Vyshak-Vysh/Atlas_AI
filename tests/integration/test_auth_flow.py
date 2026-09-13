"""Integration tests for registration, login, and refresh-token rotation
against the real API + database."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


async def _register(client: AsyncClient, email: str) -> dict:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "tenant_name": "Integration Test Co",
            "email": email,
            "password": "a-very-long-test-password-1",
            "display_name": "Test User",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_register_returns_a_working_token_pair(client: AsyncClient, unique_email: str) -> None:
    body = await _register(client, unique_email)
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["tenant_id"]

    me = await client.get(
        f"/api/v1/audit-events?tenant_id={body['tenant_id']}",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    events = me.json()
    assert any(e["event_type"] == "TENANT_CREATED" for e in events)


async def test_duplicate_email_registration_is_rejected(client: AsyncClient, unique_email: str) -> None:
    await _register(client, unique_email)
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "tenant_name": "Another Co",
            "email": unique_email,
            "password": "another-long-test-password-1",
            "display_name": "Someone Else",
        },
    )
    assert response.status_code == 409


async def test_login_with_wrong_password_is_rejected(client: AsyncClient, unique_email: str) -> None:
    await _register(client, unique_email)
    response = await client.post(
        "/api/v1/auth/login", json={"email": unique_email, "password": "wrong-password-entirely"}
    )
    assert response.status_code == 401


async def test_login_with_correct_password_succeeds(client: AsyncClient, unique_email: str) -> None:
    await _register(client, unique_email)
    response = await client.post(
        "/api/v1/auth/login", json={"email": unique_email, "password": "a-very-long-test-password-1"}
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


async def test_refresh_token_rotates_and_old_token_cannot_be_reused(client: AsyncClient, unique_email: str) -> None:
    body = await _register(client, unique_email)
    first_refresh = body["refresh_token"]

    refreshed = await client.post("/api/v1/auth/refresh", json={"refresh_token": first_refresh})
    assert refreshed.status_code == 200
    assert refreshed.json()["refresh_token"] != first_refresh

    reused = await client.post("/api/v1/auth/refresh", json={"refresh_token": first_refresh})
    assert reused.status_code == 401


async def test_protected_endpoint_rejects_missing_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/audit-events?tenant_id=00000000-0000-0000-0000-000000000000")
    assert response.status_code in (401, 403)


async def test_protected_endpoint_rejects_garbage_token(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/audit-events?tenant_id=00000000-0000-0000-0000-000000000000",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code == 401
