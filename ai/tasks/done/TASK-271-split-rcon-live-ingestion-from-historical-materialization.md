---
id: TASK-271
title: Split RCON live ingestion from historical materialization
status: done
type: backend
team: Backend Senior
supporting_teams: ["Arquitecto Python"]
roadmap_item: current-match
priority: high
---

# TASK-271 - Split RCON live ingestion from historical materialization

## Goal

Separate near-real-time AdminLog ingestion for current-match freshness from the slow historical materialization path so `/api/current-match/kills` and `/api/current-match/players` can stay fresh without waiting on heavy historical work.

## Context

Production evidence shows the current combined worker design is starving the current-match read model:

- production service `hll-vietnam-rcon-historical-worker-1` currently runs `python -m app.rcon_historical_worker loop`
- configured interval is `HLL_RCON_HISTORICAL_CAPTURE_INTERVAL_SECONDS=2`
- configured AdminLog lookback is `HLL_BACKEND_RCON_ADMIN_LOG_LOOKBACK_MINUTES=10`
- real `rcon_historical_capture_runs` durations are around `15-30` minutes
- recent runs overlapped and one failed with PostgreSQL deadlock
- each cycle materializes roughly `838k` player-stat rows and updates roughly `392-394` materialized matches
- `/api/current-match/kills` and `/api/current-match/players` read `rcon_admin_log_events`, not live CRCON/RCON per public request

This means the current-match feed problem is not primarily frontend rendering. The source table is not being refreshed frequently enough because live AdminLog ingestion is coupled to heavy historical materialization.

This task must preserve the current product identity and must not change frontend layout, CSS, assets, RCON hosts, ports, passwords, server list, `27001`, ranking semantics, Elo/MMR activation, or reintroduce `comunidad-hispana-03`.

## Steps

