---
id: TASK-270
title: Restore current-live RCON worker deployment
status: done
type: documentation
team: Backend Senior
supporting_teams: ["Arquitecto Python"]
roadmap_item: current-match
priority: high
---

# TASK-270 - Restore current-live RCON worker deployment

## Goal

Restore the existing production-good `rcon-historical-worker` deployment behavior so current-match AdminLog freshness uses the worker's supported `current-live` mode instead of the heavy historical loop.

## Context

The current GitHub/test deployment starts `rcon-historical-worker` as `python -m app.rcon_historical_worker loop`, which resolves to historical capture with heavy materialization enabled. Logs described in the task context show `capture_mode=historical`, `materialization_skipped=false`, and `interval_seconds=2`, which is the wrong runtime shape for current-match freshness.

The backend code already supports the lower-risk production-good path:

- `backend/app/rcon_historical_worker.py` supports `--capture-mode current-live`, `--interval`, `--retries`, and `--retry-delay`
- `backend/app/config.py` resolves `HLL_RCON_CURRENT_MATCH_MODE=true` or `HLL_RCON_SKIP_HISTORICAL_MATERIALIZATION=true` to `current-live`
- `current-live` always skips heavy historical materialization and uses the short current-match writer-lock timeout

Mandatory comparison result:

1. Uploaded ZIP artifact: no ZIP file matching the described production export was present in the local workspace, so an exact filesystem path inside the ZIP could not be cited directly.
2. Known-good repository reference matching the described ZIP behavior: `deploy/jta/docker-compose.yml`
3. Current repo/deployment file missing or overriding that behavior: `deploy/portainer/docker-compose.nas.yml`
4. Root `docker-compose.yml` is not the likely current Portainer stack file because it sets `container_name: hll-vietnam-rcon-historical-worker`, while the running container name provided in the request is `hll-vietnam-rcon-historical-worker-1`
5. The running container name strongly matches the Compose service `rcon-historical-worker` from a stack deployment without `container_name`, which fits `deploy/portainer/docker-compose.nas.yml`
6. `deploy/jta/docker-compose.yml` already contains the production-good `current-live` command and env pattern and serves as the checked-in known-good comparison point

## Steps

