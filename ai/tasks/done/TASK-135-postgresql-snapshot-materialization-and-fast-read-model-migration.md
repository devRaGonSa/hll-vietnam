# TASK-135-postgresql-snapshot-materialization-and-fast-read-model-migration

## Goal

Replace filesystem-based historical snapshot persistence with a PostgreSQL-backed fast-read model that preserves current endpoint behavior while moving snapshot payload storage and metadata into the database.

## Context

`backend/app/historical_snapshot_storage.py` currently persists precomputed historical snapshots as JSON files under `/app/data/snapshots`. That layer is consumed by snapshot-oriented payload builders and routes that expect quick reads without recalculating the full historical model on every request.

Relevant current surfaces include:

- `backend/app/historical_snapshot_storage.py`
- `backend/app/historical_snapshots.py`
- `backend/app/historical_runner.py`
- `backend/app/routes.py`
- `backend/app/payloads.py`

The PostgreSQL target architecture should keep the fast-read intent but stop using filesystem JSON files as the primary product storage layer. The replacement must be explicit and PostgreSQL-native.

## Steps

1. Inspect the listed files first and map the current snapshot identity model, including snapshot type, metric, server scope, generated timestamps, source range, and stale markers.
2. Define the PostgreSQL-native replacement for historical snapshot persistence.
3. Use one of the approved strategies as the primary design:
   - explicit materialization tables
   - snapshot payload tables with `JSONB`
   - a narrowly justified hybrid of both
4. Explicitly reject plain SQL views as the universal answer for all historical snapshots.
5. Define how current snapshot identity maps into PostgreSQL keys, uniqueness rules, and update semantics.
6. Define how snapshot metadata is stored, including:
   - `generated_at`
   - `source_range_start`
   - `source_range_end`
   - `is_stale`
   - source policy or provenance if relevant
7. Migrate read and write paths so runner-driven materialization persists into PostgreSQL and payload builders read from PostgreSQL instead of filesystem JSON.
8. Preserve fast-read behavior for endpoints and keep payload contracts stable.
9. If a filesystem cache remains temporarily during transition, classify it as transitional only and make sure PostgreSQL is the primary source of truth.
10. Do not redesign the public payload shapes served by routes in this task.

## Files to Read First

- `AGENTS.md`
- `backend/app/historical_snapshot_storage.py`
- `backend/app/historical_snapshots.py`
- `backend/app/historical_runner.py`
- `backend/app/routes.py`
- `backend/app/payloads.py`

## Expected Files to Modify

- `backend/app/historical_snapshot_storage.py`
- `backend/app/historical_snapshots.py`
- `backend/app/historical_runner.py`
- `backend/app/payloads.py`
- `backend/db/migrations/`

## Constraints

- The task must not use plain SQL views as the universal answer for all snapshots.
- The task must define one of these as the primary strategy:
  - explicit materialization tables
  - snapshot payload tables with `JSONB`
  - a hybrid of both where each choice is explicitly justified
- The task must explicitly explain:
  - how current snapshot identity maps into PostgreSQL
  - how `generated_at`, `source_range`, and `is_stale` metadata are stored
  - how endpoint fast-read behavior is preserved
  - whether any remaining filesystem cache is transitional only
- The task must keep API payload contracts stable.
- The task must preserve the ability to precompute and refresh snapshots outside hot request paths.
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

- the PostgreSQL snapshot and materialization strategy is clearly defined and implemented
- plain SQL views are explicitly not the only general solution
- snapshot identity and uniqueness rules are explicit
- snapshot metadata fields are stored and surfaced correctly
- fast-read endpoint expectations are preserved
- any remaining filesystem cache is clearly documented as transitional only, if it exists at all
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
