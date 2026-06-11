# Public Snapshot Refresh Schedule

## Goal

Public pages must read persisted snapshots and read models only. No public GET endpoint should regenerate ranking or historical snapshots at request time.

## Current Scheduler Owner

The internal `historical-runner` owns public refresh scheduling. Host cron is not required.

## Implemented Cadence

Local timezone for scheduled jobs: `Europe/Madrid`.

Heavy daily window:

- full public refresh:
  - `06:00`
  - rebuilds full historical snapshots, weekly/monthly ranking snapshots, annual ranking snapshots, player search index and player period stats
  - runs under `public-full-refresh`

Ranking page:

- annual ranking:
  - rebuilt inside the daily full refresh at `06:00`
  - generated sequentially per scope and metric
- monthly ranking:
  - `07:00` and `19:00`
  - generated sequentially per scope and metric
  - runs under `public-ranking-monthly-refresh`
- weekly ranking:
  - every hour at minute `10`
  - generated sequentially per scope and metric
  - runs under `public-ranking-weekly-refresh`

Historical page:

- weekly historical leaderboard subset:
  - every hour at minute `25`
  - scopes:
    - `all-servers`
    - `comunidad-hispana-01`
    - `comunidad-hispana-02`
  - metrics:
    - `kills`
    - `deaths`
    - `matches_over_100_kills`
    - `support`
  - runs under `public-historical-weekly-refresh`
- monthly historical UI subset:
  - every `2` hours at minute `40`
  - same scopes as weekly historical
  - leaderboard metrics:
    - `kills`
    - `deaths`
    - `matches_over_100_kills`
    - `support`
  - also refreshes:
    - `monthly-mvp`
    - `monthly-mvp-v2`
  - runs under `public-historical-monthly-refresh`

Recent matches:

- interval polling fallback remains enabled through `HLL_PUBLIC_RECENT_MATCHES_REFRESH_INTERVAL_SECONDS`
- default: `60` seconds
- immediate refresh still happens when the RCON capture loop materializes a finished match

## Why Historical Weekly And Monthly Were Missing

The previous short cadence only refreshed:

- `ranking_snapshots` for `/api/ranking`
- `recent-matches` snapshots

It did not refresh the broader historical snapshot subset consumed by `historico.html`. That left weekly and monthly historical leaderboard payloads in `snapshot_status=missing` until the next daily full refresh.

## Locking And Overlap Policy

The scheduler uses in-process locks and controlled skips. It does not enqueue backlog jobs.

Heavy jobs:

- `public-full-refresh`
- `public-ranking-annual-refresh`
- `public-ranking-monthly-refresh`

Policy:

- heavy jobs do not overlap with other heavy jobs
- hourly and bi-hourly jobs skip when a conflicting heavy job is in progress
- if a heavy job already ran in the same scheduler tick, lower-priority jobs skip and retry on the next tick
- weekly and monthly historical subset jobs also avoid overlapping with each other

This keeps the implementation simple and avoids CPU spikes without reintroducing request-time fallback work.

## Manual Job Hardening

Manual public jobs executed with `python -m app.historical_runner --public-job ...` now follow the same storage and error-handling rules as scheduled runs:

- CLI JSON output serializes `datetime` and `date` values safely
- ranking snapshot rows are deduplicated by `player_id` before inserting `ranking_snapshot_items`
- PostgreSQL snapshot storage initialization runs once at the start of the heavy job, then substeps reuse non-DDL connections
- missing `player_event_raw_ledger` no longer aborts `historical-monthly`; the monthly MVP V2 slice degrades to an empty payload with `event_coverage.ready = false`

This keeps manual validation commands useful without hiding partial failures inside the job payload.

## Last Update Exposure

Historical and ranking payloads continue to expose persisted generation metadata from the snapshot records:

- `snapshot_status`
- `generated_at`
- `source_range_start`
- `source_range_end`
- `is_stale`

`historico.js` already renders `generated_at` as the visible "Actualizado" label, so no frontend contract change was required for this task.

## Environment Variables

Existing variables kept:

- `HLL_PUBLIC_FULL_REFRESH_ENABLED`
- `HLL_PUBLIC_FULL_REFRESH_TIME`
- `HLL_PUBLIC_FULL_REFRESH_TIMEZONE`
- `HLL_PUBLIC_RECENT_MATCHES_REFRESH_INTERVAL_SECONDS`

Retained for compatibility:

- `HLL_PUBLIC_RANKING_REFRESH_INTERVAL_SECONDS`
  - no longer drives the hourly/slot-based ranking scheduler
  - still participates in runner tick resolution and legacy compatibility paths

New scheduler variables:

- `HLL_PUBLIC_RANKING_WEEKLY_REFRESH_MINUTE`
  - default `10`
- `HLL_PUBLIC_RANKING_MONTHLY_REFRESH_TIMES`
  - default `07:00,19:00`
- `HLL_PUBLIC_HISTORICAL_WEEKLY_REFRESH_MINUTE`
  - default `25`
- `HLL_PUBLIC_HISTORICAL_MONTHLY_REFRESH_MINUTE`
  - default `40`
- `HLL_PUBLIC_HISTORICAL_MONTHLY_REFRESH_HOUR_INTERVAL`
  - default `2`

## Manual Validation Commands

One-off public jobs through the runner:

```powershell
docker compose exec historical-runner python -m app.historical_runner --public-job ranking-weekly
docker compose exec historical-runner python -m app.historical_runner --public-job ranking-monthly
docker compose exec historical-runner python -m app.historical_runner --public-job historical-weekly
docker compose exec historical-runner python -m app.historical_runner --public-job historical-monthly
docker compose exec historical-runner python -m app.historical_runner --public-job public-full
```

Direct ranking matrix commands:

```powershell
docker compose exec historical-runner python -m app.rcon_historical_leaderboards refresh-ranking-snapshots --timeframe weekly --limit 30
docker compose exec historical-runner python -m app.rcon_historical_leaderboards refresh-ranking-snapshots --timeframe monthly --limit 30
```

Operational checks:

```powershell
docker logs --tail=300 hll-vietnam-historical-runner-1
docker exec hll-vietnam-historical-runner-1 sh -lc 'env | sort | grep HLL_PUBLIC'
python .\scripts\audit_public_requests.py --base-url https://comunidadhll.devzamode.es --timeout 30 --filter servers --output tmp\task240_servers_after.json
python .\scripts\audit_public_requests.py --base-url https://comunidadhll.devzamode.es --timeout 30 --output tmp\task240_full_audit_after.json
```

UI checks:

- verify `historico.html` weekly rankings render without `snapshot_status=missing`
- verify `historico.html` monthly rankings render without `snapshot_status=missing`
- verify the visible "Actualizado" label changes after the corresponding runner job
