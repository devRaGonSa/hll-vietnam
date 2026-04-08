# TASK-133-postgresql-core-schema-and-bootstrap-migration-runner

## Goal

Define and implement the PostgreSQL schema bootstrap and migration mechanism that replaces ad-hoc SQLite initialization inside runtime modules with one explicit, reviewable migration path.

## Context

Current persistence modules contain schema creation and compatibility logic inline with SQLite runtime code. The repository needs a single migration story before individual storage domains are ported:

- `backend/app/sqlite_utils.py` centralizes SQLite connection behavior but not a PostgreSQL migration workflow.
- `backend/app/storage.py` creates and evolves tables inline for live snapshot persistence.
- `backend/app/historical_storage.py` includes legacy schema handling, compatibility migration behavior, and normalization work tied to SQLite initialization paths.
- The current runtime has no dedicated PostgreSQL schema versioning or migration runner.

If schema bootstrap is not centralized first, later storage migrations will duplicate connection logic, schema assumptions, and startup behavior across multiple domains.

## Steps

1. Inspect the listed files first and identify where schema creation and schema-evolution behavior currently happen inline.
2. Define the repository location for PostgreSQL migrations and keep that location stable for the rest of the batch.
3. Introduce the bootstrap migration mechanism for PostgreSQL, using SQL-first migrations or a very small migration runner instead of a heavyweight framework unless clearly justified.
4. Define how schema versioning is tracked in PostgreSQL.
5. Define how migrations are executed:
   - locally from the backend workspace
   - in Docker Compose
   - in container startup or a dedicated migration command, whichever is chosen
6. Define the initial bootstrap schema boundary for PostgreSQL. It must include the core relational foundation required before downstream storage tasks can migrate.
7. Explicitly decide which tables belong in the initial bootstrap set and which are intentionally deferred to later migration tasks.
8. Prevent repetition of the old pattern where runtime hot paths perform heavyweight schema creation, compatibility renames, or normalization work automatically.
9. Do not fully port all domain storage logic in this task.
10. Do not include snapshot materialization payload migration in this task; that belongs to TASK-135.

## Files to Read First

- `AGENTS.md`
- `backend/app/config.py`
- `backend/app/sqlite_utils.py`
- `backend/app/storage.py`
- `backend/app/historical_storage.py`
- `backend/README.md`

## Expected Files to Modify

- `backend/README.md`
- `backend/app/config.py`
- `backend/app/postgres_utils.py`
- `backend/db/migrations/`
- `backend/scripts/run-migrations.py`

## Constraints

- Keep the scope limited to migration/bootstrap infrastructure and the initial PostgreSQL schema shape.
- Do not fully port all module logic here.
- Do not mix snapshot-materialization payload migration into this task.
- The task must explicitly define:
  - where migrations live in the repo
  - how migrations are executed locally and in Docker
  - how schema versioning is tracked
  - which domain tables belong to the initial bootstrap set
  - how bootstrap is invoked without hiding schema work inside hot runtime paths
- Prefer SQL-first migrations or a very small migration runner instead of a heavy migration framework unless there is a concrete technical justification.
- The task must explicitly prevent repeating the old pattern of heavyweight schema and normalization work inside live request paths or worker startup paths.
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

- the migration runner mechanism is clearly defined and implemented
- the schema location is stable and explicit
- the initial schema bootstrap coverage is documented and intentionally bounded
- the runtime invocation path for migrations is clear for local and Docker usage
- schema version tracking is explicit and testable
- runtime modules are no longer expected to own heavyweight schema bootstrap behavior for PostgreSQL
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
