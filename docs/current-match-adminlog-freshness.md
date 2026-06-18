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

Add a dedicated lightweight worker:

- module: `python -m app.rcon_current_match_worker`
- scope: only trusted current-match servers
  - `comunidad-hispana-01`
  - `comunidad-hispana-02`
- fetches recent AdminLog directly from existing configured RCON targets
- reuses existing parsing and `persist_rcon_admin_log_entries(...)`
- writes into the same `rcon_admin_log_events` table
- relies on existing dedupe/idempotency for overlap-safe windows

Default worker settings:

- `CURRENT_MATCH_ADMINLOG_INTERVAL_SECONDS=10`
- `CURRENT_MATCH_ADMINLOG_LOOKBACK_SECONDS=180`
- `CURRENT_MATCH_ADMINLOG_ENABLED=false`

The worker is opt-in. This task does not change Compose to start it automatically.

## Design Notes

The worker intentionally avoids:

- changing RCON hosts, ports or passwords
- introducing a second AdminLog schema
- reducing the heavy historical worker interval globally
- pushing ingestion into `/api/current-match/*` request handlers

Each iteration:

1. filters configured RCON targets down to trusted current-match servers
2. fetches recent AdminLog entries with a small overlap window
3. persists through the existing idempotent storage path
4. logs per-target counts for:
   - `entries_seen`
   - `events_inserted`
   - `duplicate_events`
   - `duration_ms`
5. continues if one server fails

## Run Commands

Local one-shot validation:

```powershell
cd backend
python -m app.rcon_current_match_worker once
```

Local loop:

```powershell
cd backend
python -m app.rcon_current_match_worker loop --interval 10 --lookback-seconds 180
```

Docker/Compose-style ad hoc command without changing deployment defaults:

```powershell
docker compose run --rm backend python -m app.rcon_current_match_worker loop --interval 10 --lookback-seconds 180
```

Example service snippet for a future approved deployment:

```yaml
current-match-adminlog-worker:
  profiles: ["advanced"]
  build:
    context: ./backend
  command: ["python", "-m", "app.rcon_current_match_worker", "loop"]
  environment:
    HLL_BACKEND_DATABASE_URL: ${HLL_BACKEND_DATABASE_URL}
    HLL_BACKEND_RCON_TARGETS: ${HLL_BACKEND_RCON_TARGETS}
    CURRENT_MATCH_ADMINLOG_ENABLED: ${CURRENT_MATCH_ADMINLOG_ENABLED:-false}
    CURRENT_MATCH_ADMINLOG_INTERVAL_SECONDS: ${CURRENT_MATCH_ADMINLOG_INTERVAL_SECONDS:-10}
    CURRENT_MATCH_ADMINLOG_LOOKBACK_SECONDS: ${CURRENT_MATCH_ADMINLOG_LOOKBACK_SECONDS:-180}
```

The snippet is documented only. It is not applied automatically by this task.

## Post-Deployment Validation

Watch worker logs for per-target counts and errors. The useful signals are:

- `entries_seen`
- `events_inserted`
- `duplicate_events`
- `target_key`
- `duration_ms`

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

- new CRCON kills should appear in `/api/current-match/kills` within roughly `10-30` seconds
- `/api/current-match/players` should advance accordingly
- the frontend should reflect it without further polling changes
