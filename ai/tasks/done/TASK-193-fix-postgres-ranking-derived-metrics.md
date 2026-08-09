---
id: TASK-193-fix-postgres-ranking-derived-metrics
title: Fix PostgreSQL ranking derived metrics
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto Python
  - Arquitecto de Base de Datos
roadmap_item: foundation
priority: high
---

# TASK-193 - Fix PostgreSQL ranking derived metrics

## Goal

Apply a backend hotfix so `kd_ratio` and `kills_per_match` work correctly on PostgreSQL when `/api/ranking` falls back to the runtime materialized leaderboard path.

## Context

Production weekly/monthly ranking snapshots are currently missing, so `/api/ranking` falls back to runtime aggregation. In that fallback path, the shared SQL uses `ROUND(double precision, integer)`, which is accepted by SQLite patterns but fails in PostgreSQL and breaks derived metrics while base metrics like `kills`, `deaths`, `teamkills` and `matches_considered` should remain operational.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Read the listed files first.
2. Apply only the scoped backend hotfix for derived ranking metrics.
3. Validate the result and document the root cause, fix and operational follow-up.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/postgres_rcon_storage.py`
- `backend/app/payloads.py`
- `backend/app/routes.py`
- `scripts/run-stats-validation.ps1`
- `ai/tasks/done/TASK-185-add-ranking-extra-metrics-backend-support.md`
- `ai/tasks/done/TASK-191-serve-ranking-from-snapshots-with-runtime-fallback.md`
- `ai/tasks/done/TASK-192-fix-postgres-ranking-snapshot-schema.md`

## Expected Files to Modify

- `backend/app/rcon_historical_leaderboards.py`
- `scripts/run-stats-validation.ps1`, only if a regression check is needed
- `ai/tasks/done/TASK-193-fix-postgres-ranking-derived-metrics.md`

## Constraints

- Keep the change minimal.
- Do not create new features.
- Do not modify frontend, images, assets or design.
- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.
- Avoid `ROUND(double precision, integer)` on PostgreSQL.
- Prefer safe numeric casting or Python-side rounding while preserving SQLite compatibility if it already exists.
- Keep public contracts unchanged unless strictly necessary.
- Preserve `kills`, `deaths`, `teamkills` and `matches_considered` behavior.

## Validation

Before completing the task ensure:

- `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- validate:
  - `/api/ranking?timeframe=weekly&metric=kd_ratio&limit=20`
  - `/api/ranking?timeframe=monthly&metric=kills_per_match&limit=20`
  - `/api/ranking?timeframe=weekly&metric=kills&limit=20`
  - `/api/ranking?timeframe=weekly&metric=deaths&limit=20`
  - `/api/ranking?timeframe=weekly&metric=matches_considered&limit=20`
- confirm the missing weekly/monthly snapshots explain latency but not the `kd_ratio` / `kills_per_match` PostgreSQL error
- `git diff --name-only` matches the expected scope

## Outcome

- Root cause:
  - `backend/app/rcon_historical_leaderboards.py` built shared SQL for `kd_ratio` and `kills_per_match` with `ROUND(..., 2)` over `REAL`-cast arithmetic.
  - That pattern works on the SQLite path but fails on PostgreSQL fallback reads because PostgreSQL does not define `round(double precision, integer)`.
  - The failure path matches production: `build_global_ranking_payload` -> `list_rcon_materialized_leaderboard` -> `_fetch_leaderboard_rows`.
- Applied change:
  - Replaced SQLite-oriented `REAL` casts in derived metric SQL with `NUMERIC` casts before division and rounding.
  - Kept the same public ranking route and preserved base metrics:
    - `kills`
    - `deaths`
    - `teamkills`
    - `matches_considered`
  - Kept Python-side item normalization unchanged so response contracts remain stable.
  - Added regression checks in `scripts/run-stats-validation.ps1` to assert derived metric SQL no longer uses `AS REAL` and now uses `AS NUMERIC`.
- Validations executed:
  - `python -m compileall backend/app/rcon_historical_leaderboards.py backend/app/payloads.py backend/app/routes.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
  - `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
  - local route-resolution probes for:
    - `/api/ranking?timeframe=weekly&metric=kd_ratio&limit=20`
    - `/api/ranking?timeframe=monthly&metric=kills_per_match&limit=20`
    - `/api/ranking?timeframe=weekly&metric=kills&limit=20`
    - `/api/ranking?timeframe=weekly&metric=deaths&limit=20`
    - `/api/ranking?timeframe=weekly&metric=matches_considered&limit=20`
- Validation results:
  - All requested ranking probes resolved with HTTP 200 via local route imports.
  - In this environment they returned `snapshot_status=missing` and `fallback_used=true`, which is consistent with missing weekly/monthly snapshots.
  - No backend HTTP service was available at `http://127.0.0.1:8000`, so endpoint validation completed through local imports and repository scripts.
- Operational confirmation:
  - Missing weekly/monthly snapshots explain the slower runtime fallback path.
  - Missing snapshots do not explain the `kd_ratio` / `kills_per_match` crash; that error came from PostgreSQL-incompatible rounding SQL in the runtime fallback query.
- Scope review:
  - Task-owned changes:
    - `backend/app/rcon_historical_leaderboards.py`
    - `scripts/run-stats-validation.ps1`
    - `ai/tasks/done/TASK-193-fix-postgres-ranking-derived-metrics.md`
  - `git diff --name-only` also showed a pre-existing unrelated modification:
    - `ai/system-metrics.md`
  - Existing untracked frontend assets were left untouched.
- Recommended next step:
  - generate and maintain weekly/monthly ranking snapshots so `/api/ranking` stops paying the runtime fallback cost in production

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
