"""Verify a file's actual content against its declared MIME type/extension
(TD_v2.md §4 manual-upload requirement) using the pure-Python `filetype`
package (magic-byte sniffing) — chosen over `python-magic` specifically so
this package has no system libmagic dependency on any platform, including
this project's Windows dev host.
"""

from __future__ import annotations

import filetype

_TEXT_MIME_TYPES = frozenset({"text/plain", "text/markdown", "text/csv"})


class MimeMismatchError(Exception):
    def __init__(self, *, declared: str, detected: str | None) -> None:
        self.declared = declared
        self.detected = detected
        super().__init__(f"declared MIME type {declared!r} does not match detected content ({detected!r})")


def validate_mime_type(data: bytes, declared_mime: str) -> None:
    """Raises MimeMismatchError if the content doesn't match; returns
    normally if it does. Never silently reclassifies the file — a mismatch
    is always a hard rejection (BR-020-adjacent: untrusted input is
    rejected, not guessed at)."""
    guess = filetype.guess(data)

    if declared_mime in _TEXT_MIME_TYPES:
        if guess is not None:
            # A binary signature was found where plain text was declared.
            raise MimeMismatchError(declared=declared_mime, detected=guess.mime)
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise MimeMismatchError(declared=declared_mime, detected=None) from exc
        return

    if guess is None or guess.mime != declared_mime:
        raise MimeMismatchError(declared=declared_mime, detected=guess.mime if guess else None)
