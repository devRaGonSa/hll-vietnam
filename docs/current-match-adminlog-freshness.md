# Current Match AdminLog Freshness

## Production Evidence

The current-match public feed was stale because the persisted AdminLog read model was coupled to slow historical materialization.

Observed production/runtime evidence:

- `hll-vietnam-rcon-historical-worker-1` was running `python -m app.rcon_historical_worker loop`
- configured capture interval was `HLL_RCON_HISTORICAL_CAPTURE_INTERVAL_SECONDS=2`
- configured retries were `HLL_RCON_HISTORICAL_CAPTURE_MAX_RETRIES=2` and `HLL_RCON_HISTORICAL_CAPTURE_RETRY_DELAY_SECONDS=1`
- configured AdminLog lookback was `HLL_BACKEND_RCON_ADMIN_LOG_LOOKBACK_MINUTES=10`
- real `rcon_historical_capture_runs` durations were around `15-30` minutes instead of `2` seconds
- recent examples included:
  - `40789`: `10:17:54 -> 10:33:45`
  - `40790`: `10:33:44 -> 10:49:38`
  - `40791`: `10:33:47 -> 11:05:20`
  - `40792`: `11:05:19 -> 11:21:15` failed with PostgreSQL deadlock
  - `40793`: `11:05:22` still running at inspection time
- each heavy cycle was also doing large historical work:
  - `player_stats_seen` around `838k`
  - `player_stats_materialized` around `838k`
  - `materialized_matches_updated` around `392-394`

This matters because:

- `/api/current-match/kills` reads `rcon_admin_log_events`
- `/api/current-match/players` reads `rcon_admin_log_events`
- those endpoints do not query RCON/CRCON directly per public request
- if the worker cycle lasts longer than the AdminLog lookback window, new live events can be delayed or missed from the current-match API perspective

The feed freshness problem was therefore primarily a backend ingestion architecture issue, not a frontend rendering issue.

## Architecture Before

Before this change, one worker path mixed three concerns:

1. lightweight live sample capture
2. AdminLog ingestion
3. heavy historical materialization of matches, player stats, rankings and search inputs

That design had two bad properties:

- current-match freshness depended on heavy historical work finishing
- the heavy path could deadlock or overlap while still starving `rcon_admin_log_events` refreshes

## Architecture After

### Live AdminLog ingestion path

- dedicated worker module: `python -m app.rcon_current_match_worker`
- scope: trusted current-match servers only
  - `comunidad-hispana-01`
  - `comunidad-hispana-02`
- cadence: explicit fast loop, intended for `5s`
- overlap safety: relies on idempotent AdminLog inserts and table uniqueness instead of the long historical writer lock
- output target: `rcon_admin_log_events`
- explicitly does not:
  - run `materialize_rcon_admin_log`
  - rebuild `rcon_match_player_stats`
  - refresh annual rankings
  - rebuild player search
  - process hundreds of thousands of historical stat rows

Operational behavior:

- worker startup initializes AdminLog storage once
- each loop iteration fetches recent AdminLog only
- each target is handled independently
- per-target results include:
  - `target_key`
  - `entries_seen`
  - `events_inserted`
  - `duplicate_events`
  - `duration_ms`
- target failures are isolated and do not stop healthy targets

### Historical materialization path

- historical worker remains `python -m app.rcon_historical_worker loop`
- it now runs on an explicit safe interval in Portainer instead of inheriting a too-fast runtime cadence
- heavy materialization stays in the historical worker
- a single-running-historical guard was added through the capture-run storage layer
- if a historical run is already active, the next historical attempt returns a skipped result with reason `already-running`

### Schema and initialization behavior

The hot live path was reduced in two places:

- current-match API reads already use `ensure_storage=False`, so public `GET /api/current-match/kills` and `GET /api/current-match/players` do not request schema initialization on each read
- the live AdminLog worker now initializes storage once at worker startup or once-mode execution, then persists with `ensure_storage=False`

