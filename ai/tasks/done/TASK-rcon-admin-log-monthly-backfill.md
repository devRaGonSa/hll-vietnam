---
id: TASK-rcon-admin-log-monthly-backfill
title: Add RCON AdminLog historical backfill
status: in-progress
type: backend
team: Backend Senior
supporting_teams: [Arquitecto Python]
roadmap_item: historical-rcon
priority: high
---

# TASK-rcon-admin-log-monthly-backfill - Add RCON AdminLog historical backfill

## Goal

Add an explicit RCON/AdminLog backfill CLI that can populate materialized closed matches for recent-match and leaderboard windows, and align monthly RCON leaderboard snapshots with the previous-month day 1-7 policy.

## Context

HLL Vietnam runs historical data in RCON-first mode. Prospective AdminLog capture exists, but fresh databases need an operator-run backfill path to recover recent closed matches and produce reliable weekly/monthly snapshots without changing web request startup behavior.

## Steps

1. Inspect the listed files first.
2. Add the scoped backfill CLI and window policy helpers.
3. Integrate the monthly fallback policy into RCON-backed snapshots.
4. Add focused tests and documentation.
5. Validate with the documented Python checks and Docker checks where available.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `backend/README.md`
- `backend/app/rcon_admin_log_ingestion.py`
- `backend/app/rcon_admin_log_materialization.py`
- `backend/app/historical_runner.py`
- `backend/app/rcon_historical_leaderboards.py`

## Expected Files to Modify

- `backend/app/rcon_historical_backfill.py`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/config.py`
- `backend/README.md` or `docs/historical-rcon-backfill.md`
- `docker-compose.yml`
- focused tests under `backend/tests/`

## Constraints

- Do not touch unrelated UI layout or current-match live page.
- Keep normal backend startup free from long blocking backfill work.
- Keep inserts idempotent/deduplicated and do not remove existing data.
- Keep PostgreSQL compatibility and SQLite compatibility for tests.
- Do not reintroduce `comunidad-hispana-03` by default.
- Avoid public scoreboard fallback for RCON leaderboards when materialized RCON data exists.

## Validation

- `python -m compileall backend/app`
- `python -m unittest discover -s backend/tests -p "*historical*"`
- `python -m unittest discover -s backend/tests -p "*rcon*"`
- `git diff --check`
- Docker Compose build/run checks when available in the environment.

## Outcome

Implemented.

- Added `app.rcon_historical_backfill` as an explicit operator CLI.
- Added RCON monthly day 1-7 previous-month policy and weekly sufficient-sample fallback metadata.
- Routed persisted RCON leaderboard snapshot generation through the materialized RCON read model.
- Added Docker/README documentation and focused unittest coverage.
- Docker dry-run passed. A real backfill run was started after stopping writer services; the first attempt correctly reported a busy writer lock, and the second run inserted additional materialized data before the command timeout required stopping the one-off container. Advanced services were restarted afterwards.

## Change Budget

- This task is expected to exceed the default line budget because it introduces a new operator CLI plus tests and docs, but changes should remain limited to backend historical RCON surfaces.
