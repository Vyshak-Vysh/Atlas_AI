# ADR-0005: Realtime agent-run progress via Redis pub/sub + SSE

## Status

Accepted.

## Context

Agent runs execute asynchronously in `apps/ai_atlas`'s Celery worker; the
frontend needs to show live progress through the bounded state machine
without polling.

## Decision

Redis pub/sub (`packages/db/redis_client.py`) — Redis is already a hard
dependency as the Celery broker, so this adds no new subsystem. The step
recorder (`apps/ai_atlas/agent_runner/checkpoint.py`) writes the
`agent_steps` row, commits, and only then publishes to
`agent_run:{run_id}:events`. `apps/api`'s `GET /api/v1/agent/runs/{id}
/events` subscribes to that channel *before* running its `agent_steps`
catch-up query (so a step written in the gap is never missed either way),
then streams via Server-Sent Events (`sse-starlette`). The frontend uses
`@microsoft/fetch-event-source` rather than the native `EventSource`,
because the latter cannot send an `Authorization` header and this system
uses bearer-token auth everywhere else.

Postgres `LISTEN`/`NOTIFY` was considered and rejected: its payload is
capped at 8000 bytes and it ties up a dedicated connection per subscriber
against a pool sized for OLTP traffic. Plain polling was rejected as
contrary to "realtime."

## Consequences

Realtime delivery is best-effort — if Redis pub/sub drops a message (e.g.
a subscriber briefly disconnects), the client can always fall back to
polling `GET /api/v1/agent/runs/{id}`, which reflects the same durable
`agent_steps`/`agent_runs` rows the event stream is derived from.
