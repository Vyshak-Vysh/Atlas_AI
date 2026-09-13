"""Connector registry. `POST /api/v1/sources/connect` (apps/api) only ever
offers a provider that `is_configured()` — an inert connector (no OAuth app
credentials set) is never listed as available, a real guard rather than a
comment (see the implementation plan's "Connectors" section).
"""

from __future__ import annotations

from collections.abc import Callable

from atlasai_connectors.manual_upload.connector import ManualUploadConnector
from atlasai_connectors.protocol import Connector
from atlasai_domain.enums import ConnectorProvider

_REGISTRY: dict[ConnectorProvider, Callable[[], Connector]] = {
    ConnectorProvider.MANUAL_UPLOAD: ManualUploadConnector,
}

# Populated as each Release-4 connector lands (git_ci, gmail, msgraph,
# google_drive, meetings, pm_jira) — each entry gated behind its own
# `is_configured()` classmethod checking that provider's env vars.
_CONFIGURATION_CHECKS: dict[ConnectorProvider, Callable[[], bool]] = {
    ConnectorProvider.MANUAL_UPLOAD: lambda: True,
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
