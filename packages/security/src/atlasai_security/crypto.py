"""Envelope encryption for connector credential references.

TD_v2.md §3 requires connector tokens to be encrypted and never placed in
prompts or logs; ERD_FINAL.md rule #9 requires raw provider credentials to
never be stored in the database tables themselves. The pattern here: the
real OAuth token/secret is encrypted with this module and only the
resulting ciphertext (plus a key version prefix) is stored in
`connectors.credential_ref` — never the plaintext token.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from atlasai_security.settings import CredentialEncryptionSettings


class CredentialDecryptionError(Exception):
    pass


class SecretCipher:
    """Thin wrapper around Fernet so callers never touch the raw key or
    choose their own encryption scheme. `CREDENTIAL_ENCRYPTION_KEY` must be
    a urlsafe-base64-encoded 32-byte key (`Fernet.generate_key()`)."""

    def __init__(self, key: str | None = None) -> None:
        resolved_key = key or CredentialEncryptionSettings().credential_encryption_key
        self._fernet = Fernet(resolved_key.encode("utf-8"))

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise CredentialDecryptionError("credential_ref could not be decrypted") from exc
