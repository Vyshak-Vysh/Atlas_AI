# ADR-0008: Source-to-project association via `connector_scopes`, not a new column

## Status

Accepted.

## Context

`docs/ERD_FINAL.md`'s `source_records` table carries `tenant_id` but no
`project_id` — evidence is tenant-scoped, and the ERD's implied join path
for "which project does this evidence belong to" is
`source_records.connector_id -> connectors -> connector_scopes.project_id`.
Manual uploads need per-project association from the moment a file is
uploaded (before any requirement/curation step exists to imply it).

## Decision

`apps/api/services/upload_service.py` lazily creates one `MANUAL_UPLOAD`
connector per `(tenant, project)` the first time that project receives an
upload, plus a `connector_scopes` row scoping it to that project, and
reuses both on every subsequent upload to the same project. Every uploaded
`source_record.connector_id` points at that project's manual-upload
connector. `packages/retrieval`'s hybrid search and
`apps/api/services/source_service.py`'s access checks join through the
same path (`source_record -> connector -> connector_scopes.project_id`) to
scope queries and authorize access to a specific project's evidence.

No new column or table was added — this is entirely a matter of how the
existing `connectors`/`connector_scopes` tables are populated and queried.

## Consequences

Every project-scoped evidence query pays a four-table join
(`evidence_chunks -> source_versions -> source_records -> connectors ->
connector_scopes`). Acceptable at this build's scale; if it becomes a
bottleneck, a denormalized `source_records.project_id` column (added via a
migration, backfilled from this same join) would be the natural follow-up
— not attempted here since it would be schema drift from `ERD_FINAL.md`
without first confirming it's actually needed.
