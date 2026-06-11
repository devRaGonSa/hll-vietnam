# Public Snapshot Refresh Schedule

## Goal

Public pages should read precomputed PostgreSQL read models or persisted public snapshots. Ranking requests must not regenerate snapshots and must not query RCON directly.

## Runner Scheduling

The internal `historical-runner` owns public refresh scheduling. Host cron is not required.

Daily full refresh:

- Controlled by `HLL_PUBLIC_FULL_REFRESH_ENABLED`.
- Runs once per local day after `HLL_PUBLIC_FULL_REFRESH_TIME` in `HLL_PUBLIC_FULL_REFRESH_TIMEZONE`.
- Default: `06:00 Europe/Madrid`.
- Intended for the lowest RCON and database load window.

The daily full refresh rebuilds:

- full historical public snapshots/read models from `generate_and_persist_historical_snapshots()`;
- weekly/monthly `ranking_snapshots`;
- annual 2026 ranking snapshots for `kills`, `deaths`, `teamkills`, `matches_considered`, `kd_ratio` and `kills_per_match`;
- `player_search_index`;
- `player_period_stats`.

Frequent refreshes:

- `HLL_PUBLIC_RANKING_REFRESH_INTERVAL_SECONDS`, default `900`, refreshes weekly/monthly public ranking snapshots.
- `HLL_PUBLIC_RECENT_MATCHES_REFRESH_INTERVAL_SECONDS`, default `60`, refreshes recent-match snapshots when no direct finished-match hook fires.
- When the RCON capture cycle reports newly materialized finished matches, the runner refreshes recent-match snapshots immediately.

## Gap Found In Scheduler Audit

Current short cadence refresh only covers:

- `refresh_public_ranking_snapshots()` for `/api/ranking`
- `refresh_public_recent_matches_snapshots()` for recent matches

It does not refresh the broader historical snapshot matrix consumed by `historico.html` every hour. That means weekly/monthly historical leaderboard or summary data can remain `snapshot_status=missing` until the next daily full refresh at `06:00`, even while ranking snapshots are already updating every 15 minutes.

## Recommended Future Cadence

Target cadence identified by the audit:

- annual ranking snapshots:
  - daily at `06:00 Europe/Madrid`
- monthly ranking snapshots:
  - `07:00` and `19:00 Europe/Madrid`
- weekly ranking snapshots:
  - every hour
- historical weekly leaderboard snapshots used by `historico.html`:
  - every hour
- historical monthly leaderboard snapshots used by `historico.html`:
  - every 2 hours

Operational constraints for that future backend change:

- large ranking matrix refreshes should run sequentially
- annual/full refresh should not overlap with shorter historical refreshes
- per-job start/end/duration/scope/result logs should remain explicit
- public GET endpoints must stay snapshot-only and must not regenerate heavy data on request

Refreshes are idempotent: existing ranking snapshots are replaced for the same window/scope, player read models are rebuilt per scope, and persisted historical snapshots are replaced/upserted by snapshot identity.

## Portainer

Run the `historical-runner` service from the Compose stack with the advanced profile. The service runs:

```powershell
python -m app.historical_runner
```

Recommended Portainer environment values:

```text
HLL_PUBLIC_FULL_REFRESH_ENABLED=true
HLL_PUBLIC_FULL_REFRESH_TIME=06:00
HLL_PUBLIC_FULL_REFRESH_TIMEZONE=Europe/Madrid
HLL_PUBLIC_RANKING_REFRESH_INTERVAL_SECONDS=900
HLL_PUBLIC_RECENT_MATCHES_REFRESH_INTERVAL_SECONDS=60
```

Do not add host cron unless the internal runner cannot be used in the deployment. If a sidecar is ever required, it should call the same Python modules, not duplicate SQL logic.

## Manual Emergency Commands

One-off full runner cycle:

```powershell
docker compose exec historical-runner python -m app.historical_runner --max-runs 1
```

Weekly/monthly ranking snapshots:

```powershell
docker compose exec historical-runner python -m app.rcon_historical_leaderboards refresh-ranking-snapshots --limit 30
```

Annual ranking snapshot, one metric/scope:

```powershell
docker compose exec historical-runner python -m app.rcon_annual_rankings generate --year 2026 --metric kills --server-key all
```

Player read models:

```powershell
docker compose exec historical-runner python -m app.rcon_historical_player_stats refresh-player-search-index
docker compose exec historical-runner python -m app.rcon_historical_player_stats refresh-player-period-stats
```

Operational checks:

```powershell
docker compose ps historical-runner
docker compose logs --tail=200 historical-runner
docker compose exec backend python -m app.storage_diagnostics
```
