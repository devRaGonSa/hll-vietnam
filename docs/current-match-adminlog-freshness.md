# Current Match AdminLog Freshness

## Problem

The public current-match page was lagging because:

- `/api/current-match/kills` reads persisted `rcon_admin_log_events`
- `/api/current-match/players` reads persisted `rcon_admin_log_events`
- those endpoints do not ingest AdminLog during the request path
- the checked-in historical worker path refreshes AdminLog on a much slower cadence
- frontend polling was already faster than backend data freshness

Observed behavior from TASK-268 matched this design:

- checked-in historical worker interval: `600` seconds
- checked-in AdminLog lookback: `10` minutes
- observed public lag growing from about `333s` to about `651s`

## Solution

Restore the existing `rcon-historical-worker` deployment to the code path that already supports lightweight current-match ingestion:

- module: `python -m app.rcon_historical_worker`
- command:

```text
python -m app.rcon_historical_worker loop --capture-mode current-live --interval 5 --retries 0 --retry-delay 0
```

- scope: only trusted current-match servers
  - `comunidad-hispana-01`
  - `comunidad-hispana-02`
- uses the same AdminLog ingestion and persistence path that already feeds `rcon_admin_log_events`
- skips heavy historical materialization on each near-live loop
- keeps the shared writer lock held only for short current-match ingestion windows

Deployment settings for the current-live worker:

- `HLL_RCON_CURRENT_MATCH_MODE=true`
- `HLL_RCON_SKIP_HISTORICAL_MATERIALIZATION=true`
- `HLL_RCON_CURRENT_MATCH_CAPTURE_INTERVAL_SECONDS=5`
- `HLL_RCON_CURRENT_MATCH_WRITER_LOCK_TIMEOUT_SECONDS=4`
- `HLL_RCON_HISTORICAL_CAPTURE_MAX_RETRIES=0`
- `HLL_RCON_HISTORICAL_CAPTURE_RETRY_DELAY_SECONDS=0`

The dedicated worker added in TASK-269 stays in the repository, but it is not the primary deployment fix and is not activated by this change.

## Design Notes

This deployment change intentionally avoids:

- changing RCON hosts, ports or passwords
- introducing a second AdminLog schema
- changing `historical-runner`
- pushing ingestion into `/api/current-match/*` request handlers
- activating `python -m app.rcon_current_match_worker` in production

Each iteration:

1. filters configured RCON targets down to trusted current-match servers
2. captures fresh live server state and recent AdminLog entries
3. persists through the existing idempotent storage path
4. skips heavy historical match materialization for the current-live loop
5. continues if one server fails

The heavy historical/snapshot path remains the responsibility of `historical-runner` on its scheduled cadence.

## Run Commands

One-shot validation using the same worker path:

```powershell
cd backend
python -m app.rcon_historical_worker capture --capture-mode current-live
```

Local near-live loop:

```powershell
cd backend
python -m app.rcon_historical_worker loop --capture-mode current-live --interval 5 --retries 0 --retry-delay 0
```

Docker/Compose-style ad hoc command:

```powershell
docker compose run --rm rcon-historical-worker python -m app.rcon_historical_worker loop --capture-mode current-live --interval 5 --retries 0 --retry-delay 0
```

Expected runtime signals after deployment:

- `capture_mode: current-live`
- `materialization_skipped: true`
- `interval_seconds: 5`
- no repeated heavy materialization every cycle

## Post-Deployment Validation

Verify the current-live worker command and env:

```bash
docker inspect -f '{{.Path}} {{json .Args}}' hll-vietnam-rcon-historical-worker-1
docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' hll-vietnam-rcon-historical-worker-1 | sort | grep -Ei 'CAPTURE|CURRENT|RCON|ADMIN|MATERIAL|INTERVAL|RETRY|LOOKBACK|LOCK'
```

Watch worker logs for:

- `capture_mode: current-live`
- `materialization_skipped: true`
- `interval_seconds: 5`
- `target_count: 2`
- `comunidad-hispana-01`
- `comunidad-hispana-02`

Confirm the worker is not doing heavy historical materialization every 5 seconds and that the writer lock is not held for long periods:

```bash
docker exec -it hll-vietnam-backend-1 sh -lc 'ls -l /app/data/hll_vietnam_dev.writer.lock || true; cat /app/data/hll_vietnam_dev.writer.lock || true'
```

Sample the public API every 10 seconds:

```powershell
$killsBase = "https://comunidadhll.devzamode.es/api/current-match/kills?server=comunidad-hispana-02&limit=18"
$playersBase = "https://comunidadhll.devzamode.es/api/current-match/players?server=comunidad-hispana-02"

1..18 | ForEach-Object {
  $now = Get-Date
  $ts = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()

  $kills = Invoke-RestMethod "$killsBase&_ts=$ts" -Headers @{ "Cache-Control" = "no-cache"; "Pragma" = "no-cache" }
  $killItems = @($kills.data.items)
  $topKill = $killItems | Select-Object -First 1

  $players = Invoke-RestMethod "$playersBase&_ts=$ts" -Headers @{ "Cache-Control" = "no-cache"; "Pragma" = "no-cache" }
  $playerItems = @($players.data.items)
  $topPlayers = $playerItems | Sort-Object -Property kills -Descending | Select-Object -First 5 | ForEach-Object {
    "$($_.player_name):K=$($_.kills):D=$($_.deaths):Team=$($_.team)"
  }

  $killLocalTime = ""
  $lagSeconds = ""
  if ($topKill -and $topKill.server_time) {
    $killDate = [DateTimeOffset]::FromUnixTimeSeconds([int64]$topKill.server_time).ToLocalTime()
    $killLocalTime = $killDate.ToString("HH:mm:ss")
    $lagSeconds = [int](([DateTimeOffset]::Now - $killDate).TotalSeconds)
  }

  [PSCustomObject]@{
    sample = $_
    sampled_at = $now.ToString("HH:mm:ss")
    kills_scope = $kills.data.scope
    kills_count = $killItems.Count
    first_id = if ($killItems.Count -gt 0) { $killItems[0].event_id } else { "" }
    first_kill_time = $killLocalTime
    estimated_lag_seconds = $lagSeconds
    first_kill = if ($topKill) { "$($topKill.killer_name)->$($topKill.victim_name):$($topKill.weapon)" } else { "" }
    players_count = $playerItems.Count
    top_players = ($topPlayers -join " | ")
  }

  Start-Sleep -Seconds 10
}
```

Expected outcome after deployment:

- new CRCON kills should appear in `/api/current-match/kills` within roughly `5-30` seconds
- `/api/current-match/players` should advance accordingly
- the frontend should reflect it without further polling changes
- `historical-runner` should remain responsible for hourly or scheduled heavy refresh work
