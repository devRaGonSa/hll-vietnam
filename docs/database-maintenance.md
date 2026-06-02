# Database Maintenance

## Overview

HLL Vietnam keeps database cleanup at the application level.

The current maintenance scope is intentionally narrow:

- old `server_snapshots`;
- old non-critical `rcon_admin_log_events`;
- old critical `rcon_admin_log_events` only after retention and protected-match checks;
- old non-protected `rcon_materialized_matches`;
- dependent `rcon_match_player_stats` for deleted matches.

The first maintenance pass does not routinely delete:

- `displayed_historical_snapshots`;
- file-based snapshots under `backend/data/snapshots/`;
- public-scoreboard `historical_*` fallback tables;
- `player_event_raw_ledger` and its worker metadata;
- Elo/MMR tables;
- Comunidad Hispana #03 data reactivation or targets.

## Why Application-Level And Not `pg_cron`

Cleanup is versioned in backend code instead of delegated to `pg_cron`, host cron, or a separate container because the retention logic depends on product rules:

- keep the latest 100 closed materialized matches;
- keep the current month;
- keep the previous month during the first 7 days of a new month;
- keep the current week;
- keep the previous week when weekly fallback may still need it;
- keep child stats for protected matches;
- avoid breaking current/live pages that still read recent AdminLog data.

Those rules belong with the application’s read and write model, not inside database-only scheduling.

## Scheduled Cleanup Inside `historical-runner`

Database maintenance is scheduled inside `app.historical_runner`.

Behavior:

- disabled by default;
- no extra Docker service is added for maintenance;
- the runner checks whether maintenance is due;
- when enabled and due, the runner invokes `python -m app.database_maintenance cleanup --apply` behavior through the shared Python function;
- failures are logged and do not crash the historical runner loop;
- cleanup runs under the same writer-lock coordination used by the historical writer flows.

Relevant structured log events:

- `database-maintenance-scheduler-skipped-disabled`
- `database-maintenance-scheduler-skipped-not-due`
- `database-maintenance-scheduler-started`
- `database-maintenance-scheduler-completed`
- `database-maintenance-scheduler-failed`

## Environment Variables

Required maintenance-related variables:

```text
HLL_DB_MAINTENANCE_ENABLED=false
HLL_DB_MAINTENANCE_INTERVAL_SECONDS=43200
HLL_RECENT_MATCHES_KEEP=100
HLL_ADMIN_LOG_NONCRITICAL_RETENTION_DAYS=30
HLL_ADMIN_LOG_CRITICAL_RETENTION_DAYS=90
HLL_SERVER_SNAPSHOT_RETENTION_DAYS=14
HLL_DB_MAINTENANCE_BATCH_SIZE=5000
```

Meaning:

- `HLL_DB_MAINTENANCE_ENABLED`
  Enables scheduled apply mode inside `historical-runner`.
- `HLL_DB_MAINTENANCE_INTERVAL_SECONDS`
  Default scheduler interval. `43200` means every 12 hours.
- `HLL_RECENT_MATCHES_KEEP`
  Number of latest closed materialized matches that must always be protected.
- `HLL_ADMIN_LOG_NONCRITICAL_RETENTION_DAYS`
  Retention for non-critical AdminLog events such as chat/connect/disconnect.
- `HLL_ADMIN_LOG_CRITICAL_RETENTION_DAYS`
  Retention for critical AdminLog events such as `kill`, `match_start`, `match_end`.
- `HLL_SERVER_SNAPSHOT_RETENTION_DAYS`
  Retention for live server snapshots.
- `HLL_DB_MAINTENANCE_BATCH_SIZE`
  Delete batch size for apply mode.

## Protected Data

The cleanup command protects:

- latest 100 closed materialized matches by default;
- current month materialized matches;
- previous month materialized matches when the current day is `1` through `7`;
- current week materialized matches;
- previous week materialized matches when weekly fallback may still need them;
- `rcon_match_player_stats` belonging to protected matches;
- current/live AdminLog data required for visible current-match surfaces;
- `displayed_historical_snapshots`;
- file snapshots in `backend/data/snapshots/`.

If a match timestamp cannot be interpreted safely, that match is skipped and protected instead of deleted.

## Deleted Data

Apply mode is currently allowed to delete:

- `server_snapshots` older than retention;
- non-critical `rcon_admin_log_events` older than retention;
- critical `rcon_admin_log_events` older than retention only when they are not required by protected materialized match ranges;
- non-protected `rcon_materialized_matches`;
- dependent `rcon_match_player_stats` for deleted matches.

Current critical AdminLog event types:

- `kill`
- `match_start`
- `match_end`

## Dry-Run Command

From `backend/`:

```powershell
python -m app.database_maintenance cleanup --dry-run
```

