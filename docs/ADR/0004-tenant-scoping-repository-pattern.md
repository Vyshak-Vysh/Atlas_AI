# ADR-0004: Tenant/project scoping via a repository pattern, not Postgres Row-Level Security

## Status

Accepted.

## Context

`docs/ERD_FINAL.md` critical integrity rule #8 requires "all tenant/project
authorization checks... before data access." Two mechanisms were
considered: Postgres Row-Level Security (RLS) with a `SET LOCAL
app.tenant_id` per request, or a repository-layer pattern that makes
tenant/project scoping a mandatory constructor argument.

## Decision

Use the repository pattern (`packages/db/repositories/base.py`):
`TenantScopedRepository` and `ProjectScopedRepository` require
`tenant_id`/`project_id` in their constructors and inject the
corresponding filter into every query method — a caller cannot construct
a query that skips it. Cross-tenant/cross-project lookups raise
`NotFoundError` uniformly (never a distinct "forbidden" shape, so a
response never reveals whether a resource exists in a tenant the caller
cannot see).

RLS was not chosen as the primary mechanism because `SET LOCAL` against a
pooled `asyncpg` connection is easy to get subtly wrong (a variable
leaking across pooled connections, or a reset that runs after an early
return) and harder to unit-test without a real database connection for
every negative-authorization case.

## Consequences

- Correctness depends on every new repository method being built on the
  scoped base classes — mitigated by `tests/integration/
  test_authorization_negative.py`, which exercises real cross-tenant
  access attempts against the live API.
- RLS remains available as an optional future defense-in-depth layer, to
  be added once the repository layer has a track record, not as a
  replacement for it.
