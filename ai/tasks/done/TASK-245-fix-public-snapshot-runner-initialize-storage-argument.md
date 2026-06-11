---
id: TASK-245
title: Fix public snapshot runner initialize storage argument
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto Python
roadmap_item: foundation
priority: high
---

# TASK-245 - Fix public snapshot runner initialize storage argument

## Goal

Fix the deployed manual public jobs that failed with `initialize_rcon_materialized_storage() got an unexpected keyword argument 'ensure_storage'`.

## Context

TASK-243 added `ensure_storage` gating in the ranking and historical snapshot paths, but one wrapper incorrectly propagated that keyword into `initialize_rcon_materialized_storage()`, whose signature only accepts `db_path`.

The failure was visible when running:

- `python -m app.historical_runner --public-job ranking-weekly`
- `python -m app.historical_runner --public-job ranking-monthly`
- `python -m app.historical_runner --public-job historical-weekly`
- `python -m app.historical_runner --public-job historical-monthly`

## Steps

1. Audited every `ensure_storage=` path around public snapshot generation.
2. Confirmed that `initialize_rcon_materialized_storage()` does not accept that keyword.
3. Moved the gating logic to a local path resolver in `rcon_historical_leaderboards`.
4. Kept `connect_postgres_compat(initialize=False)` for follow-up read/write connections after the one-time initialization point.
5. Added regression tests for both enabled and disabled initialization flows.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `backend/app/historical_runner.py`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/rcon_admin_log_materialization.py`

## Expected Files to Modify

- `backend/app/rcon_historical_leaderboards.py`
- `backend/tests/test_historical_snapshot_refresh.py`
- `docs/public-snapshot-refresh-schedule.md`

## Constraints

- Keep public GET endpoints snapshot-only.
- Do not touch frontend, assets or server configuration.
- Preserve the TASK-243 fixes for JSON serialization, duplicate ranking items and monthly MVP V2 fallback.

## Validation

- `python -m compileall backend/app`
- `cd backend; python -m unittest tests.test_historical_snapshot_refresh`
- `cd backend; python -m unittest tests.test_current_match_payload tests.test_rcon_admin_log_storage tests.test_historical_snapshot_refresh`

## Outcome

- Manual public jobs no longer pass an invalid keyword to `initialize_rcon_materialized_storage()`.
- `ensure_storage=True` still initializes materialized storage once through the wrapper layer.
- `ensure_storage=False` now skips the base initializer cleanly and relies on the existing non-DDL connection path.
- Regression coverage now asserts both enabled and disabled initialization flows.
