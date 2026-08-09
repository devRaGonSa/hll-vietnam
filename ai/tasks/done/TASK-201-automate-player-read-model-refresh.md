---
id: TASK-201-automate-player-read-model-refresh
title: Automate player read model refresh
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto de Base de Datos
  - Arquitecto Python
roadmap_item: foundation
priority: high
---

# TASK-201 - Automate player read model refresh

## Goal

Automate the periodic refresh of `player_search_index` and `player_period_stats` inside the existing backend historical runner so the public stats endpoints can keep using their read models without depending on manual operator refreshes.

## Context

Production already validates the full read-model chain required by the public player stats flows:

- `player_search_index` exists and `/api/stats/players/search` already uses `read_model=player-search-index` with `fallback_used=false`
- `player_period_stats` exists and `/api/stats/players/{player_id}` already uses `read_model=player-period-stats` with `fallback_used=false`
- `ranking_snapshots` / `ranking_snapshot_items` already exist
- `refresh-ranking-snapshots --limit 30` already runs in the periodic historical runner
- PostgreSQL is the operational storage target
- runtime fallback must remain preserved for player stats and ranking

The remaining gap is operational automation for the two player read models. The existing periodic runner in `backend/app/historical_runner.py` is the intended scheduler surface, so this task must extend that cycle instead of inventing a new scheduler. The cycle should keep `refresh-ranking-snapshots` and add dedicated, separately reported refresh steps for player search and player period stats.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Read the listed files first.
2. Inspect the current historical runner flow and the existing manual read-model refresh entrypoints.
3. Integrate `refresh_player_search_index(...)` into the periodic backend cycle.
4. Integrate `refresh_player_period_stats(...)` into the periodic backend cycle.
5. Keep `refresh-ranking-snapshots` in the same cycle and preserve its current behavior.
6. Run the cycle in this order unless the current runner architecture safely requires a different invariant:
   - existing RCON ingestion/materialization cycle
   - `player_search_index`
   - `player_period_stats`
   - `ranking_snapshots`
7. Report `player_search_index_result`, `player_period_stats_result` and `ranking_snapshot_result` separately.
8. Preserve visibility of failures and avoid hiding one read-model failure behind another. One failure should not necessarily prevent the remaining refresh attempts unless the runner already enforces a stricter global policy.
9. Preserve the manual CLIs and the public contracts of:
   - `/api/stats/players/search`
   - `/api/stats/players/{player_id}`
   - `/api/ranking`
10. Document the automatic runner refresh, inherited cadence, emergency manual commands, fallback preservation and final cycle order.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `backend/app/historical_runner.py`
- `backend/app/rcon_historical_player_stats.py`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/postgres_rcon_storage.py`
- `backend/app/payloads.py`
- `docs/player-search-read-model-plan.md`
- `docs/player-period-stats-read-model-plan.md`
- `docs/ranking-snapshot-read-model-plan.md`
- `scripts/run-stats-validation.ps1`
- `ai/tasks/done/TASK-197-automate-ranking-snapshot-refresh.md`
- `ai/tasks/done/TASK-198-add-player-search-read-model.md`
- `ai/tasks/done/TASK-199-add-player-period-stats-read-model.md`
- `ai/tasks/done/TASK-200-fix-player-profile-runtime-postgres-grouping.md`

## Expected Files to Modify

- `backend/app/historical_runner.py`
- `docs/player-search-read-model-plan.md`
- `docs/player-period-stats-read-model-plan.md`
- `docs/ranking-snapshot-read-model-plan.md`
- `scripts/run-stats-validation.ps1`
- `ai/tasks/in-progress/TASK-201-automate-player-read-model-refresh.md`

## Constraints

- Keep the change minimal and backend/documentation only.
- Do not execute `ai-platform run`.
- Do not modify frontend.
- Do not change design.
- Do not touch images or assets.
- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana `#03`.
- Do not mix visual corrections into this task.
- Preserve PostgreSQL as the operational storage target.
- Preserve runtime fallback for player stats and ranking.
- Do not break the manual CLIs:
  - `refresh-player-search-index`
  - `refresh-player-period-stats`
  - `refresh-ranking-snapshots`
  - `generate-ranking-snapshot`
- Do not change public contracts of:
  - `/api/stats/players/search`
  - `/api/stats/players/{player_id}`
  - `/api/ranking`

## Validation

Before completing the task ensure:

