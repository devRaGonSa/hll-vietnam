# TASK-137-postgresql-concurrency-job-locking-and-operator-runbook-migration

## Goal

Replace SQLite-era timeout and file-lock coordination assumptions with a PostgreSQL-compatible concurrency model for manual commands, daemon jobs, and heavy writers, while keeping operator-facing diagnostics clear and actionable.

## Context

The current backend coordinates write-heavy jobs using SQLite and filesystem-local assumptions:

- `backend/app/writer_lock.py` implements file-based single-writer coordination derived from the SQLite storage path.
- `backend/app/config.py` exposes SQLite writer timeout, busy timeout, and writer-lock polling settings.
- `backend/app/historical_runner.py`, `backend/app/rcon_historical_worker.py`, and `backend/app/player_event_worker.py` participate in this coordination model.
- Operational behavior still assumes `/app/data`, local lock files, and stale lock recovery heuristics tied to container-local filesystem state.

A PostgreSQL migration is not complete if only the driver changes. Job coordination must also move to a database-compatible model so multiple backend processes or containers can coordinate without relying on shared local files.

## Steps

1. Inspect the listed files first and document the exact current writer-lock behavior, including manual preflight checks, wait behavior, stale lock recovery, and diagnostics payloads.
2. Define the PostgreSQL-era coordination strategy, preferring advisory locks or a clearly justified database-backed equivalent.
3. Map the current job types into the new coordination model:
   - manual commands
   - daemon loops
   - periodic runners
   - rebuild or rematerialization jobs
4. Define how lock acquisition, release, timeout, and conflict reporting behave under PostgreSQL.
5. Define how stale-lock scenarios are handled in a PostgreSQL world, including connection loss, crashed workers, and operator retries.
6. Replace file-based lock ownership and lock-file heartbeat semantics with PostgreSQL-native ownership semantics.
7. Update operator-facing diagnostics and runbook documentation so lock conflicts remain explicit and actionable.
8. Define what happens to old SQLite busy-timeout and writer-lock settings:
   - removed
   - transitional
   - replaced by PostgreSQL-era settings
9. Keep this task focused on coordination and operational behavior, not on domain storage logic.
10. Preserve a simple manual-operator workflow for local development and Docker usage.

## Files to Read First

- `AGENTS.md`
- `backend/app/writer_lock.py`
- `backend/app/historical_runner.py`
- `backend/app/rcon_historical_worker.py`
- `backend/app/player_event_worker.py`
- `backend/app/config.py`

## Expected Files to Modify

- `backend/app/writer_lock.py`
- `backend/app/config.py`
- `backend/app/historical_runner.py`
- `backend/app/rcon_historical_worker.py`
- `backend/app/player_event_worker.py`

## Constraints

- Do not keep file-based writer lock as the primary long-term coordination mechanism.
- The task must explicitly define the PostgreSQL-era coordination strategy, preferably:
  - advisory locks
  - or a clearly justified equivalent database-backed lock model
- The task must explain:
  - how manual commands behave
  - how daemon jobs behave
  - how conflicts are surfaced
  - how stale lock scenarios are handled
  - what happens to old SQLite busy-timeout settings
- Keep operator-facing diagnostics explicit and actionable.
- Do not redesign domain storage logic in this task.
- Do not silently downgrade concurrency guarantees during the migration.
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

- the PostgreSQL lock and concurrency model is clearly defined and implemented
- manual and daemon execution paths are both explicitly handled
- stale or crashed-worker scenarios are explicitly handled
- operator diagnostics remain clear and actionable
- old SQLite timeout or file-lock assumptions are removed, replaced, or clearly marked transitional
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
- PostgreSQL session-scoped advisory locking now replaces file-based writer coordination as the primary runtime model in `backend/app/writer_lock.py`.
- Manual command diagnostics now report PostgreSQL lock holder metadata, timeout behavior, and the automatic stale-lock behavior that comes from session release on disconnect instead of file cleanup.
- Active runtime settings now prefer `HLL_BACKEND_POSTGRES_ADVISORY_LOCK_TIMEOUT_SECONDS` and `HLL_BACKEND_POSTGRES_ADVISORY_LOCK_POLL_INTERVAL_SECONDS`, while the old writer-lock env vars are retained only as deprecated compatibility aliases.
- `app.historical_runner`, `app.rcon_historical_worker`, and `app.player_event_worker` now surface acquired/conflict/timeout payloads aligned with the PostgreSQL advisory-lock model.

### Modified Files

- `backend/app/writer_lock.py`
- `backend/app/config.py`
- `backend/app/historical_runner.py`
- `backend/app/rcon_historical_worker.py`
- `backend/app/player_event_worker.py`

### Validations Run

- `python -m py_compile app\\writer_lock.py app\\config.py app\\historical_runner.py app\\rcon_historical_worker.py app\\player_event_worker.py`
- real PostgreSQL advisory-lock runtime validation with a temporary PostgreSQL 16 cluster:
  - manual conflict against an active holder
  - daemon conflict against an active holder
  - reacquire after a forced failure inside the lock scope
  - backend bootstrap `/health` verification against PostgreSQL-primary runtime settings
- `git diff --name-only`

### Validation Results

- `py_compile`: passed
- live PostgreSQL advisory-lock runtime validation: passed
  - manual conflict returned an operator-facing conflict payload with active lock metadata
  - daemon conflict timed out cleanly with advisory-lock diagnostics instead of overlapping writers
  - advisory lock released correctly after a forced failure and was reacquired successfully by a new process
  - backend bootstrap still answered `GET /health` successfully after the PostgreSQL lock migration
- `git diff --name-only`: only the expected five backend files are part of the validated TASK-137 code scope

### Delivery Metadata

- Branch: `task/elo-canonical-rating-monthly`
- Commit SHA: `pending local TASK-137-only commit`
- Push executed: intentionally deferred
- Push policy note: runtime validation closed TASK-137, but push remains intentionally deferred because TASK-138 is still open and the user requested no push
