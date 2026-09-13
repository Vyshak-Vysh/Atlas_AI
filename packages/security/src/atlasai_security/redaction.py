"""Log and prompt redaction (TD_v2.md §10 security gates: "Redaction in
logs and client drafts"; connector rule: "Never place access tokens in
prompts, logs, or source text.").

`structlog_redactor` is registered as a structlog processor in every app's
logging setup (see apps/api/src/atlasai_api/logging.py and the ai_atlas
equivalent) so redaction happens at the one place all structured log events
pass through, rather than relying on every call site to remember not to log
a secret.
"""

from __future__ import annotations

import re
from typing import Any

_SENSITIVE_KEY_PATTERN = re.compile(
    r"(password|secret|token|credential|api[_-]?key|authorization|access_key)", re.IGNORECASE
)
_BEARER_TOKEN_PATTERN = re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE)
_REDACTED = "[REDACTED]"


def redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return _BEARER_TOKEN_PATTERN.sub(f"Bearer {_REDACTED}", value)
    if isinstance(value, dict):
        return {k: redact_value(v) if not _SENSITIVE_KEY_PATTERN.search(k) else _REDACTED for k, v in value.items()}
    if isinstance(value, list):
        return [redact_value(v) for v in value]
    return value


def structlog_redactor(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:  # noqa: ARG001
    return {
        key: (_REDACTED if _SENSITIVE_KEY_PATTERN.search(key) else redact_value(value))
        for key, value in event_dict.items()
    }