This removes obvious repeated PostgreSQL DDL/init from the live ingestion loop.

## Deployment Decision

The chosen deployment split in `deploy/portainer/docker-compose.nas.yml` is:

1. add a dedicated live worker service:

```yaml
rcon-live-adminlog-worker:
  command:
    - python
    - -m
    - app.rcon_current_match_worker
    - loop
    - --interval
    - "5"
    - --lookback-minutes
    - "15"
```

2. keep the historical worker for heavy materialization, but force a safe cadence:

```yaml
rcon-historical-worker:
  command:
    - python
    - -m
    - app.rcon_historical_worker
    - loop
    - --capture-mode
    - historical
    - --interval
    - "900"
```

Rationale:

- the repository already uses the historical worker for AdminLog-backed materialization
- `historical-runner` is not a drop-in replacement for `materialize_rcon_admin_log`
- the immediate production risk was heavy materialization running effectively every few seconds
- slowing the heavy worker to `900s` while moving live ingestion to a dedicated `5s` worker cleanly separates freshness from historical backfill/materialization cost

Non-negotiable result:

- no worker should be materializing `~838k` player-stat rows every `2` seconds
- live current-match freshness no longer depends on heavy historical materialization completing first

## Current-Match API Read Path

Confirmed after this change:

- `/api/current-match/kills` reads from `rcon_admin_log_events`
- `/api/current-match/players` reads from `rcon_admin_log_events`
- those routes do not trigger `materialize_rcon_admin_log`
- those routes do not query RCON directly per public request
- those routes avoid repeated storage initialization through `ensure_storage=False`

## Validation

Code validation completed locally:

- `python -m compileall backend/app`
- `cd backend; python -m unittest tests.test_current_match_payload`
- `cd backend; python -m unittest tests.test_rcon_historical_worker`
- `cd backend; python -m unittest tests.test_rcon_current_match_worker`

Coverage added/updated for:

- live worker one-shot persistence reuse
- live worker loop `max-runs`
- live worker one-time storage initialization with `ensure_storage=False` on hot writes
- live worker per-target failure isolation
- historical worker skip when a heavy run is already active
- compose split validation for live worker presence and historical safe interval
- current-match read paths remaining read-only and not triggering materialization

## Post-Deploy Validation Commands

### 1. Verify services

```powershell
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Command}}\t{{.Status}}"
```

### 2. Verify live worker command

```powershell
docker inspect -f '{{.Path}} {{json .Args}}' hll-vietnam-rcon-live-adminlog-worker-1
```

Adapt the container name to the actual stack service name if needed.

### 3. Verify historical worker is no longer 2-second heavy materialization

```powershell
docker inspect -f '{{.Path}} {{json .Args}}' hll-vietnam-rcon-historical-worker-1

docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' hll-vietnam-rcon-historical-worker-1 | sort | grep -Ei 'CAPTURE|CURRENT|RCON|ADMIN|MATERIAL|INTERVAL|RETRY|LOOKBACK|LOCK'
```

Expected:

- no heavy materialization every `2` seconds
- historical interval should be safe if materialization remains in this service

### 4. Live worker logs

```powershell
docker logs --tail=200 hll-vietnam-rcon-live-adminlog-worker-1
```

Expected:

- short cycles
- per-target AdminLog counts
- no `player_stats_seen 838k`
- no `materialized_matches_updated` output every few seconds
- no repeated deadlocks

### 5. Historical worker/materializer logs

```powershell
docker logs --since 30m hll-vietnam-rcon-historical-worker-1 2>&1 | grep -Ei "deadlock|materialized|player_stats_seen|capture-cycle|error|exception|traceback"
```

Expected:

- no repeated deadlocks
- no overlapping heavy cycles
- no heavy cycle every `2` seconds

### 6. DB capture run sanity

