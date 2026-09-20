"""GitHub connector: issues and pull requests as project evidence.

Delivery questions ("was the notification centre actually shipped?") are
often answered by the tracker rather than by prose in a contract, so GitHub
issues and PRs are treated as first-class evidence alongside documents.

Auth is a fine-grained personal access token read from settings, not an
OAuth app. That is a deliberate scope choice: a PAT is a real credential
that makes the connector genuinely usable today, whereas an OAuth app would
add a browser redirect flow and a callback endpoint without changing what
the connector can read. `authorize()` therefore validates the configured
token against `GET /user` and returns the authenticated login as the
external account id, rather than returning an `authorize_url`.

Every network call goes through `_request`, which centralises the base URL,
the API version header, error translation, and the timeout - so no call
site can accidentally omit authentication or hang without a bound.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict

from atlasai_connectors.protocol import (
    AccountRef,
    AuthorizationRequest,
    AuthorizationResult,
    ExternalItem,
    HealthResult,
    NormalizedSource,
    ScopeItem,
    SyncPage,
)
from atlasai_domain.enums import ConnectorProvider

_API_BASE = "https://api.github.com"
_API_VERSION = "2022-11-28"
_PAGE_SIZE = 50
_TIMEOUT_SECONDS = 30.0


class GitHubSettings(BaseSettings):
    """Environment-driven GitHub configuration.

    `github_token` is optional so that importing this module never fails on
    a deployment that has not configured GitHub; `is_configured()` is what
    the registry consults before offering the provider.
    """

    model_config = SettingsConfigDict(extra="ignore")

    github_token: str = ""
    github_api_base_url: str = _API_BASE


class GitHubAuthError(Exception):
    """The configured token is missing, invalid, or lacks the needed scope."""


class GitHubConnector:
    """Connector-protocol adapter for GitHub issues and pull requests."""

    provider = ConnectorProvider.GIT_CI_GITHUB

    def __init__(self, settings: GitHubSettings | None = None, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings or GitHubSettings()
        self._client = client
        self._owns_client = client is None
        self._scope_repos: list[str] = []

    @classmethod
    def is_configured(cls) -> bool:
        """Consulted by the registry. A connector with no token is never
        offered as available, so the UI cannot invite a user to connect
        something that would immediately fail."""
        return bool(GitHubSettings().github_token.strip())

    # ---- HTTP plumbing -------------------------------------------------

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=_TIMEOUT_SECONDS)
        return self._client

    def _headers(self) -> dict[str, str]:
        token = self._settings.github_token.strip()
        if not token:
            raise GitHubAuthError("GITHUB_TOKEN is not configured")
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": _API_VERSION,
        }

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = path if path.startswith("http") else f"{self._settings.github_api_base_url}{path}"
        response = await self._http().request(method, url, headers=self._headers(), **kwargs)
        if response.status_code in (401, 403):
            raise GitHubAuthError(f"GitHub rejected the configured token ({response.status_code})")
        response.raise_for_status()
        return response.json()

    # ---- Connector protocol --------------------------------------------

    async def authorize(self, request: AuthorizationRequest) -> AuthorizationResult:
        """Validate the configured token and resolve the account it belongs
        to. The token itself is never returned - `credential_ref` names the
        settings key holding it, so the secret stays out of the database."""
        user = await self._request("GET", "/user")
        login = str(user.get("login", "unknown"))
        return AuthorizationResult(
            provider=ConnectorProvider.GIT_CI_GITHUB,
            external_account_id=login,
            credential_ref="env:GITHUB_TOKEN",
            granted_scopes=["repo:read"],
        )

    async def discover_scope(self, account: AccountRef) -> list[ScopeItem]:
        """List repositories the token can read, each offered as a scope the
        user can attach to a project."""
        repos = await self._request(
            "GET",
            "/user/repos",
            params={
                "per_page": _PAGE_SIZE,
                "sort": "updated",
                "affiliation": "owner,collaborator,organization_member",
            },
        )
        return [
            ScopeItem(
                scope_type="repository",
                scope_external_id=str(repo["full_name"]),
                display_name=str(repo["full_name"]),
                scope_json={
                    "private": bool(repo.get("private", False)),
                    "default_branch": repo.get("default_branch"),
                    "html_url": repo.get("html_url"),
                },
            )
            for repo in repos
        ]

    def set_scope(self, repo_full_names: list[str]) -> None:
        """Restrict `sync()` to the repositories a project is scoped to.

        Scope comes from the connector_scopes rows the API wrote when the
        user attached this connector to a project - never from user input at
        sync time - which is what keeps a sync inside the project boundary.
        """
        self._scope_repos = list(repo_full_names)

    async def sync(self, cursor: str | None) -> SyncPage:
        """Fetch issues and pull requests updated since `cursor`.

        The cursor is an ISO-8601 timestamp, so a resumed sync asks GitHub
        only for what changed - incremental by construction rather than by
        filtering a full listing client-side.
        """
        if not self._scope_repos:
            return SyncPage(items=[], next_cursor=cursor, has_more=False)

        params: dict[str, Any] = {"per_page": _PAGE_SIZE, "state": "all", "sort": "updated", "direction": "asc"}
        if cursor:
            params["since"] = cursor

        items: list[ExternalItem] = []
        latest = cursor
        for repo in self._scope_repos:
            issues = await self._request("GET", f"/repos/{repo}/issues", params=params)
            for issue in issues:
                item = self._to_external_item(repo, issue)
                items.append(item)
                updated = str(issue.get("updated_at") or "")
                if updated and (latest is None or updated > latest):
                    latest = updated

        return SyncPage(items=items, next_cursor=latest, has_more=len(items) >= _PAGE_SIZE)

    async def fetch_item(self, external_id: str) -> ExternalItem:
        """`external_id` is "owner/repo#number" - the same id `sync()` emits."""
        repo, _, number = external_id.rpartition("#")
        if not repo or not number.isdigit():
            raise ValueError(f"malformed GitHub external_id: {external_id!r} (expected 'owner/repo#123')")
        issue = await self._request("GET", f"/repos/{repo}/issues/{number}")
        return self._to_external_item(repo, issue)

    async def normalize(self, item: ExternalItem) -> NormalizedSource:
        """Flatten an issue or PR into the provider-agnostic shape the
        ingestion pipeline chunks and embeds."""
        payload = item.raw_payload
        number = payload.get("number")
        title = str(payload.get("title") or f"#{number}")
        body = str(payload.get("body") or "")
        state = str(payload.get("state") or "")
        labels = [str(label.get("name", "")) for label in payload.get("labels", []) if isinstance(label, dict)]
        author = str((payload.get("user") or {}).get("login", "unknown"))
        is_pr = "pull_request" in payload

        header_lines = [
            f"{'Pull request' if is_pr else 'Issue'} #{number}: {title}",
            f"Repository: {payload.get('_repo', '')}",
            f"State: {state}",
            f"Author: {author}",
        ]
        if labels:
            header_lines.append(f"Labels: {', '.join(labels)}")
        if payload.get("merged_at"):
            header_lines.append(f"Merged at: {payload['merged_at']}")
        elif payload.get("closed_at"):
            header_lines.append(f"Closed at: {payload['closed_at']}")

        extracted_text = "\n".join(header_lines) + ("\n\n" + body if body else "")

        return NormalizedSource(
            external_id=item.external_id,
            record_type=item.record_type,
            title=f"{payload.get('_repo', '')}#{number}: {title}",
            canonical_url=item.canonical_url,
            # updated_at is the version key: a re-sync of an unchanged issue
            # produces the same key and is deduplicated upstream rather than
            # creating a redundant source_version.
            version_key=str(payload.get("updated_at") or item.external_id),
            authored_at=item.authored_at,
            modified_at=item.modified_at,
            effective_at=item.modified_at or item.authored_at,
            extracted_text=extracted_text,
            metadata={
                "state": state,
                "labels": labels,
                "author": author,
                "is_pull_request": is_pr,
                "number": number,
            },
        )

    async def revoke(self) -> None:
        """Nothing to revoke server-side for a PAT: the credential lives in
        the deployment's environment, and removing the connector row stops
        every sync. Closing the client is the meaningful local cleanup."""
        await self.aclose()

    async def health_check(self) -> HealthResult:
        checked_at = datetime.now(UTC)
        if not self._settings.github_token.strip():
            return HealthResult(healthy=False, detail="GITHUB_TOKEN is not configured", checked_at=checked_at)
        try:
            user = await self._request("GET", "/user")
        except (GitHubAuthError, httpx.HTTPError) as exc:
            return HealthResult(healthy=False, detail=str(exc), checked_at=checked_at)
        return HealthResult(
            healthy=True, detail=f"authenticated as {user.get('login', 'unknown')}", checked_at=checked_at
        )

    async def aclose(self) -> None:
        if self._client is not None and self._owns_client:
            await self._client.aclose()
            self._client = None

    # ---- helpers -------------------------------------------------------

    @staticmethod
    def _to_external_item(repo: str, issue: dict[str, Any]) -> ExternalItem:
        number = issue.get("number")
        is_pr = "pull_request" in issue
        # Stash the repo on the payload so normalize() can title the record
        # without needing the sync loop's context.
        payload = {**issue, "_repo": repo}
        return ExternalItem(
            external_id=f"{repo}#{number}",
            record_type="GIT_PULL_REQUEST" if is_pr else "GIT_ISSUE",
            raw_payload=payload,
            canonical_url=issue.get("html_url"),
            authored_at=_parse_ts(issue.get("created_at")),
            modified_at=_parse_ts(issue.get("updated_at")),
        )


def _parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
