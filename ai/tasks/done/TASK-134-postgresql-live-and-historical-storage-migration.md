# TASK-134-postgresql-live-and-historical-storage-migration

## Goal

Migrate the live snapshot relational storage layer and the core historical relational storage layer from SQLite to PostgreSQL while preserving caller-facing behavior and keeping the scope limited to these foundational storage domains.

## Context

Two current modules form the base of the structured persistence model:

- `backend/app/storage.py` persists live snapshot metadata in SQLite and serves read paths such as latest snapshots and snapshot history.
- `backend/app/historical_storage.py` persists the core historical relational model and contains substantial SQLite-specific schema, normalization, compatibility, and read/write logic.

These modules also depend on:

- `backend/app/config.py` for `get_storage_path()` and SQLite runtime settings.
- `backend/app/sqlite_utils.py` for writer and readonly connections.
- `backend/app/historical_ingestion.py` for historical write flows into the relational store.

This migration stage must move the relational foundation first, before snapshot materialization, RCON-specific storage, player events, or Elo/MMR are migrated.

## Steps

1. Inspect the listed files first and map the exact public and internal functions in `storage.py` and `historical_storage.py` that assume SQLite.
2. Replace SQLite connection usage in these two storage domains with the shared PostgreSQL connection layer introduced earlier in the batch.
3. Rewrite schema and query usage for PostgreSQL only within these two domains.
4. Define how inserts, updates, and upserts behave under PostgreSQL, including conflict targets and stable identity rules.
5. Rewrite readonly query paths for PostgreSQL while preserving the shape and semantics expected by current callers.
6. Remove dependence on SQLite path existence checks, SQLite connection URIs, `PRAGMA` behavior, and SQLite-specific SQL constructs for these domains.
7. Keep the caller contract stable for:
   - live snapshot listing
   - live snapshot history
   - server-specific snapshot history
   - historical relational persistence and reads used by ingestion and payload builders
8. Update initialization flow so these modules depend on PostgreSQL schema bootstrap, not on inline SQLite file creation.
9. Explicitly document any SQL dialect differences that required rewrites, including placeholders, upsert syntax, row access assumptions, and date/time handling.
10. Do not include filesystem snapshot migration, RCON historical storage migration, player-event storage migration, or Elo/MMR storage migration in this task.

## Files to Read First

- `AGENTS.md`
- `backend/app/storage.py`
- `backend/app/historical_storage.py`
- `backend/app/historical_ingestion.py`
- `backend/app/config.py`
- `backend/app/sqlite_utils.py`

## Expected Files to Modify

- `backend/app/storage.py`
- `backend/app/historical_storage.py`
- `backend/app/historical_ingestion.py`
- `backend/app/config.py`
- `backend/app/postgres_utils.py`

## Constraints

- Keep the task focused on:
  - live snapshot relational persistence
  - historical relational persistence
- Do not include JSON or filesystem snapshot materialization migration in this task.
- Do not include Elo/MMR persistence migration in this task.
- Do not include player-event or RCON-specific storage migration in this task.
- The task must explicitly define:
  - how inserts and upserts change under PostgreSQL
  - how readonly read paths change
  - how SQL dialect differences are handled
  - how initialization stops depending on SQLite path existence
  - how caller-facing contracts remain stable
- Preserve API contract expectations for callers even if internal SQL changes significantly.
- Keep schema changes aligned with the migration framework introduced in TASK-133 instead of recreating schema inline.
- When this task is implemented later, no push may be executed while any sibling PostgreSQL migration task in the `TASK-131` to `TASK-138` batch still remains in `ai/tasks/pending/`.
- When this task is implemented later, push is allowed only if this task completes as the last remaining pending task of the batch.
- The final implementation response for this task must explicitly report:
  - modified files
  - validations run
  - validation results
  - branch
  - commit SHA
  - push executed or intentionally deferred

## Validation

Before completing the task ensure:

- the task outcome clearly isolates these two storage domains from the rest of the migration batch
- write paths in `storage.py` and `historical_storage.py` no longer depend on SQLite-only helpers
- readonly query paths are migrated and preserve caller-visible behavior
- SQL rewrite choices and PostgreSQL conflict handling are documented
- initialization no longer depends on SQLite file creation or SQLite URI assumptions for these domains
- unrelated domains such as snapshots, RCON storage, player events, and Elo/MMR were not migrated here
- no unrelated files were modified
- future implementation push policy is explicit:
  - no push while sibling PostgreSQL migration tasks in this batch remain pending
  - push only when the final pending task of this batch is completed
- future implementation reporting requirements are explicit:
  - modified files
  - validations run
  - validation results
  - branch
  - commit SHA
  - push executed or intentionally deferred

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
