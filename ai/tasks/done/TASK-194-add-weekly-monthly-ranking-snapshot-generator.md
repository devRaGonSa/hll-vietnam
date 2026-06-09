---
id: TASK-194-add-weekly-monthly-ranking-snapshot-generator
title: Add weekly monthly ranking snapshot generator
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto de Base de Datos
  - Arquitecto Python
roadmap_item: foundation
priority: high
---

# TASK-194 - Add weekly monthly ranking snapshot generator

## Goal

Implement a manual weekly/monthly ranking snapshot generator plus CLI so PostgreSQL-backed `/api/ranking` can serve persisted global ranking snapshots instead of runtime fallback when operators generate the required combinations.

## Context

`TASK-191` introduced the snapshot-first read path for weekly/monthly global ranking, and `TASK-192` / `TASK-193` stabilized the PostgreSQL path and runtime fallback metrics. The missing piece is still out-of-band generation for `ranking_snapshots` and `ranking_snapshot_items`, so production ranking requests continue to return `snapshot_status=missing`, `freshness=runtime` and `fallback_used=true`.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Read the listed files first.
2. Add a manual generator for weekly/monthly ranking snapshots using the existing materialized RCON leaderboard logic and snapshot tables.
3. Expose a CLI command for one explicit combination; only add matrix generation if it remains small and justified.
4. Validate generated snapshot reads, preserved runtime fallback behavior and production-oriented run commands.
5. Document the manual generation workflow and recommended combinations.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/rcon_annual_rankings.py`
- `backend/app/routes.py`
- `backend/app/payloads.py`
- `backend/app/postgres_rcon_storage.py`
- `scripts/run-stats-validation.ps1`
- `docs/ranking-snapshot-read-model-plan.md`
- `docs/ranking-stats-performance-audit.md`
- `ai/tasks/done/TASK-191-serve-ranking-from-snapshots-with-runtime-fallback.md`
- `ai/tasks/done/TASK-192-fix-postgres-ranking-snapshot-schema.md`
- `ai/tasks/done/TASK-193-fix-postgres-ranking-derived-metrics.md`

## Expected Files to Modify

- `backend/app/rcon_historical_leaderboards.py`
- `scripts/run-stats-validation.ps1`
- `docs/ranking-snapshot-read-model-plan.md`
- `ai/tasks/done/TASK-194-add-weekly-monthly-ranking-snapshot-generator.md`

## Constraints

- Keep the change minimal.
- Do not modify frontend, assets or design.
- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.
- Keep annual ranking behavior unchanged unless a helper can be safely shared without changing annual contracts.
- Prefer the existing module pattern already used by `backend/app/rcon_annual_rankings.py`.
- Do not change `/api/ranking` unless strictly necessary for validation-safe compatibility.
- Keep PostgreSQL as the operational target and preserve SQLite compatibility already present in the shared backend path.

## Validation

Before completing the task ensure:

- `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- local import validation proves:
  - `generate_ranking_snapshot(timeframe="weekly", server_key="all", metric="kills", limit=20)` creates a snapshot
  - `get_latest_ranking_snapshot(...)` can read that snapshot
  - `/api/ranking?timeframe=weekly&server_id=all&metric=kills&limit=20` returns `snapshot_status=ready`
  - the same response returns `fallback_used=false`
  - requesting a combination without a snapshot still preserves runtime fallback when enabled
- document the manual CLI command for local and Docker execution
- `git diff --name-only` matches the expected scope

## Outcome

Implemented:

- `backend/app/rcon_historical_leaderboards.py`
  - `generate_ranking_snapshot(...)`
  - persistence helpers for `ranking_snapshots` and `ranking_snapshot_items`
  - manual CLI entrypoint:
    - `python -m app.rcon_historical_leaderboards generate-ranking-snapshot --timeframe weekly --server-key all --metric kills --limit 20`
- `scripts/run-stats-validation.ps1`
  - now validates a real generated weekly snapshot through:
    - direct function import
    - `get_latest_ranking_snapshot(...)`
    - `/api/ranking`
  - confirms generated snapshot reads return:
    - `snapshot_status=ready`
    - `fallback_used=false`
  - confirms runtime fallback still works for a missing combination
- `docs/ranking-snapshot-read-model-plan.md`
  - documents the manual command
  - documents the recommended weekly/monthly/server/metric matrix
  - documents suggested refresh cadence
  - documents the expected `ready` vs fallback response states

Supported generation scope:

- `timeframe`
  - `weekly`
  - `monthly`
- `server-key`
  - `all`
  - `all-servers`
  - `comunidad-hispana-01`
  - `comunidad-hispana-02`
- `metric`
  - `kills`
  - `deaths`
  - `teamkills`
  - `matches_considered`
  - `kd_ratio`
  - `kills_per_match`

Validations executed:

- `python -m compileall backend/app/rcon_historical_leaderboards.py backend/app/payloads.py backend/app/routes.py backend/app/postgres_rcon_storage.py`
- direct local import probe for `generate_ranking_snapshot(...)`
- `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- local CLI probe:
  - `python -m app.rcon_historical_leaderboards generate-ranking-snapshot --timeframe weekly --server-key all --metric kills --limit 20`

Validation notes:

- Live backend HTTP at `http://127.0.0.1:8000` was not available, so route validation completed through local imports and repository scripts.
- The manual CLI is unitary per `(timeframe, server-key, metric)` combination.
- A broader matrix helper was intentionally left out to keep the task small and verifiable.

Recommended Docker command for production:

- `docker compose exec backend python -m app.rcon_historical_leaderboards generate-ranking-snapshot --timeframe weekly --server-key all --metric kills --limit 20`

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
