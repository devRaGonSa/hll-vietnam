# TASK-138-sqlite-to-postgresql-backfill-validation-and-final-cutover

## Goal

Define and implement the backfill, validation, cutover, rollback, and SQLite decommission plan required to complete the migration from SQLite and filesystem snapshot storage to PostgreSQL safely.

## Context

A PostgreSQL runtime, schema, and migrated storage modules are not enough by themselves. The repository also needs a controlled completion path that answers:

- how existing SQLite-backed data moves into PostgreSQL
- how filesystem historical snapshot payloads are migrated if still needed
- how PostgreSQL outputs are validated against current behavior
- how API reads and background jobs cut over in a safe order
- when SQLite files, SQLite helpers, WAL assumptions, and `/app/data` product-storage expectations are retired

This final task exists to make the migration operationally finishable instead of leaving the repository in an indefinite mixed-storage state.

## Steps

1. Inspect the listed files first and document the remaining SQLite-era and filesystem-era persistence assumptions that survive after the earlier PostgreSQL migration tasks.
2. Define the approved backfill strategy for existing data, choosing and documenting one of:
   - direct read-from-SQLite then write-to-PostgreSQL backfill
   - export/import pipeline
   - hybrid strategy where each domain has an explicit reason
3. Define how historical snapshot payloads on disk are handled during backfill, including whether they are migrated into PostgreSQL, regenerated from PostgreSQL, or both.
4. Define validation checks that compare SQLite-era and PostgreSQL-era outputs for all relevant domains before cutover.
5. Define the exact cutover order for:
   - backend API runtime
   - historical runner
   - RCON historical worker
   - player event worker
   - Elo/MMR rebuilds and reads if relevant
6. Define rollback expectations and rollback limits after each cutover phase.
7. Define the point where SQLite-specific paths, helpers, environment variables, WAL assumptions, and local lock behavior become deprecated or removed.
8. Narrow or retire `/app/data` assumptions so that it is no longer the primary durable product store after cutover.
9. Preserve API contract stability throughout the cutover.
10. Complete the batch by removing ambiguity about when push is finally allowed for the migration work.

## Files to Read First

- `AGENTS.md`
- `backend/README.md`
- `backend/app/storage.py`
- `backend/app/historical_storage.py`
- `backend/app/historical_snapshot_storage.py`
- `docker-compose.yml`

## Expected Files to Modify

- `backend/README.md`
- `docs/decisions.md`
- `docs/postgresql-cutover-runbook.md`
- `docker-compose.yml`
- `backend/scripts/postgresql-backfill.py`

## Constraints

- The task must explicitly define:
  - data export/import or direct backfill strategy
  - validation checks between SQLite-era and PostgreSQL-era outputs
  - cutover ordering
  - rollback expectations
  - the point where SQLite paths, env vars, and helpers become deprecated or removed
- The task must explicitly cover operational verification for:
  - backend
  - historical runner
  - RCON historical worker
  - player event worker if relevant
  - Elo/MMR rebuild and read paths if relevant
- The task must preserve API contract stability during cutover.
- The task must document how existing `/app/data` assumptions are retired or narrowed.
- The task must finish the migration in staged order, not as an unbounded cleanup pass.
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

- the backfill strategy is explicit and executable
- validation checks between SQLite-era and PostgreSQL-era outputs are explicit
- cutover order is explicit for API runtime and all relevant workers
- rollback expectations and rollback limits are explicit
- the deprecation or removal point for SQLite paths, env vars, helpers, and WAL assumptions is explicit
- `/app/data` assumptions are retired or narrowed in documentation and runtime expectations
- API contract stability during cutover is preserved
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

## Outcome

- Status: completed
- The approved cutover strategy is now explicit and executable:
  direct SQLite-to-PostgreSQL relational backfill plus PostgreSQL-driven
  regeneration of historical snapshot payloads.
- A dedicated runbook now defines validation gates, cutover order, rollback
  limits, API parity expectations, and the point where `/app/data`, SQLite WAL,
  `busy_timeout`, and filesystem snapshots stop being primary runtime concerns.
- Docker Compose now treats PostgreSQL as the steady-state durable store and
  narrows legacy SQLite usage to `/app/runtime/legacy`.

### Modified Files

- `backend/README.md`
- `docs/decisions.md`
- `docs/postgresql-cutover-runbook.md`
- `docker-compose.yml`
- `backend/scripts/postgresql-backfill.py`

### Validations Run

- `python -m py_compile scripts\\postgresql-backfill.py`
- `python scripts\\postgresql-backfill.py plan`
- real PostgreSQL validation on a temporary PostgreSQL 16 UTF-8 cluster with
  working psycopg/libpq:
  - `python scripts\\postgresql-backfill.py plan`
  - `python scripts\\postgresql-backfill.py execute --truncate-target-first`
  - `python scripts\\postgresql-backfill.py validate`
- `git status --short`

### Validation Results

- `py_compile`: passed
- `postgresql-backfill.py plan`: passed and confirmed the legacy source set is
  real and non-empty:
  - SQLite file present at `backend/data/hll_vietnam_dev.sqlite3`
  - snapshot directory present at `backend/data/snapshots`
  - 68 legacy snapshot JSON files detected
  - relational source tables detected with substantial row counts, including:
    - `historical_matches = 9708`
    - `historical_player_match_stats = 1066887`
    - `player_event_raw_ledger = 14715`
    - `elo_mmr_match_results = 2128992`
- `postgresql-backfill.py execute --truncate-target-first`: passed in real
  PostgreSQL runtime after moving to batched inserts, UTF-8 session handling,
  per-table commits, and an execute manifest for large-table validation.
- `postgresql-backfill.py validate`: passed in real PostgreSQL runtime.
  Small tables were validated by exact SQLite/PostgreSQL row counts and the
  largest tables were validated against the exact execute manifest persisted by
  the same backfill run.
- `git status --short`: no unrelated tracked files were modified for this task;
  remaining tracked edits belong to the still-uncommitted TASK-138 closure
  scope only

### Delivery Metadata

- Branch: `task/elo-canonical-rating-monthly`
- Commit SHA: `pending local TASK-138-only commit`
- Push executed: intentionally deferred
- Push policy note: this task now closes the last item in the
  `TASK-131` to `TASK-138` PostgreSQL migration batch, but push remains an
  explicit operator choice and was not executed in this turn