From the repository root with the backend package on `PYTHONPATH`:

```powershell
$env:PYTHONPATH='backend'
python -m app.database_maintenance cleanup --dry-run
```

Inside Docker Compose:

```powershell
docker compose exec backend python -m app.database_maintenance cleanup --dry-run
```

Useful dry-run options:

```powershell
docker compose exec backend python -m app.database_maintenance cleanup --dry-run `
  --recent-matches-keep 100 `
  --admin-log-noncritical-retention-days 30 `
  --admin-log-critical-retention-days 90 `
  --server-snapshot-retention-days 14 `
  --batch-size 5000
```

Dry-run is the safe preview path and should be reviewed before any production apply.

## Apply Command

Local module execution:

```powershell
python -m app.database_maintenance cleanup --apply
```

Docker Compose:

```powershell
docker compose exec backend python -m app.database_maintenance cleanup --apply
```

One-off local validation with a fixed time anchor:

```powershell
python -m app.database_maintenance cleanup --apply --now 2026-06-20T12:00:00Z
```

Optional maintenance vacuum/analyze:

```powershell
python -m app.database_maintenance cleanup --apply --vacuum-analyze
```

## Table-Size Audit SQL

```sql
select
  schemaname,
  relname as table_name,
  pg_size_pretty(pg_total_relation_size(relid)) as total_size,
  pg_size_pretty(pg_relation_size(relid)) as table_size,
  pg_size_pretty(pg_total_relation_size(relid) - pg_relation_size(relid)) as indexes_size,
  n_live_tup as estimated_rows,
  n_dead_tup as estimated_dead_rows
from pg_stat_user_tables
order by pg_total_relation_size(relid) desc;
```

## Row-Count And Age Audit SQL

### AdminLog events by type/date

```sql
select
  event_type,
  count(*) as row_count,
  min(event_timestamp) as first_event_timestamp,
  max(event_timestamp) as last_event_timestamp,
  min(server_time) as first_server_time,
  max(server_time) as last_server_time
from rcon_admin_log_events
group by event_type
order by row_count desc, event_type asc;
```

### Materialized matches by server/date

```sql
select
  target_key,
  source_basis,
  count(*) as matches,
  min(coalesce(ended_at, started_at)) as first_closed_at,
  max(coalesce(ended_at, started_at)) as last_closed_at
from rcon_materialized_matches
group by target_key, source_basis
order by target_key asc, source_basis asc;
```

### Server snapshots by date

```sql
select
  server_id,
  min(captured_at) as first_captured_at,
  max(captured_at) as last_captured_at,
  count(*) as snapshot_rows
from server_snapshots
group by server_id
order by last_captured_at desc;
```

### Displayed snapshots count

```sql
select
  snapshot_type,
  metric,
  snapshot_window,
  count(*) as snapshot_rows,
  min(generated_at) as first_generated_at,
  max(generated_at) as last_generated_at
from displayed_historical_snapshots
group by snapshot_type, metric, snapshot_window
order by snapshot_type asc, metric asc, snapshot_window asc;
```

## Logs To Inspect

The cleanup command emits JSON logs. Minimum events to look for:

- `database-maintenance-started`
- `database-maintenance-plan`
- `database-maintenance-table-skipped`
- `database-maintenance-delete-batch`
- `database-maintenance-completed`
- `database-maintenance-error`

Examples:

```powershell
docker compose logs --tail=200 backend
docker compose logs --tail=200 historical-runner
```

If scheduled cleanup is enabled:

```powershell
docker compose logs --tail=200 historical-runner
```

## Docker And Portainer Warnings

- Never use `docker compose down -v` unless you intentionally want to delete PostgreSQL and mounted volume data.
- Always review dry-run output before enabling apply in production.
- Do not manually delete protected match or player-stat rows from PostgreSQL.
- Keep backups before changing retention settings.
- Do not add Comunidad Hispana #03 back into RCON targets in this task.
- Do not add a separate maintenance container, host cron, or `pg_cron` job for this feature.

For Portainer-style operations the same warning applies:

- deleting volumes is destructive;
- maintenance should run through the application command, not through manual table purges.

## Rollback And Restore Considerations

- Retention changes are destructive when apply mode runs.
- Keep a PostgreSQL backup before enabling scheduled apply in production.
- If cleanup removes too much data, recovery is restore-based, not “undo last delete.”
- Favor dry-run, smaller batch sizes, and reviewed retention values before long-running scheduled apply.

## Safe Operator Flow

1. Audit table size and row ages with the SQL above.
2. Run dry-run locally or in Compose.
3. Review protected counts and candidate counts in JSON output.
4. Enable `HLL_DB_MAINTENANCE_ENABLED=true` only after dry-run review.
5. Monitor `historical-runner` logs for scheduler events and cleanup completion.
