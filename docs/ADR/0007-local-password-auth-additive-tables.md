# ADR-0007: Built-in email+password auth via two additive tables

## Status

Accepted.

## Context

`docs/ERD_FINAL.md`'s `users` table has no password column — the ERD
assumes an external identity provider. The build decision made with the
user before implementation started is a built-in email+password provider
instead (structured so a real OIDC/SSO provider can be swapped in later),
with no external IdP required to run the system.

## Decision

Add two tables not in the ERD's literal catalogue, kept fully separate
from `users` so that table stays byte-for-byte as specified:

- `local_credentials` (`user_id` PK/FK, `password_hash`, `updated_at`) —
  one row per user who authenticates via the local provider; a user
  authenticating solely via a future external OIDC provider would have no
  row here.
- `refresh_tokens` (`id`, `user_id`, `token_hash`, `expires_at`,
  `revoked_at`, `created_at`) — revocable, one-time-use refresh tokens.
  Only the SHA-256 hash is stored, mirroring how the password hash is
  handled; the raw token is only ever seen by the client.

Access tokens are short-lived, stateless JWTs (never persisted).

## Consequences

Adding a real OIDC provider later does not require touching `users` or
either additive table — a new `AuthProvider` implementation would issue
the same JWT shape and could coexist with `local_credentials` for users
who still authenticate locally.
