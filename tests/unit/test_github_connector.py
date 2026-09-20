"""Unit tests for the GitHub connector.

Run against an in-process `httpx.MockTransport` rather than the live API,
so they need no token and no network while still exercising the real
request construction, pagination cursor, and normalization logic.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import httpx
import pytest

from atlasai_connectors.git_ci.connector import GitHubAuthError, GitHubConnector, GitHubSettings
from atlasai_connectors.registry import get_connector, list_available_providers
from atlasai_domain.contracts.connectors import AccountRef, AuthorizationRequest
from atlasai_domain.enums import ConnectorProvider

_ISSUE = {
    "number": 41,
    "title": "Notification centre: deliver Phase 2 scope",
    "body": "Implements the real-time notification centre deferred from Phase 1.",
    "state": "closed",
    "user": {"login": "dev-one"},
    "labels": [{"name": "phase-2"}, {"name": "delivered"}],
    "html_url": "https://github.com/acme/portal/issues/41",
    "created_at": "2026-02-01T10:00:00Z",
    "updated_at": "2026-03-04T12:30:00Z",
    "closed_at": "2026-03-04T12:30:00Z",
}

_PULL = {
    **_ISSUE,
    "number": 42,
    "title": "Add notification centre API",
    "pull_request": {"url": "https://api.github.com/repos/acme/portal/pulls/42"},
    "merged_at": "2026-03-05T09:00:00Z",
    "updated_at": "2026-03-05T09:00:00Z",
}


def _connector(handler: Any, *, token: str = "ghp_testtoken") -> GitHubConnector:  # noqa: S107 - fake token
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    return GitHubConnector(settings=GitHubSettings(github_token=token), client=client)


def _json_response(payload: Any, status: int = 200) -> httpx.Response:
    return httpx.Response(status, content=json.dumps(payload), headers={"content-type": "application/json"})


async def test_authorize_resolves_the_account_and_never_returns_the_token() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["version"] = request.headers.get("x-github-api-version")
        return _json_response({"login": "acme-bot"})

    connector = _connector(handler)
    result = await connector.authorize(
        AuthorizationRequest(
            tenant_id=uuid.uuid4(), provider=ConnectorProvider.GIT_CI_GITHUB, requested_by_user_id=uuid.uuid4()
        )
    )

    assert result.external_account_id == "acme-bot"
    assert seen["auth"] == "Bearer ghp_testtoken"
    assert seen["version"] == "2022-11-28"
    # The secret must never reach the database — only a reference to it.
    assert "ghp_testtoken" not in result.credential_ref
    assert result.credential_ref == "env:GITHUB_TOKEN"


async def test_missing_token_raises_before_any_request_is_made() -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover - must not run
        raise AssertionError("no HTTP request should be attempted without a token")

    connector = _connector(handler, token="")
    with pytest.raises(GitHubAuthError, match="not configured"):
        await connector.authorize(
            AuthorizationRequest(
                tenant_id=uuid.uuid4(),
                provider=ConnectorProvider.GIT_CI_GITHUB,
                requested_by_user_id=uuid.uuid4(),
            )
        )


async def test_health_check_reports_unhealthy_rather_than_raising_when_unconfigured() -> None:
    connector = GitHubConnector(settings=GitHubSettings(github_token=""))
    result = await connector.health_check()
    assert result.healthy is False
    assert "not configured" in (result.detail or "")


async def test_401_is_translated_into_a_typed_auth_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response({"message": "Bad credentials"}, status=401)

    connector = _connector(handler)
    with pytest.raises(GitHubAuthError, match="401"):
        await connector.authorize(
            AuthorizationRequest(
                tenant_id=uuid.uuid4(),
                provider=ConnectorProvider.GIT_CI_GITHUB,
                requested_by_user_id=uuid.uuid4(),
            )
        )


async def test_discover_scope_lists_repositories() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(
            [
                {"full_name": "acme/portal", "private": True, "default_branch": "main"},
                {"full_name": "acme/docs", "private": False, "default_branch": "main"},
            ]
        )

    connector = _connector(handler)
    scopes = await connector.discover_scope(
        AccountRef(connector_id=uuid.uuid4(), external_account_id="acme-bot", credential_ref="env:GITHUB_TOKEN")
    )

    assert [s.scope_external_id for s in scopes] == ["acme/portal", "acme/docs"]
    assert all(s.scope_type == "repository" for s in scopes)
    assert scopes[0].scope_json["private"] is True


async def test_sync_without_scope_fetches_nothing() -> None:
    """A connector not yet attached to a project must not sync the whole
    account — scope comes from connector_scopes, not from the token."""

    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover - must not run
        raise AssertionError("sync must not call GitHub before a scope is set")

    connector = _connector(handler)
    page = await connector.sync(cursor=None)
    assert page.items == []
    assert page.has_more is False


async def test_sync_is_incremental_and_advances_the_cursor() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["params"] = dict(request.url.params)
        return _json_response([_ISSUE, _PULL])

    connector = _connector(handler)
    connector.set_scope(["acme/portal"])
    page = await connector.sync(cursor="2026-01-01T00:00:00Z")

    assert captured["params"]["since"] == "2026-01-01T00:00:00Z"
    assert captured["params"]["state"] == "all"
    assert len(page.items) == 2
    # Cursor advances to the newest updated_at seen, so the next sync
    # resumes rather than refetching.
    assert page.next_cursor == "2026-03-05T09:00:00Z"


async def test_sync_distinguishes_issues_from_pull_requests() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response([_ISSUE, _PULL])

    connector = _connector(handler)
    connector.set_scope(["acme/portal"])
    page = await connector.sync(cursor=None)

    record_types = {item.external_id: item.record_type for item in page.items}
    assert record_types["acme/portal#41"] == "GIT_ISSUE"
    assert record_types["acme/portal#42"] == "GIT_PULL_REQUEST"


async def test_normalize_produces_searchable_text_and_a_stable_version_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response([_ISSUE])

    connector = _connector(handler)
    connector.set_scope(["acme/portal"])
    page = await connector.sync(cursor=None)
    normalized = await connector.normalize(page.items[0])

    assert "Notification centre" in normalized.extracted_text
    assert "Repository: acme/portal" in normalized.extracted_text
    assert "State: closed" in normalized.extracted_text
    assert "phase-2" in normalized.extracted_text
    # updated_at as version_key means an unchanged issue re-syncs to the
    # same version rather than creating a duplicate.
    assert normalized.version_key == "2026-03-04T12:30:00Z"
    assert normalized.metadata["is_pull_request"] is False
    assert normalized.canonical_url == "https://github.com/acme/portal/issues/41"


async def test_fetch_item_rejects_a_malformed_external_id() -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover - must not run
        raise AssertionError("a malformed id must be rejected before any request")

    connector = _connector(handler)
    with pytest.raises(ValueError, match="malformed GitHub external_id"):
        await connector.fetch_item("not-a-valid-id")


def test_registry_hides_github_when_no_token_is_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "")
    available = list_available_providers()
    assert ConnectorProvider.MANUAL_UPLOAD in available
    assert ConnectorProvider.GIT_CI_GITHUB not in available
    with pytest.raises(PermissionError, match="not configured"):
        get_connector(ConnectorProvider.GIT_CI_GITHUB)


def test_registry_offers_github_once_a_token_is_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_configured")
    assert ConnectorProvider.GIT_CI_GITHUB in list_available_providers()
    assert isinstance(get_connector(ConnectorProvider.GIT_CI_GITHUB), GitHubConnector)


def test_unimplemented_providers_are_absent_rather_than_pretending(monkeypatch: pytest.MonkeyPatch) -> None:
    """Gmail and friends are declared in the enum and rendered in the UI,
    but must not resolve to a connector — the registry is the honest
    boundary between "declared" and "implemented"."""
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_configured")
    for provider in (
        ConnectorProvider.GMAIL,
        ConnectorProvider.MSGRAPH,
        ConnectorProvider.GOOGLE_DRIVE,
        ConnectorProvider.MEETINGS,
        ConnectorProvider.PM_JIRA,
    ):
        assert provider not in list_available_providers()
        with pytest.raises(KeyError):
            get_connector(provider)
