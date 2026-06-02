---
id: TASK-db-retention-audit
title: Audit database retention strategy
status: pending
type: research
team: Arquitecto de Base de Datos
supporting_teams: [Backend Senior, Arquitecto Python, PM]
roadmap_item: historical-data-maintenance
priority: high
---

# TASK-db-retention-audit - Audit database retention strategy

## Goal

Audit the current HLL Vietnam database/storage model and produce a precise retention strategy before any destructive cleanup is implemented.

## Context

The project stores live and historical RCON data, materialized matches, precomputed snapshots, player/event data and server snapshots.

We need to prevent the database from growing indefinitely, but we must not delete data required for:

- the latest 100 visible matches;
- current weekly leaderboards;
- previous-week fallback leaderboards;
- current monthly leaderboards;
- previous-month fallback leaderboards during the first 7 days of a new month;
- current or recent RCON materialization;
- current-match/live pages.

Important architectural decision:
Do not use native database scheduling, `pg_cron` or an external cron service for now. The future cleanup should be application-level, versioned, logged and executed from the existing `historical-runner`.

Known snapshot context:
Precomputed display snapshots should already be bounded because PostgreSQL stores them in `displayed_historical_snapshots` using a logical primary key `(server_key, snapshot_type, metric, snapshot_window)` and persistence uses upsert semantics. File-based snapshots also use deterministic paths by server/type/metric. This task must verify that assumption against the current code.

## Steps

1. Inspect the listed files first.
2. Identify all tables/files involved in:
   - RCON admin log events;
   - RCON materialized matches;
   - materialized player stats;
   - server snapshots;
   - displayed historical snapshots;
   - player event raw ledger;
   - Elo/MMR tables if present;
   - monthly rankings/checkpoints if present.
3. Determine which data is safe to delete and when.
4. Determine which data must be protected.
5. Determine the safe delete order to avoid orphan data.
6. Determine whether any foreign keys/cascade rules exist or are missing.
7. Create a concise retention audit document.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `backend/app/postgres_display_storage.py`
- `backend/app/historical_snapshot_storage.py`
- `backend/app/historical_runner.py`
- `backend/app/rcon_historical_worker.py`
- `backend/app/rcon_historical_read_model.py`
- `backend/app/rcon_historical_backfill.py`
- `backend/app/player_event_aggregates.py`

## Expected Files to Modify

- `ai/tasks/pending/TASK-db-retention-audit.md`
- `ai/reports/database-retention-audit.md`

If `ai/reports/*.md` is ignored by Git, create the report in:

- `ai/tasks/review/TASK-db-retention-audit-report.md`

and explain why in the outcome.

## Constraints

- Do not implement cleanup logic in this task.
- Do not delete data.
- Do not modify backend runtime behavior.
- Do not add Docker services.
- Do not touch `main` directly.
- Keep the report factual and based on the actual schema/code.
- Clearly separate confirmed facts from assumptions.
- Do not expand Elo/MMR functionality.

## Retention Rules To Validate

The future cleanup must protect:

- latest 100 closed/materialized matches;
- all matches from current month;
- all matches from previous month while `now.day <= 7`;
- all matches from current week;
- all matches from previous week if weekly fallback logic may still need them;
- child/player-stat rows belonging to protected matches;
- snapshot records currently addressed by frontend endpoints;
- current RCON/live data.

Candidate cleanup areas:

- old `server_snapshots`;
- non-critical old `rcon_admin_log_events`;
- old critical admin log events only after retention and protection checks;
- old materialized matches not protected by latest-100/month/week rules;
- child stats for deleted materialized matches;
- legacy/corrupt duplicate snapshots only if actually found.

AdminLog critical events:

- `kill`
- `match_start`
- `match_end`

AdminLog non-critical events:

- `chat`
- `message`
- `connected`
- `disconnected`
- `team_switch`
- `unknown`
- `kick`
- `ban`
- any other event not required for materialized stats/rankings.

## Validation

Run:

```powershell
python -m compileall backend/app
git diff --check
```

Also include recommended SQL audit commands in the report:

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

and table-specific row/age queries for the actual tables found.

## Outcome

Document:

- files inspected;
- tables/storage areas audited;
- safe-to-delete data;
- protected data;
- required delete order;
- risks;
- missing indexes/constraints if any;
- recommended implementation plan for the cleanup command.

Codex CLI must commit and push the completed task branch.

Suggested implementation branch:

`task/db-retention-audit`

Suggested commit message:

`docs: audit database retention strategy`

## Change Budget

Prefer fewer than 3 modified files.
No runtime changes.
No product code changes.
