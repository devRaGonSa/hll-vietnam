# Historical RCON AdminLog Backfill

The RCON/AdminLog backfill is an explicit operator command. It does not run on
backend startup or on web requests.

Run it through the advanced worker image:

```powershell
docker compose run --rm rcon-historical-worker python -m app.rcon_historical_backfill --ensure-recent-matches 100 --servers comunidad-hispana-01,comunidad-hispana-02 --dry-run
```

Before a real manual backfill, stop the writer services to avoid waiting on the
shared writer lock:

```powershell
docker compose --profile advanced stop historical-runner rcon-historical-worker
```

Restart them afterwards:

```powershell
docker compose --profile advanced up -d historical-runner rcon-historical-worker
```

Examples:

```powershell
docker compose run --rm rcon-historical-worker python -m app.rcon_historical_backfill --ensure-recent-matches 100 --servers comunidad-hispana-01,comunidad-hispana-02
docker compose run --rm rcon-historical-worker python -m app.rcon_historical_backfill --ensure-current-month --servers comunidad-hispana-01,comunidad-hispana-02
docker compose run --rm rcon-historical-worker python -m app.rcon_historical_backfill --ensure-leaderboard-windows --servers comunidad-hispana-01,comunidad-hispana-02
docker compose run --rm rcon-historical-worker python -m app.rcon_historical_backfill --ensure-recent-matches 100 --servers comunidad-hispana-01,comunidad-hispana-02 --chunk-hours 6 --sleep-seconds 1 --max-days-back 45 --regenerate-snapshots
```

Direct module examples:

```powershell
python -m app.rcon_historical_backfill --from 2026-05-01 --to now --servers comunidad-hispana-01,comunidad-hispana-02
python -m app.rcon_historical_backfill --ensure-recent-matches 100 --servers comunidad-hispana-01,comunidad-hispana-02
python -m app.rcon_historical_backfill --ensure-current-month --servers comunidad-hispana-01,comunidad-hispana-02
python -m app.rcon_historical_backfill --ensure-leaderboard-windows --servers comunidad-hispana-01,comunidad-hispana-02
```

Useful configuration:

- `HLL_RCON_BACKFILL_CHUNK_HOURS`, default `6`
- `HLL_RCON_BACKFILL_SLEEP_SECONDS`, default `1`
- `HLL_RCON_BACKFILL_MAX_DAYS_BACK`, default `45`
- `HLL_BACKEND_RCON_ADMIN_LOG_LOOKBACK_MINUTES`, for normal prospective worker capture only

The command only selects `comunidad-hispana-01` and `comunidad-hispana-02` by
default. `comunidad-hispana-03` is not included unless it is configured in
`HLL_BACKEND_RCON_TARGETS` and explicitly passed with `--servers`.

Monthly RCON leaderboards use the previous calendar month on days 1 through 7.
From day 8 onward they use the current calendar month. Weekly RCON leaderboards
use the current week only when the current week has enough closed materialized
matches; otherwise they fall back to the previous week.
