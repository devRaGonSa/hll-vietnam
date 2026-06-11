---
id: TASK-237
title: Review and fix ranking historical snapshot schedules
status: done
type: documentation
team: Analista
supporting_teams:
  - Backend Senior
roadmap_item: foundation
priority: medium
---

# TASK-237 - Review and fix ranking historical snapshot schedules

## Goal

Audit the current ranking and historical snapshot scheduler, identify why weekly/monthly historical data can remain missing, and document the exact backend work required to fix it.

## Context

The requested functional fix lives in `backend/app/historical_runner.py`, `backend/app/config.py` and the ranking snapshot generators. In this run the repository was under an explicit user restriction of not touching backend code, so the task was completed as a scheduler audit plus implementation plan only.

## Files Read First

- `backend/app/historical_runner.py`
- `backend/app/config.py`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/tests/test_historical_snapshot_refresh.py`
- `docker-compose.yml`
- `docs/public-snapshot-refresh-schedule.md`

## Current Scheduler Found

- Daily public full refresh:
  - `HLL_PUBLIC_FULL_REFRESH_ENABLED=true`
  - `HLL_PUBLIC_FULL_REFRESH_TIME=06:00`
  - `HLL_PUBLIC_FULL_REFRESH_TIMEZONE=Europe/Madrid`
- Short cadence ranking refresh:
  - `HLL_PUBLIC_RANKING_REFRESH_INTERVAL_SECONDS=900`
- Short cadence recent matches refresh:
  - `HLL_PUBLIC_RECENT_MATCHES_REFRESH_INTERVAL_SECONDS=60`

Current runner behavior:

1. `refresh_public_full_read_models()` runs full historical snapshots, ranking snapshots, annual ranking snapshots, player search index and player period stats once per day.
2. `refresh_public_ranking_snapshots()` refreshes only weekly/monthly `ranking_snapshots` every 900 seconds.
3. `refresh_public_recent_matches_snapshots()` refreshes recent matches every 60 seconds.

## Why Weekly/Monthly Historical Data Can Still Be Missing

The historical UI does not only depend on `ranking_snapshots`.

- `frontend/historico.html` reads:
  - `/api/historical/snapshots/server-summary`
  - `/api/historical/snapshots/leaderboard`
  - `/api/historical/snapshots/recent-matches`
- The short cadence runner refresh only covers:
  - ranking snapshots for `/api/ranking`
  - recent matches snapshots
- It does not refresh the full `generate_and_persist_historical_snapshots()` matrix every hour.

That leaves this gap:

1. Weekly/monthly ranking snapshots for `ranking.html` may be fresh.
2. Historical summary/leaderboard snapshots consumed by `historico.html` may remain missing until the next daily 06:00 full refresh.
3. If the runner service is not actually running, nothing refreshes at all regardless of configured cadence.

## Backend Work Required To Fix It

Required implementation, not applied in this run:

1. Add separate hourly historical leaderboard refresh cadence for the snapshot matrix used by `historico.html`.
2. Add separate every-2-hours monthly historical snapshot cadence.
3. Split public refreshes by workload class:
   - annual ranking: daily at 06:00
   - monthly ranking snapshots: 07:00 and 19:00
   - weekly ranking snapshots: hourly
   - historical weekly snapshots: hourly
   - historical monthly snapshots: every 2 hours
4. Introduce per-refresh-type locks so annual/full jobs do not overlap with shorter historical jobs.
5. Keep large ranking snapshot combinations sequential.
6. Permit lighter historical snapshot groups in parallel only if they stay outside the shared writer critical section.
7. Add explicit start/end/duration/scope/result logs for each scheduler job.

## Final Recommended Cadences

- Ranking annual:
  - daily at `06:00 Europe/Madrid`
- Ranking monthly:
  - `07:00` and `19:00 Europe/Madrid`
- Ranking weekly:
  - every hour
- Historical leaderboards weekly:
  - every hour
- Historical leaderboards monthly:
  - every 2 hours
- Recent matches:
  - keep event-driven refresh plus short polling fallback

## Sequential vs Parallel

Sequential:

- annual ranking snapshot matrix
- full ranking weekly/monthly matrix if still generated as one bulk writer job
- any refresh that writes through the shared backend writer lock

Potentially parallel after backend refactor:

- independent historical snapshot groups that do not share the same writer section
- read-only validations and status probes

## Validation

- Reviewed `backend/app/historical_runner.py`
- Reviewed `backend/app/config.py`
- Reviewed `backend/app/rcon_historical_leaderboards.py`
- Reviewed `backend/tests/test_historical_snapshot_refresh.py`
- Reviewed `docker-compose.yml`
- Updated `docs/public-snapshot-refresh-schedule.md`

## Post-Deploy Validation Commands

```powershell
docker compose ps historical-runner
docker compose logs --tail=200 historical-runner
docker compose exec historical-runner python -m app.historical_runner --max-runs 1
docker compose exec historical-runner python -m app.rcon_historical_leaderboards refresh-ranking-snapshots --limit 30
Invoke-RestMethod "http://127.0.0.1:8000/api/historical/snapshots/leaderboard?server=all-servers&timeframe=weekly&metric=kills&limit=10" | ConvertTo-Json -Depth 10
Invoke-RestMethod "http://127.0.0.1:8000/api/historical/snapshots/leaderboard?server=all-servers&timeframe=monthly&metric=kills&limit=10" | ConvertTo-Json -Depth 10
Invoke-RestMethod "http://127.0.0.1:8000/api/ranking?timeframe=weekly&server_id=all&metric=kills&limit=20" | ConvertTo-Json -Depth 10
Invoke-RestMethod "http://127.0.0.1:8000/api/ranking?timeframe=monthly&server_id=all&metric=kills&limit=20" | ConvertTo-Json -Depth 10
```

## Outcome

The scheduler audit is complete, the likely root cause is documented, and the exact backend changes are scoped. No backend implementation was applied in this run because the current instruction set explicitly forbids backend edits.
