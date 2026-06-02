---
id: TASK-database-maintenance-cleanup-command
title: Add database maintenance cleanup command
status: pending
type: backend
team: Backend Senior
supporting_teams: [Arquitecto de Base de Datos, Arquitecto Python]
roadmap_item: historical-data-maintenance
priority: high
---

# TASK-database-maintenance-cleanup-command - Add database maintenance cleanup command

## Goal

Implement a safe backend cleanup command with dry-run/apply modes to remove database data that is no longer needed while preserving all data required for visible history and leaderboards.

## Context

The project should keep the database bounded without manually deleting data.

The command will later be scheduled from historical-runner, but this task only implements the cleanup module and tests.

The cleanup must not rely on native PostgreSQL scheduling or a new Docker service.

The cleanup must protect:

- latest 100 closed/materialized matches;
- current month;
- previous month during the first 7 days of the new month;
- current week;
- previous week if fallback weekly logic may need it;
- child/player stats for protected matches;
- current live/RCON data.

## Steps

1. Inspect the listed files first.
2. Add a backend module for database maintenance.
3. Provide a CLI entry point:
   - `python -m app.database_maintenance cleanup --dry-run`
   - `python -m app.database_maintenance cleanup --apply`
4. Make dry-run the default behavior.
5. Add JSON logs for planning, batches and completion.
6. Add tests.
7. Validate locally.
8. Commit and push the task branch.

## Files to Read First

- `AGENTS.md`
- `backend/app/config.py`
- `backend/app/postgres_display_storage.py`
- `backend/app/historical_runner.py`
- `backend/app/rcon_historical_read_model.py`
- `backend/app/rcon_historical_backfill.py`
- `backend/tests/`

## Expected Files to Modify

- `backend/app/database_maintenance.py`
- `backend/app/config.py`
- `backend/tests/test_database_maintenance.py`

Optional only if required by existing test helpers:

- `backend/tests/conftest.py`
- `backend/tests/test_*.py`

Do not modify frontend files in this task.

## Functional Requirements

Create a cleanup command:

```powershell
python -m app.database_maintenance cleanup --dry-run
python -m app.database_maintenance cleanup --apply
```

Supported options:

- `--recent-matches-keep`
- `--admin-log-noncritical-retention-days`
- `--admin-log-critical-retention-days`
- `--server-snapshot-retention-days`
- `--batch-size`
- `--vacuum-analyze`
- `--now`

Environment defaults:

- `HLL_RECENT_MATCHES_KEEP=100`
- `HLL_ADMIN_LOG_NONCRITICAL_RETENTION_DAYS=30`
- `HLL_ADMIN_LOG_CRITICAL_RETENTION_DAYS=90`
- `HLL_SERVER_SNAPSHOT_RETENTION_DAYS=14`
- `HLL_DB_MAINTENANCE_BATCH_SIZE=5000`

Dry-run behavior:

- calculate all candidate rows;
- do not delete anything;
- log exactly what would be deleted;
- return status ok.

Apply behavior:

- delete only candidate rows;
- delete in batches;
- use transactions safely;
- do not block indefinitely;
- log deleted row counts;
- return status ok even if deleted counts are zero.

Retention Logic

Protected materialized matches:

- latest N closed matches, default N = 100;
- current month matches;
- previous month matches if now.day <= 7;
- current week matches;
- previous week matches if weekly fallback may need them;
- any match whose end/start timestamp cannot be safely interpreted should be skipped/protected, not deleted.

Delete materialized matches only if:

- not in protected latest N;
- not in protected current/previous month window;
- not in protected current/previous week window;
- older than the relevant protected windows;
- child stats/events that depend on the match are handled first.

AdminLog critical events:

- `kill`
- `match_start`
- `match_end`

Critical events may only be deleted after `HLL_ADMIN_LOG_CRITICAL_RETENTION_DAYS` and only if they are not needed for protected materialized matches/windows.

AdminLog non-critical events may be deleted after `HLL_ADMIN_LOG_NONCRITICAL_RETENTION_DAYS`.

Server snapshots may be deleted after `HLL_SERVER_SNAPSHOT_RETENTION_DAYS`.

`displayed_historical_snapshots` should not be routinely deleted because it is keyed/upserted. Only skip or report suspicious legacy/corrupt records; do not aggressively delete snapshots in this task.

## Safety Requirements

- If an optional table does not exist, log a controlled skip and continue.
- If PostgreSQL URL is not configured and the app is in SQLite mode, either support SQLite safely or return a clear unsupported message, depending on existing architecture.
- Do not leave orphan rows.
- Do not delete from unrelated Elo/MMR tables unless the audit proves exact dependency and task scope is explicitly updated.
- Use existing project lock/writer-lock patterns if present.
- Cleanup failure must produce JSON error output.

## Required JSON Log Events

At minimum:

- `database-maintenance-started`
- `database-maintenance-plan`
- `database-maintenance-table-skipped`
- `database-maintenance-delete-batch`
- `database-maintenance-completed`
- `database-maintenance-error`

## Tests

Create `backend/tests/test_database_maintenance.py`.

Minimum cases:

- dry-run does not delete.
- apply deletes old server snapshots.
- apply deletes old non-critical admin log events.
- apply preserves critical events within retention.
- apply preserves latest 100 materialized matches.
- apply preserves current month matches.
- apply preserves previous month when now.day <= 7.
- apply preserves current week.
- apply preserves previous week when fallback protection applies.
- apply deletes an old non-protected materialized match.
- child/player stats for deleted matches are deleted first or handled without orphans.
- missing optional tables are logged and do not crash cleanup.

## Validation

Run:

```powershell
PYTHONPATH=backend python -m unittest backend.tests.test_database_maintenance
python -m compileall backend/app
git diff --check
```

Also manually run:

```powershell
docker compose exec backend python -m app.database_maintenance cleanup --dry-run
```

or, if backend container is unavailable:

```powershell
cd backend
python -m app.database_maintenance cleanup --dry-run
```

Document which one was used.

## Outcome

Document:

- validation commands run;
- dry-run output summary;
- any existing unrelated test failures;
- exact files changed;
- any follow-up task needed instead of expanding scope.

Codex CLI must commit and push the completed task branch.

Suggested implementation branch:

`task/database-maintenance-cleanup-command`

Suggested commit message:

`feat: add database maintenance cleanup command`

## Change Budget

Prefer fewer than 5 modified files.
Prefer focused backend-only changes.
Split follow-up tasks if implementation exceeds safe scope.
