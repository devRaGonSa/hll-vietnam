---
id: TASK-database-maintenance-docs
title: Document database maintenance operations
status: pending
type: documentation
team: PM
supporting_teams: [Backend Senior, Arquitecto de Base de Datos]
roadmap_item: historical-data-maintenance
priority: medium
---

# TASK-database-maintenance-docs - Document database maintenance operations

## Goal

Document how database maintenance works, how to audit database growth, and how to run dry-run/apply safely.

## Context

Database cleanup will be implemented as application-level maintenance and scheduled inside historical-runner.

Operators must understand:

- what data is deleted;
- what data is protected;
- how to preview deletes;
- how to enable/disable scheduled cleanup;
- how to verify table sizes;
- what not to do in Docker/Portainer.

## Steps

1. Inspect the listed files first.
2. Add or update operational documentation.
3. Include exact commands for PowerShell/Docker.
4. Include safety warnings.
5. Validate docs diff.
6. Commit and push the task branch.

## Files to Read First

- `README.md`
- `backend/README.md`
- `ai/README.md`
- `backend/app/database_maintenance.py`
- `backend/app/historical_runner.py`
- `docker-compose.yml`

## Expected Files to Modify

Preferred:

- `docs/database-maintenance.md`

Also update if relevant:

- `README.md`
- `backend/README.md`

Do not modify runtime code in this task.

## Required Documentation Content

Include sections:

- Overview
- Why cleanup is application-level and not `pg_cron`
- Scheduled cleanup inside `historical-runner`
- Environment variables
- Protected data
- Deleted data
- Dry-run command
- Apply command
- Table-size audit SQL
- Row-count/age audit SQL
- Logs to inspect
- Docker/Portainer warnings
- Rollback/restore considerations

Required environment variables:

- `HLL_DB_MAINTENANCE_ENABLED=false`
- `HLL_DB_MAINTENANCE_INTERVAL_SECONDS=43200`
- `HLL_RECENT_MATCHES_KEEP=100`
- `HLL_ADMIN_LOG_NONCRITICAL_RETENTION_DAYS=30`
- `HLL_ADMIN_LOG_CRITICAL_RETENTION_DAYS=90`
- `HLL_SERVER_SNAPSHOT_RETENTION_DAYS=14`
- `HLL_DB_MAINTENANCE_BATCH_SIZE=5000`

Required warnings:

- Never use `docker compose down -v` unless intentionally deleting volumes.
- Always review dry-run output before enabling apply in production.
- Do not manually delete protected match/stat rows from PostgreSQL.
- Keep backups before changing retention settings.
- Do not add Comunidad Hispana #03 back into RCON targets in this task.

Required SQL:

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

Also include table-specific examples for:

- admin log events by type/date;
- materialized matches by server/date;
- server snapshots by date;
- displayed snapshots count.

## Validation

Run:

```powershell
git diff --check
```

If README files are touched, ensure examples are consistent with the current Compose profiles.

## Outcome

Document:

- files changed;
- docs sections added;
- validation performed;
- any follow-up needed.

Codex CLI must commit and push the completed task branch.

Suggested implementation branch:

`task/database-maintenance-docs`

Suggested commit message:

`docs: document database maintenance operations`

## Change Budget

- Documentation only.
- Prefer fewer than 3 modified files.