- `python -m py_compile backend/app/historical_runner.py backend/app/rcon_historical_player_stats.py`
- `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- local/import validation proves the runner calls:
  - `refresh_player_search_index(...)`
  - `refresh_player_period_stats(...)`
  - `refresh_ranking_snapshots(...)`
- validation proves the periodic cycle reports these results separately:
  - `player_search_index_result`
  - `player_period_stats_result`
  - `ranking_snapshot_result`
- validation proves the manual CLIs still work:
  - `refresh-player-search-index`
  - `refresh-player-period-stats`
  - `refresh-ranking-snapshots`
- validation proves `/api/stats/players/search` can still use `player-search-index`
- validation proves `/api/stats/players/{player_id}` can still use `player-period-stats`
- validation proves ranking snapshots are not broken
- `git diff --name-only` matches the expected scope

## Outcome

Implemented:

- `backend/app/historical_runner.py`
  - integrated automatic periodic refresh of `player_search_index`
  - integrated automatic periodic refresh of `player_period_stats`
  - preserved the existing `ranking_snapshots` refresh
  - the runner now reports:
    - `player_search_index_result`
    - `player_period_stats_result`
    - `ranking_snapshot_result`
  - one read-model failure is now reported explicitly and does not prevent the runner from attempting the remaining refresh steps in the same cycle
  - the runner returns `status=partial` when one of those periodic read-model refresh steps fails but the cycle continues
- `docs/player-search-read-model-plan.md`
  - documents automatic runner refresh
  - documents inherited cadence from `HLL_HISTORICAL_REFRESH_INTERVAL_SECONDS`
  - documents the emergency manual command
  - documents fallback preservation
- `docs/player-period-stats-read-model-plan.md`
  - documents automatic runner refresh
  - documents inherited cadence from `HLL_HISTORICAL_REFRESH_INTERVAL_SECONDS`
  - documents the emergency manual command
  - documents fallback preservation
- `docs/ranking-snapshot-read-model-plan.md`
  - documents the final runner order
  - documents that ranking refresh remains part of the same periodic cycle
  - documents cadence inheritance and fallback preservation
- `scripts/run-stats-validation.ps1`
  - validates that the runner calls the player read-model refreshes before ranking snapshots
  - validates separate result reporting
  - validates that a `player_search_index` refresh failure remains visible and does not stop the remaining periodic refresh attempts

Modified files:

- `backend/app/historical_runner.py`
- `docs/player-search-read-model-plan.md`
- `docs/player-period-stats-read-model-plan.md`
- `docs/ranking-snapshot-read-model-plan.md`
- `scripts/run-stats-validation.ps1`
- `ai/tasks/done/TASK-201-automate-player-read-model-refresh.md`

Final runner order:

1. existing RCON ingestion/materialization cycle
2. `player_search_index`
3. `player_period_stats`
4. `ranking_snapshots`

Added cycle results/logs:

- `player_search_index_result`
- `player_period_stats_result`
- `ranking_snapshot_result`
- start events:
  - `player-search-index-refresh-started`
  - `player-period-stats-refresh-started`
- failure events:
  - `player-search-index-refresh-failed`
  - `player-period-stats-refresh-failed`

Validations executed:

- `python -m py_compile backend/app/historical_runner.py backend/app/rcon_historical_player_stats.py`
- `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`

Production validation path:

- run one controlled backend cycle:
  - `python -m app.historical_runner --max-runs 1`
- verify the cycle output includes:
  - `player_search_index_result`
  - `player_period_stats_result`
  - `ranking_snapshot_result`
- confirm the player stats endpoints still report:
  - `/api/stats/players/search` -> `source.read_model=player-search-index`
  - `/api/stats/players/{player_id}` -> `source.read_model=player-period-stats`
- confirm `/api/ranking` still serves ranking snapshots when ready and preserves fallback behavior when a snapshot is missing
- if emergency rebuild is needed, operators can still run:
  - `python -m app.rcon_historical_player_stats refresh-player-search-index`
  - `python -m app.rcon_historical_player_stats refresh-player-period-stats`
  - `python -m app.rcon_historical_leaderboards refresh-ranking-snapshots --limit 30`

Pending limitations kept out of scope:

- the runner still refreshes the player read models for all supported public scopes even when a manual runner execution is limited with `--server`
- this task does not introduce a separate external scheduler or deployment-specific cron wiring
- live HTTP validation at `http://127.0.0.1:8000` was not available in this environment; route-contract validation passed via local Python imports instead

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
