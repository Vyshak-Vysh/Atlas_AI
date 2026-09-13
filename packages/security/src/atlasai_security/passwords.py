"""Password hashing for the built-in local auth provider."""

from __future__ import annotations

import bcrypt

_BCRYPT_ROUNDS = 12


def hash_password(plaintext: str) -> str:
    return bcrypt.hashpw(plaintext.encode("utf-8"), bcrypt.gensalt(_BCRYPT_ROUNDS)).decode("utf-8")


def verify_password(*, plaintext: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plaintext.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        # Malformed stored hash — never let a hash-format bug surface as a
        # successful login.
        return False