1. Compare the worker CLI/config support with the deployment compose variants in the repository.
2. Update only the deployment compose file that likely backs the current Portainer stack.
3. Keep `backend/app/rcon_current_match_worker.py` inactive in deployment.
4. Update documentation to reflect that current-match freshness should come from `rcon-historical-worker` in `current-live` mode.
5. Validate compose syntax and confirm no unrelated files changed.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/backend-senior.md`
- `backend/app/rcon_historical_worker.py`
- `backend/app/config.py`
- `deploy/portainer/docker-compose.nas.yml`
- `deploy/jta/docker-compose.yml`
- `docs/current-match-adminlog-freshness.md`
- `ai/tasks/done/TASK-269-implement-current-match-adminlog-freshness-worker.md`

## Expected Files to Modify

- `deploy/portainer/docker-compose.nas.yml`
- `docs/current-match-adminlog-freshness.md`
- `ai/tasks/done/TASK-270-restore-current-live-rcon-worker-deployment.md`

## Constraints

- Do not run `ai-platform run`.
- Do not commit or push.
- Do not touch frontend except for documentation references.
- Do not touch physical assets or `frontend/assets/img/`.
- Do not change RCON hosts, ports, passwords, `external_server_id`, `target_key`, server list, or `27001`.
- Do not change `historical-runner`.
- Do not activate `backend/app/rcon_current_match_worker.py` in this task.
- Do not reactivate Elo/MMR.
- Do not reintroduce `comunidad-hispana-03`.
- Do not touch `ai/system-metrics.md`.
- Do not include `tmp/` or unrelated pending changes.

## Validation

Before completing the task ensure:

- `python -m app.rcon_historical_worker --help`
- `docker compose -f deploy/portainer/docker-compose.nas.yml --env-file deploy/portainer/stack.env.example config`
- optional backend sanity because Python code was not changed:
  - `python -m compileall backend/app`
  - `cd backend; python -m unittest tests.test_rcon_historical_worker tests.test_current_match_payload`
- `git diff --name-only` matches the expected scope

## Outcome

What was wrong in the current deployment:

- `rcon-historical-worker` was deployed as the heavy historical loop instead of the existing lightweight `current-live` path
- this lets frequent materialization hold the shared writer lock
- it blocks `historical_runner` and also collides with the new dedicated TASK-269 worker if both are active
- deadlock risk increases under PostgreSQL because multiple writers contend around the same persisted read-model refresh path

What the known-good production behavior did correctly:

- reused `python -m app.rcon_historical_worker` instead of introducing a second always-on worker
- ran it in `current-live` mode
- skipped heavy historical materialization
- used a short interval and short writer-lock timeout to keep current-match AdminLog/read-model freshness moving

Exact service changed:

- service: `rcon-historical-worker`
- likely running container: `hll-vietnam-rcon-historical-worker-1`
- file changed: `deploy/portainer/docker-compose.nas.yml`

Exact command/env before:

- command: `python -m app.rcon_historical_worker loop`
- env:
  - `HLL_RCON_HISTORICAL_CAPTURE_INTERVAL_SECONDS=${HLL_RCON_HISTORICAL_CAPTURE_INTERVAL_SECONDS:-600}`
  - `HLL_RCON_HISTORICAL_CAPTURE_MAX_RETRIES=${HLL_RCON_HISTORICAL_CAPTURE_MAX_RETRIES:-2}`
  - `HLL_RCON_HISTORICAL_CAPTURE_RETRY_DELAY_SECONDS=${HLL_RCON_HISTORICAL_CAPTURE_RETRY_DELAY_SECONDS:-15}`
  - no `HLL_RCON_CURRENT_MATCH_MODE`
  - no `HLL_RCON_SKIP_HISTORICAL_MATERIALIZATION`
  - no `HLL_RCON_CURRENT_MATCH_CAPTURE_INTERVAL_SECONDS`
  - no `HLL_RCON_CURRENT_MATCH_WRITER_LOCK_TIMEOUT_SECONDS`

Exact command/env after:

- command: `python -m app.rcon_historical_worker loop --capture-mode current-live --interval 5 --retries 0 --retry-delay 0`
- env:
  - `HLL_RCON_HISTORICAL_CAPTURE_INTERVAL_SECONDS=5`
  - `HLL_RCON_CURRENT_MATCH_CAPTURE_INTERVAL_SECONDS=5`
  - `HLL_RCON_CURRENT_MATCH_MODE=true`
  - `HLL_RCON_SKIP_HISTORICAL_MATERIALIZATION=true`
  - `HLL_RCON_HISTORICAL_CAPTURE_MAX_RETRIES=0`
  - `HLL_RCON_HISTORICAL_CAPTURE_RETRY_DELAY_SECONDS=0`
  - `HLL_RCON_CURRENT_MATCH_WRITER_LOCK_TIMEOUT_SECONDS=4`
  - `HLL_BACKEND_RCON_ADMIN_LOG_LOOKBACK_MINUTES` left unchanged

Why this is the correct approach:

- TASK-269 added a dedicated worker, but it still competes for the same shared writer lock if the historical worker is left in heavy mode
- the known-good current production behavior already solved current-match freshness with the existing `rcon_historical_worker` `current-live` mode
- restoring that existing mode is lower-risk than adding a second permanent live worker immediately
- the bad deployment shape is `capture_mode=historical` with `materialization_skipped=false` at a near-live cadence, which is the wrong design for current-match freshness
- the correct split is:
  - current-live worker: fast interval, no heavy materialization, current-match AdminLog freshness
  - historical-runner: scheduled heavy historical refresh/snapshot work

Confirmation of protected settings:

- RCON hosts unchanged
- RCON ports unchanged
- RCON credentials unchanged
- server list unchanged
- `external_server_id` values unchanged
- `target_key` values unchanged
- `27001` unchanged
- `historical-runner` command and interval unchanged
- TASK-269 dedicated worker not activated

Post-deploy validation commands for the operator:

```bash
docker inspect -f '{{.Path}} {{json .Args}}' hll-vietnam-rcon-historical-worker-1
docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' hll-vietnam-rcon-historical-worker-1 | sort | grep -Ei 'CAPTURE|CURRENT|RCON|ADMIN|MATERIAL|INTERVAL|RETRY|LOOKBACK|LOCK'
docker logs --tail=200 hll-vietnam-rcon-historical-worker-1
docker exec -it hll-vietnam-backend-1 sh -lc 'ls -l /app/data/hll_vietnam_dev.writer.lock || true; cat /app/data/hll_vietnam_dev.writer.lock || true'
```

Expected runtime signals:

- command includes `--capture-mode current-live`
- `materialization_skipped=true`
- `interval_seconds=5`
- `retries=0`
- `retry_delay=0`
- targets remain `comunidad-hispana-01` and `comunidad-hispana-02`
- no repeated heavy materialization every 5 seconds

Current-match API freshness validation script:

```powershell
cd "D:\Proyectos\HLL Vietnam"

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

Acceptance target:

- when CRCON shows a new kill, `/api/current-match/kills` should advance in roughly `5-30` seconds
- `/api/current-match/players` should follow shortly after
- not `5-10` minutes later

Risks:

- if Portainer stack-level environment variables explicitly override the new current-live env values in a different hidden stack file, runtime may still need operator verification after redeploy
- if another untracked deployment file is actually used instead of `deploy/portainer/docker-compose.nas.yml`, the compose change here will not affect the running stack
- `hll-vietnam-backend-1` lock-file command assumes the standard container name pattern and may need adaptation if the stack/project name differs

Validation completed:

- `python -m app.rcon_historical_worker --help`
- `docker compose -f deploy/portainer/docker-compose.nas.yml --env-file deploy/portainer/stack.env.example config`
- `python -m compileall backend/app`
- `cd backend; python -m unittest tests.test_rcon_historical_worker tests.test_current_match_payload`
- No RCON host changed
- No RCON port changed
- No RCON credentials changed
- No `27001` changed
- No server list changed
- TASK-269 worker was not activated

## Change Budget

- Modified files kept to the requested minimal deployment/docs/task scope.
- No backend Python changes.
- No frontend or asset changes.
