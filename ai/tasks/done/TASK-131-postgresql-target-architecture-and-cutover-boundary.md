# TASK-131-postgresql-target-architecture-and-cutover-boundary

## Goal

Define the exact PostgreSQL target architecture, storage ownership, and cutover boundary for the backend so the SQLite-to-PostgreSQL migration stays staged, explicit, and reviewable instead of becoming an uncontrolled mixed-storage rewrite.

## Context

The current backend persistence model is split across local SQLite files, filesystem JSON snapshots, and file-based writer coordination:

- `docker-compose.yml` mounts `./backend/data:/app/data` and does not define a PostgreSQL service.
- `backend/Dockerfile` exports `HLL_BACKEND_STORAGE_PATH=/app/data/hll_vietnam_dev.sqlite3`.
- `backend/app/config.py` is centered on `get_storage_path()` plus SQLite timeout and lock settings.
- `backend/app/sqlite_utils.py` centralizes `sqlite3`, `PRAGMA journal_mode = WAL`, and `PRAGMA busy_timeout`.
- `backend/app/storage.py` persists live snapshots in SQLite.
- `backend/app/historical_snapshot_storage.py` persists historical snapshot payloads as JSON files under `/app/data/snapshots`.
- `backend/app/historical_storage.py`, `backend/app/rcon_historical_storage.py`, `backend/app/player_event_storage.py`, `backend/app/elo_mmr_storage.py`, and `backend/app/writer_lock.py` assume SQLite or local filesystem semantics as the baseline.

Before implementation starts, the repository needs one authoritative task that defines the desired destination state and the boundary for the migration batch. This task exists to remove ambiguity about what PostgreSQL will own, what the filesystem will stop owning, what remains derived data, and how jobs coordinate when SQLite-era file locks disappear.

## Steps

1. Inspect the listed files first and capture the current persistence boundary exactly as it exists today.
2. Define the PostgreSQL target architecture for the backend as the primary durable store.
3. Explicitly map every current persistence concern into one of these categories:
   - primary PostgreSQL domain data
   - PostgreSQL materialized or snapshot read models
   - transitional compatibility surface
   - data that is no longer product storage after cutover
4. State the future role of:
   - live snapshot metadata
   - historical matches and player stats
   - RCON historical persistence
   - player event persistence
   - Elo/MMR persistence
   - snapshot payloads and snapshot metadata
5. State the future fate of:
   - `.sqlite3` files
   - SQLite WAL and busy-timeout assumptions
   - local file-based writer locks
   - `/app/data/snapshots` as product storage
6. Define the approved fast-read snapshot strategy for PostgreSQL and explicitly reject using plain SQL views as the universal solution.
7. Define the cutover boundary between transitional mixed mode and final PostgreSQL-primary mode, including what is allowed to coexist temporarily and what is not allowed to survive long-term.
8. Document the dependency order for TASK-132 through TASK-138 so later implementation tasks have a clear execution sequence.
9. Document only architecture and migration boundaries in this task. Do not implement backend runtime code, schema code, or feature code here.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `backend/README.md`
- `docker-compose.yml`
- `backend/app/config.py`

## Expected Files to Modify

- `docs/decisions.md`
- `docs/postgresql-target-architecture.md`
- `backend/README.md`

## Constraints

- Keep the implementation of this task documentation-only.
- Preserve HLL Vietnam project identity and repository structure.
- Do not introduce unnecessary frameworks, ORMs, or platform abstractions.
- Do not implement backend functionality in this task.
- The target architecture must assume PostgreSQL as the primary durable store for backend product data.
- The target architecture must not keep SQLite as a long-term primary runtime dependency.
- The target architecture must not treat `/app/data/snapshots` as the long-term primary product store for historical fast-read payloads.
- The target architecture must not rely on plain SQL views as the main strategy for all snapshot or read-model payloads.
- The target architecture should prefer explicit materialization tables, snapshot tables with `JSONB`, or a narrow hybrid where each choice is justified.
- The target architecture must explicitly describe what replaces file-based writer lock semantics after migration, with PostgreSQL-compatible coordination as the long-term direction.
- The task must define a staged migration path and must not describe a blind big-bang rewrite.
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

- the architecture document clearly defines PostgreSQL as the primary store
- the document explicitly states the fate of filesystem JSON snapshots
- the document explicitly states the fate of SQLite-only helpers and settings
- the document explicitly states the intended lock and concurrency model after migration
- the document clearly defines the cutover boundary between transitional and final states
- the document names the migration sequence dependency across TASK-132 through TASK-138
- no backend or frontend product code was modified
- no unrelated files were modified
- documentation remains consistent with the current repository state
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