1. Inspect the current historical worker, current-match worker, AdminLog ingestion/storage, materialization path, API read path and Portainer deployment.
2. Implement a dedicated lightweight live AdminLog worker that only refreshes `rcon_admin_log_events`.
3. Reduce repeated PostgreSQL schema initialization in the live path by moving obvious DDL/init work out of hot loops and request reads.
4. Add no-overlap protection for heavy historical materialization so concurrent heavy runs skip cleanly instead of overlapping.
5. Update Portainer deployment so live ingestion and heavy historical materialization run as separate services with safe cadences.
6. Add or update focused tests and refresh the current-match freshness documentation with post-deploy validation commands.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/backend-senior.md`
- `backend/app/rcon_historical_worker.py`
- `backend/app/rcon_current_match_worker.py`
- `backend/app/rcon_admin_log_ingestion.py`
- `backend/app/rcon_admin_log_storage.py`
- `backend/app/postgres_rcon_storage.py`
- `backend/app/payloads.py`
- `deploy/portainer/docker-compose.nas.yml`
- `docs/current-match-adminlog-freshness.md`

## Expected Files to Modify

- `ai/tasks/in-progress/TASK-271-split-rcon-live-ingestion-from-historical-materialization.md`
- `backend/app/rcon_current_match_worker.py`
- `backend/app/rcon_admin_log_storage.py`
- `backend/app/postgres_rcon_storage.py`
- `backend/app/rcon_historical_storage.py`
- `backend/app/rcon_historical_worker.py`
- `backend/tests/test_rcon_current_match_worker.py`
- `backend/tests/test_rcon_historical_worker.py`
- `backend/tests/test_current_match_payload.py`
- `deploy/portainer/docker-compose.nas.yml`
- `docs/current-match-adminlog-freshness.md`

## Constraints

- Do not run `ai-platform run`.
- Do not commit or push.
- Do not use `git add .`.
- Do not touch `ai/system-metrics.md`.
- Do not include `tmp/`.
- Do not include TASK-204, TASK-242 or unrelated in-progress/done tasks.
- Do not touch weapon assets, map assets or clan assets.
- Do not touch frontend layout or CSS.
- Do not change RCON hosts, ports, passwords, `27001` or the configured server list.
- Do not reintroduce `comunidad-hispana-03`.
- Do not reactivate Elo/MMR.
- Do not change ranking semantics or fabricate support rankings.
- Do not change annual tops/player search behavior except where explicitly needed to stop them from blocking live ingestion.
- Keep the change backend/deployment/documentation scoped and reviewable.

## Validation

Before completing the task ensure:

- `python -m compileall backend/app`
- `cd backend; python -m unittest tests.test_current_match_payload`
- `cd backend; python -m unittest tests.test_rcon_historical_worker`
- `cd backend; python -m unittest tests.test_rcon_current_match_worker`
- `git diff --name-only` matches the intended scope
- no unrelated dirty files were modified
- documentation reflects the new live worker split and post-deploy checks

## Outcome

Implemented scope:

- dedicated live AdminLog worker path kept in `backend/app/rcon_current_match_worker.py`
- live worker storage initialization moved out of the hot loop body and out of per-target persistence calls
- live worker no longer waits on the shared long-running backend writer lock
- current-match persistence stays idempotent through the existing `rcon_admin_log_events` dedupe path
- historical capture/materialization path gained a single-running historical guard and returns `skipped` with `already-running` when a heavy run is still active
- Portainer deployment now splits `rcon-live-adminlog-worker` from `rcon-historical-worker`
- heavy historical cadence was set explicitly to `900` seconds in the Portainer compose file

Validation completed:

- `python -m compileall backend/app`
- `cd backend; python -m unittest tests.test_current_match_payload`
- `cd backend; python -m unittest tests.test_rcon_historical_worker`
- `cd backend; python -m unittest tests.test_rcon_current_match_worker`

Post-deploy hotfix note:

- live AdminLog PostgreSQL startup now initializes only AdminLog tables instead of the full historical/materialization schema path
- the old `idx_rcon_historical_single_running_historical` unique index is removed from schema bootstrap and dropped when present
- PostgreSQL historical single-running protection now uses a runtime advisory lock on the heavy historical worker path
- duplicate or stale historical `running` rows no longer crash the live worker startup path

Follow-up intentionally left out of central scope:

- `TEAM KILL` parser correctness remains a separate follow-up task unless handled later with a tiny isolated patch

## Production Hotfix Root Cause

The TASK-271 split originally added the PostgreSQL unique index
`idx_rcon_historical_single_running_historical` as a schema-level historical
single-running guard. Production already had more than one
`rcon_historical_capture_runs` row with `mode='historical'`, so full PostgreSQL
schema initialization attempted to create a unique index over non-unique
existing data and failed with `psycopg.errors.UniqueViolation`.

The live AdminLog worker called `initialize_rcon_admin_log_storage()` on startup.
Before the hotfix, that PostgreSQL path delegated to full RCON schema bootstrap,
so live AdminLog ingestion could crash because of historical capture-run state.

## Production Hotfix Fix

- Removed creation of `idx_rcon_historical_single_running_historical` from
  runtime PostgreSQL schema SQL.
- Added an idempotent `DROP INDEX IF EXISTS
  idx_rcon_historical_single_running_historical` cleanup to full PostgreSQL
  bootstrap.
- Added `initialize_postgres_admin_log_storage()` so the live AdminLog worker
  initializes only `rcon_admin_log_events` and profile snapshot tables.
- Replaced PostgreSQL historical overlap protection with
  `pg_try_advisory_lock()` on the heavy historical path only.
- Kept SQLite historical overlap protection query-based with stale `running`
  rows marked after the existing runtime timeout.

## Production Hotfix Validation

- Live worker startup is independent from duplicate or stale
  `mode='historical'` capture rows.
- The live worker persists AdminLog rows idempotently and does not call
  `materialize_rcon_admin_log`.
- The historical worker returns `skipped` with reason `already-running` when the
  PostgreSQL advisory lock is unavailable.
- Runtime schema code no longer creates
  `idx_rcon_historical_single_running_historical`.

## Remaining Risks

- Existing stale PostgreSQL `running` rows remain historical audit data; they no
  longer provide locking semantics and should be interpreted through worker
  logs plus advisory-lock behavior.
- Live freshness still depends on RCON AdminLog availability and credentials per
  configured trusted target.
- `TEAM KILL` AdminLog parser correctness remains a separate follow-up.

## Change Budget

- Prefer fewer than 5 modified files when feasible, but accept a slightly larger backend/deploy/docs scope if required to complete the split safely.
- Prefer focused edits over broad refactors.
- Split out follow-up correctness issues instead of expanding scope unnecessarily.
