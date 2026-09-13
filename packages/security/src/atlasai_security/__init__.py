"""RBAC helpers, credential-ref envelope encryption, payload hashing, and
log/prompt redaction. Depends only on atlasai_domain."""

from atlasai_security.crypto import CredentialDecryptionError, SecretCipher
from atlasai_security.jwt_tokens import (
    AccessTokenClaims,
    IssuedRefreshToken,
    TokenError,
    create_access_token,
    decode_access_token,
    hash_token,
    issue_refresh_token,
)
from atlasai_security.passwords import hash_password, verify_password
from atlasai_security.payload_hash import hash_payload
from atlasai_security.rbac import Permission, can_view_internal_evidence, role_has_permission
from atlasai_security.redaction import redact_value, structlog_redactor

__all__ = [
    "AccessTokenClaims",
    "CredentialDecryptionError",
    "IssuedRefreshToken",
    "Permission",
    "SecretCipher",
    "TokenError",
    "can_view_internal_evidence",
    "create_access_token",
    "decode_access_token",
    "hash_password",
    "hash_payload",
    "hash_token",
    "issue_refresh_token",
    "redact_value",
    "role_has_permission",
    "structlog_redactor",
    "verify_password",
]
