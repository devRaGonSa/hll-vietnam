---
id: TASK-historical-runner-maintenance-scheduler
title: Schedule database maintenance inside historical runner
status: pending
type: backend
team: Arquitecto Python
supporting_teams: [Backend Senior, Arquitecto de Base de Datos]
roadmap_item: historical-data-maintenance
priority: high
---

# TASK-historical-runner-maintenance-scheduler - Schedule database maintenance inside historical runner

## Goal

Integrate the database maintenance cleanup command into the existing historical-runner loop without adding a new Docker service or external scheduler.

## Context

The project already has historical-runner as an advanced service. We want database maintenance to run as an internal assistant task from that runner.

No new container/service should be added.

The runner must continue working even if maintenance fails.

The maintenance must be disabled by default and enabled only by environment configuration.

## Steps

1. Inspect the listed files first.
2. Add configuration for maintenance scheduler.
3. Integrate a due-check into historical-runner.
4. Call the cleanup command in apply mode only when enabled and due.
5. Ensure cleanup failures do not crash the runner.
6. Add tests.
7. Validate.
8. Commit and push the task branch.

## Files to Read First

- `AGENTS.md`
- `backend/app/historical_runner.py`
- `backend/app/config.py`
- `backend/app/database_maintenance.py`
- `backend/tests/`
- `docker-compose.yml`
- `deploy/portainer/docker-compose.nas.yml` if present

## Expected Files to Modify

- `backend/app/historical_runner.py`
- `backend/app/config.py`
- `backend/tests/test_historical_runner_maintenance.py`

Optional only if documentation is needed for env examples:

- `backend/.env.example`

Do not add a new Docker service in this task.

## Functional Requirements

Add env/config:

- `HLL_DB_MAINTENANCE_ENABLED=false`
- `HLL_DB_MAINTENANCE_INTERVAL_SECONDS=43200`
- `HLL_RECENT_MATCHES_KEEP=100`
- `HLL_ADMIN_LOG_NONCRITICAL_RETENTION_DAYS=30`
- `HLL_ADMIN_LOG_CRITICAL_RETENTION_DAYS=90`
- `HLL_SERVER_SNAPSHOT_RETENTION_DAYS=14`
- `HLL_DB_MAINTENANCE_BATCH_SIZE=5000`

Behavior:

- if `HLL_DB_MAINTENANCE_ENABLED` is false or missing, runner logs skip and does nothing;
- if enabled, runner checks whether maintenance is due;
- default interval is 12 hours;
- if due, runner invokes database maintenance apply mode;
- if not due, runner logs not-due at low verbosity or structured event;
- if maintenance fails, runner logs error and continues normal historical processing;
- maintenance must not run concurrently with snapshot refresh/backfill if existing writer locks apply;
- if lock is busy, skip or fail gracefully without leaving runner stuck.

Required logs:

- `database-maintenance-scheduler-skipped-disabled`
- `database-maintenance-scheduler-skipped-not-due`
- `database-maintenance-scheduler-started`
- `database-maintenance-scheduler-completed`
- `database-maintenance-scheduler-failed`
- `database-maintenance-scheduler-lock-busy` if applicable

## Constraints

- Do not add `database-maintenance` as a new compose service.
- Do not use `pg_cron`.
- Do not use host cron.
- Do not change frontend.
- Do not change public API contracts.
- Do not run cleanup by default unless env explicitly enables it.
- Do not block the runner indefinitely.

## Tests

Create tests for:

- scheduler disabled does not call cleanup;
- scheduler enabled but not due does not call cleanup;
- scheduler enabled and due calls cleanup;
- cleanup exception is logged and runner continues;
- interval parsing handles invalid values safely;
- maintenance state is tracked in-process or persisted safely according to existing runner design.

Use mocks/stubs to avoid real destructive cleanup in scheduler tests.

## Validation

Run:

```powershell
PYTHONPATH=backend python -m unittest backend.tests.test_historical_runner_maintenance
PYTHONPATH=backend python -m unittest backend.tests.test_database_maintenance
python -m compileall backend/app
git diff --check
```

Optional runtime validation:

```powershell
docker compose --profile advanced up -d --build historical-runner
docker compose logs --tail=200 historical-runner
```

Only enable maintenance in local test with a short interval and safe dataset.

## Outcome

Document:

- validation commands run;
- whether a local runner smoke test was performed;
- logs observed;
- exact files changed;
- any follow-up task needed.

Codex CLI must commit and push the completed task branch.

Suggested implementation branch:

`task/historical-runner-maintenance-scheduler`

Suggested commit message:

`feat: schedule database maintenance in historical runner`

## Change Budget

- Prefer fewer than 4 modified files.
- No Docker service addition.
- Keep scheduling logic small and testable.
