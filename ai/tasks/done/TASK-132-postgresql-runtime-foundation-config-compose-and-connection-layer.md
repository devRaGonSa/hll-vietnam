# TASK-132-postgresql-runtime-foundation-config-compose-and-connection-layer

## Goal

Prepare the backend runtime foundation for PostgreSQL by introducing the minimum required container, configuration, dependency, and connection-layer changes without yet migrating domain storage logic.

## Context

The current runtime foundation is SQLite-centric:

- `docker-compose.yml` mounts `./backend/data:/app/data` and has no PostgreSQL service.
- `backend/Dockerfile` exports `HLL_BACKEND_STORAGE_PATH=/app/data/hll_vietnam_dev.sqlite3`.
- `backend/requirements.txt` is effectively stdlib-only in practice.
- `backend/app/config.py` exposes SQLite path, SQLite writer timeout, busy timeout, and file-lock timing settings.
- `backend/app/sqlite_utils.py` is the shared connection layer for current persistence modules.

The migration batch needs a runtime base before schema and storage modules can be ported. This task should establish the minimum PostgreSQL-capable runtime and clearly define how old SQLite environment variables become transitional, deprecated, or removed later in the batch.

## Steps

1. Inspect the listed files first and confirm the current runtime assumptions around `/app/data`, SQLite, and container startup.
2. Add the minimum PostgreSQL Python dependency stack, preferring `psycopg` and a small explicit connection layer over a heavy ORM.
3. Extend Docker Compose with a PostgreSQL service definition suitable for local development and containerized backend execution.
4. Define the environment variable contract for PostgreSQL connectivity, including host, port, database, user, password, and any DSN form if both are supported.
5. Define backend configuration helpers that read PostgreSQL settings without breaking the staged migration order.
6. Introduce or define the new shared PostgreSQL connection bootstrap layer and decide whether pooling is needed at this stage or intentionally deferred.
7. Define healthcheck expectations for the PostgreSQL service and for backend startup ordering in Docker Compose.
8. Define how old SQLite runtime variables behave in this stage:
   - still required
   - transitional
   - deprecated but tolerated
   - removed later
9. Explicitly decide whether the migration runner bootstrap belongs in this task or is deferred to TASK-133, and document that decision in the task outcome.
10. Do not migrate domain SQL, storage modules, or API payload contracts in this task.

## Files to Read First

- `AGENTS.md`
- `backend/README.md`
- `backend/requirements.txt`
- `backend/Dockerfile`
- `docker-compose.yml`
- `backend/app/config.py`

## Expected Files to Modify

- `backend/requirements.txt`
- `backend/Dockerfile`
- `docker-compose.yml`
- `backend/app/config.py`
- `backend/app/postgres_utils.py`

## Constraints

- Keep the scope limited to runtime foundation only.
- Do not migrate domain storage logic in this task.
- Do not redesign API payloads or endpoint contracts in this task.
- Prefer a minimal PostgreSQL Python stack such as `psycopg` plus a small explicit connection layer instead of introducing a heavy ORM by default.
- The task must explicitly cover:
  - new PostgreSQL environment variables
  - Docker Compose PostgreSQL service
  - container networking assumptions
  - service healthcheck expectations
  - backend startup dependency expectations
  - connection bootstrap layer
  - transitional or deprecated handling for SQLite env vars
- The task must explicitly decide whether a small migration runner is introduced here or deferred to TASK-133.
- The task must preserve the ability to stage the migration in multiple steps instead of forcing immediate domain cutover.
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

- the runtime changes clearly scope dependencies, Docker/runtime changes, config changes, and the new PostgreSQL connection layer
- the task outcome explicitly states whether migration-runner bootstrap is included here or deferred to TASK-133
- PostgreSQL configuration is defined without yet migrating domain storage modules
- old SQLite runtime variables are classified as active, transitional, deprecated, or future removal
- Docker Compose assumptions for backend-to-database connectivity are explicit
- no domain storage logic was migrated
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
