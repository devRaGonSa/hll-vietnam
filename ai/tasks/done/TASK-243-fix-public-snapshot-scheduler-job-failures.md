---
id: TASK-243
title: Fix public snapshot scheduler job failures
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto Python
roadmap_item: foundation
priority: high
---

# TASK-243 - Fix public snapshot scheduler job failures

## Goal

Fix the real failures found when running manual public snapshot jobs through `python -m app.historical_runner --public-job ...`.

## Context

After TASK-240 the public HTTP audit was healthy, but manual runner jobs still exposed four operational problems:

- CLI JSON serialization could crash on `datetime`
- ranking snapshot item persistence could fail with duplicate `player_id` rows inside one snapshot
- repeated PostgreSQL schema initialization could trigger deadlocks during heavy jobs
- historical monthly generation could abort if `player_event_raw_ledger` was missing

## Steps

1. Reviewed the runner CLI path, ranking snapshot persistence path and historical monthly MVP V2 path.
2. Added safe JSON serialization for manual job output.
3. Deduplicated ranking snapshot rows by `player_id` before item insertion.
4. Pre-initialized PostgreSQL snapshot storage once per heavy job and reused read/write connections without repeated DDL initialization.
5. Degraded monthly MVP V2 to a controlled empty payload when `player_event_raw_ledger` is missing instead of aborting the whole job.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `backend/app/historical_runner.py`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/historical_snapshots.py`

## Expected Files to Modify

- `backend/app/historical_runner.py`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/rcon_historical_storage.py`
- `backend/app/historical_snapshots.py`
- `backend/app/historical_storage.py`
- `backend/tests/test_historical_snapshot_refresh.py`
- `docs/public-snapshot-refresh-schedule.md`

## Constraints

- Keep public GET endpoints snapshot-only.
- No RCON host or server configuration changes.
- No Elo/MMR reactivation.
- No Comunidad Hispana #03 reintroduction.

## Validation

- `python -m compileall backend/app`
- `cd backend; python -m unittest tests.test_historical_snapshot_refresh`
- `cd backend; python -m unittest tests.test_current_match_payload tests.test_rcon_admin_log_storage tests.test_historical_snapshot_refresh`

## Outcome

- Manual public jobs now print JSON safely with datetime serialization.
- Ranking snapshot item insertion no longer tries to persist the same `player_id` twice inside one snapshot.
- Heavy scheduler jobs initialize PostgreSQL snapshot storage once and then reuse non-DDL connections for the rest of the job.
- Missing `player_event_raw_ledger` now yields a controlled empty monthly MVP V2 result instead of aborting `historical-monthly`.

## Change Budget

- This task exceeded the preferred tiny scope because the fixes crossed runner orchestration, persistence and regression tests.
