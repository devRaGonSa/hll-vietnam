---
id: TASK-240
title: Implement ranking and historical snapshot scheduler
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto Python
roadmap_item: foundation
priority: high
---

# TASK-240 - Implement ranking and historical snapshot scheduler

## Goal

Implement the real out-of-band scheduler for ranking and historical public snapshots so `ranking.html` and `historico.html` no longer depend on the daily full refresh to populate weekly and monthly data.

## Context

The previous audit in TASK-237 documented the gap but did not change runtime behavior. The runner refreshed ranking snapshots and recent matches, but the broader historical weekly/monthly snapshot subset used by the public historical page could remain missing for hours.

## Steps

1. Reviewed scheduler, snapshot generators, config and Compose wiring.
2. Added slot-based public jobs with explicit cadence and non-overlap rules.
3. Extended docs and tests for the implemented cadence.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `backend/app/historical_runner.py`
- `backend/app/historical_snapshots.py`
- `docs/public-snapshot-refresh-schedule.md`

## Expected Files to Modify

- `backend/app/config.py`
- `backend/app/historical_runner.py`
- `backend/app/historical_snapshots.py`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/tests/test_historical_snapshot_refresh.py`
- `docker-compose.yml`
- `docs/public-snapshot-refresh-schedule.md`

## Constraints

- No public request-time regeneration.
- No RCON host, port or server configuration changes.
- No Elo/MMR reactivation.
- No Comunidad Hispana #03 reintroduction.
- Keep the scheduler simple: locks and controlled skips instead of external dependencies.

## Validation

- `python -m compileall backend/app`
- `cd backend; python -m unittest tests.test_historical_snapshot_refresh`
- `cd backend; python -m unittest tests.test_current_match_payload tests.test_rcon_admin_log_storage tests.test_historical_snapshot_refresh`
- `git diff --name-only`

## Outcome

- Implemented wall-clock public jobs for ranking weekly/monthly and historical weekly/monthly subsets.
- Added manual runner entrypoints through `python -m app.historical_runner --public-job ...`.
- Kept recent matches on the existing fast path.
- Left request contracts compatible; `generated_at` remains the last-update field used by the public historical UI.

## Change Budget

- Scope exceeded the ideal small-task budget because scheduler, snapshot generation, tests, Compose wiring and docs had to move together to avoid partial behavior.
