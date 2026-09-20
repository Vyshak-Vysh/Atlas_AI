"""Connector registry. `POST /api/v1/sources/connect` (apps/api) only ever
offers a provider that `is_configured()` — an inert connector (no OAuth app
credentials set) is never listed as available, a real guard rather than a
comment (see the implementation plan's "Connectors" section).
"""

from __future__ import annotations

from collections.abc import Callable

from atlasai_connectors.git_ci.connector import GitHubConnector
from atlasai_connectors.manual_upload.connector import ManualUploadConnector
from atlasai_connectors.protocol import Connector
from atlasai_domain.enums import ConnectorProvider

_REGISTRY: dict[ConnectorProvider, Callable[[], Connector]] = {
    ConnectorProvider.MANUAL_UPLOAD: ManualUploadConnector,
    ConnectorProvider.GIT_CI_GITHUB: GitHubConnector,
}

# Each entry is gated behind that provider's own `is_configured()` check, so
# a provider whose credentials are absent is never offered as available.
# gmail, msgraph, google_drive, meetings and pm_jira are declared in
# ConnectorProvider and rendered in the UI, but have no adapter yet and so
# deliberately appear in neither map — `list_available_providers()` omits
# them and `get_connector()` raises KeyError rather than pretending.
_CONFIGURATION_CHECKS: dict[ConnectorProvider, Callable[[], bool]] = {
    ConnectorProvider.MANUAL_UPLOAD: lambda: True,
    ConnectorProvider.GIT_CI_GITHUB: GitHubConnector.is_configured,
}


def list_available_providers() -> list[ConnectorProvider]:
    return [provider for provider, is_configured in _CONFIGURATION_CHECKS.items() if is_configured()]


def get_connector(provider: ConnectorProvider) -> Connector:
    if provider not in _REGISTRY:
        raise KeyError(f"unknown connector provider: {provider}")
    is_configured = _CONFIGURATION_CHECKS.get(provider)
    if is_configured is not None and not is_configured():
        raise PermissionError(f"connector provider {provider} is not configured")
    return _REGISTRY[provider]()