```powershell
docker exec -i hll-vietnam-postgres-1 psql -U hll_vietnam -d hll_vietnam -P pager=off -c "
SELECT
  id,
  mode,
  status,
  started_at,
  completed_at,
  targets_seen,
  samples_inserted,
  duplicate_samples,
  failed_targets,
  LEFT(COALESCE(notes,''), 160) AS notes
FROM rcon_historical_capture_runs
ORDER BY id DESC
LIMIT 20;
"
```

### 7. AdminLog freshness

```powershell
docker exec -i hll-vietnam-postgres-1 psql -U hll_vietnam -d hll_vietnam -P pager=off -c "
SELECT
  target_key,
  event_type,
  COUNT(*) AS n,
  MAX(server_time) AS max_server_time,
  MAX(event_timestamp) AS max_event_timestamp,
  MAX(created_at) AS max_created_at
FROM rcon_admin_log_events
WHERE target_key IN ('comunidad-hispana-01', 'comunidad-hispana-02')
  AND created_at >= now() - interval '15 minutes'
GROUP BY target_key, event_type
ORDER BY target_key, n DESC;
"
```

### 8. API validation from Windows PowerShell

```powershell
cd "D:\Proyectos\HLL Vietnam"

$servers = @("comunidad-hispana-01", "comunidad-hispana-02")

foreach ($server in $servers) {
    $ts = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()

    $kills = Invoke-RestMethod "https://comunidadhll.devzamode.es/api/current-match/kills?server=$server&limit=20&_ts=$ts" -Headers @{
        "Cache-Control" = "no-cache"
        "Pragma" = "no-cache"
    }

    $players = Invoke-RestMethod "https://comunidadhll.devzamode.es/api/current-match/players?server=$server&_ts=$ts" -Headers @{
        "Cache-Control" = "no-cache"
        "Pragma" = "no-cache"
    }

    ""
    "===== $server ====="

    [PSCustomObject]@{
        server = $server
        kills_scope = $kills.data.scope
        kills_confidence = $kills.data.confidence
        kills_count = @($kills.data.items).Count
        kills_stale_filtered = $kills.data.stale_events_filtered
        players_scope = $players.data.scope
        players_confidence = $players.data.confidence
        players_count = @($players.data.items).Count
        players_updated_at = $players.data.updated_at
    }

    "Latest kills:"
    $kills.data.items | Select-Object -First 10 event_id,server_time,event_timestamp,killer_name,killer_team,victim_name,victim_team,weapon

    "Top players:"
    $players.data.items | Sort-Object kills -Descending | Select-Object -First 10 player_name,team,kills,deaths,teamkills,deaths_by_teamkill,most_used_weapon
}
```

Expected acceptance after redeploy:

- new CRCON kills should reach `rcon_admin_log_events` within roughly `5-30` seconds under normal conditions
- `/api/current-match/kills` should reflect them shortly after
- `/api/current-match/players` should also advance shortly after
- no worker should materialize `838k` player stats every few seconds
- repeated PostgreSQL deadlocks should stop

## Known Remaining Issue

`TEAM KILL` AdminLog parsing was left as follow-up work in this task.

Known behavior:

- parser currently recognizes `KILL:` but not the separate `TEAM KILL` label in some lines
- those lines can still land as `event_type="unknown"`
- that means some teamkills may remain absent from current-match feed/stats until a follow-up parser fix lands

This was intentionally not expanded into the central scope of the ingestion/materialization split.

## Risks And Rollback

Primary residual risks:

- a stale historical `running` row can cause later heavy cycles to skip until an operator clears the stale state
- if production has multiple unexpected worker replicas, logs should be reviewed after redeploy to confirm the split behaves as intended
- live freshness still depends on RCON AdminLog availability per target

Rollback path:

1. stop the dedicated `rcon-live-adminlog-worker`
2. restore the previous historical worker command/env in Portainer if required
3. redeploy the stack

Rollback should only be used if the new live worker introduces unexpected operational issues, because the previous combined design is known to starve current-match freshness under heavy materialization load.
