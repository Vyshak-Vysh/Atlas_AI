"""structlog configuration shared by every module in this app.

The redaction processor from packages/security runs on every log event
before it's rendered, so no call site has to remember not to log a secret
(TD_v2.md §10: "Redaction in logs and client drafts").
"""

from __future__ import annotations

import logging
import sys
from typing import Any, cast

import structlog

from atlasai_api.settings import Settings
from atlasai_security import structlog_redactor


def configure_logging() -> None:
    settings = Settings()
    logging.basicConfig(stream=sys.stdout, level=settings.log_level, format="%(message)s")

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            # structlog's Processor stub is looser than our redactor's
            # precise dict[str, Any] -> dict[str, Any] signature.
            cast(Any, structlog_redactor),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(settings.log_level)),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    return cast(structlog.BoundLogger, structlog.get_logger(name))
