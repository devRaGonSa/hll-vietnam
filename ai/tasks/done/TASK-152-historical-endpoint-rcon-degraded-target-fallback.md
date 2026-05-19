# TASK-152-historical-endpoint-rcon-degraded-target-fallback

## Goal

Diagnose and implement automatic, explicit fallback to `public-scoreboard` for compatible historical endpoints when a server target has degraded or unavailable RCON, without pretending that scoreboard has exact parity for endpoints where it does not.

## Context

The `comunidad-hispana-03` RCON target has a confirmed external/runtime issue:

- TCP connection and `ServerConnect` work.
- `Login` returns `401 Unable to perform request. Missing authentication credentials.`
- The same failure was reproduced both through this application and through CRCON tooling.
- Therefore this is not considered a local RCON client bug.

The project still has useful `public-scoreboard` data for server 3. Some historical reads and snapshots already degrade correctly to `public-scoreboard`, for example the monthly kills leaderboard. Other reads still resolve through RCON or degrade inconsistently. The product should avoid blind historical views when RCON is degraded but a compatible scoreboard-backed historical source can answer honestly.

This task is not about fixing server 3 RCON credentials. It is about endpoint source selection and fallback behavior.

## Scope

- Review historical endpoint source selection and fallback policy endpoint by endpoint.
- Detect degraded RCON status per target using persisted health/capture signals such as:
  - `last_run_status`
  - `last_error`
  - `last_error_at`
  - `last_successful_capture_at`
  - target key / external server id / server slug aliases
- Treat relevant RCON failures as fallback-eligible when the endpoint has a compatible `public-scoreboard` implementation, including:
  - `auth/login`
  - `401`
  - `timeout`
  - `connection-refused`
  - equivalent connection or login-stage failures already normalized by the app
- Apply automatic fallback to `public-scoreboard` for compatible historical reads where scoreboard has valid data.
- Keep payloads honest and traceable by exposing:
  - `primary_source`
  - `selected_source`
  - `fallback_used`
  - `fallback_reason`
  - `source_attempts`
  - `accuracy_mode` or equivalent capability/accuracy metadata where applicable
- Identify endpoints that cannot degrade honestly and leave them explicitly `unsupported`, `partial`, or RCON-only with a clear reason.
- Keep fallback policy consistent and centralized enough to avoid endpoint-by-endpoint ad hoc drift.

## Endpoints To Review

Review at least:

- `GET /api/historical/snapshots/leaderboard`
- `GET /api/historical/snapshots/recent-matches`
- `GET /api/historical/snapshots/server-summary`
- `GET /api/historical/leaderboard`
- `GET /api/historical/recent-matches`
- `GET /api/historical/server-summary`
- any historical top, leaderboard, MVP, or summary read path touched by the implementation

The implementation must document which endpoints are compatible with scoreboard fallback and which are not.

## Steps

1. Inspect the listed files first and map current historical source selection for live and snapshot endpoints.
2. Query current RCON capture/storage status for all targets, especially `comunidad-hispana-03`.
3. Reproduce the current behavior for server 3 across compatible endpoints and record which ones fallback correctly and which do not.
4. Define a narrow target-health interpretation for degraded RCON states that should trigger fallback.
5. Implement the smallest shared selector/helper change that lets compatible endpoints choose `public-scoreboard` when RCON is degraded for that target.
6. Preserve RCON-first behavior when RCON is healthy and coverage is sufficient.
7. Preserve honest capability reporting for endpoints where scoreboard is only approximate, partial, or unsupported.
8. Validate with Docker, SQL, API calls, and logs.
9. Document the before/after endpoint matrix and any limits that remain.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `docs/rcon-data-capability-audit.md`
- `docs/frontend-data-consumption-plan.md`
- `backend/app/payloads.py`
- `backend/app/routes.py`
- `backend/app/historical_snapshot_storage.py`
- `backend/app/historical_storage.py`
- `backend/app/rcon_historical_storage.py`
- `backend/app/data_sources.py`

## Candidate Files

- `backend/app/payloads.py`
- `backend/app/routes.py`
- `backend/app/historical_snapshot_storage.py`
- `backend/app/historical_storage.py`
- `backend/app/rcon_historical_storage.py`
- `backend/app/data_sources.py`
- `backend/app/providers/rcon_historical_provider.py` if present or equivalent provider module
- `backend/README.md` only for a narrow runbook/source-policy note
- targeted tests or validation helpers only if the repository already has an appropriate pattern

## Expected Files to Modify

- Prefer one shared selector/policy owner plus the smallest endpoint integration changes.
- `backend/app/payloads.py` if HTTP payload source arbitration lives there.
- `backend/app/historical_snapshot_storage.py` only if snapshot metadata or stored payload fallback metadata needs correction.
- `backend/app/rcon_historical_storage.py` only if degraded target health cannot currently be queried cleanly.
- `backend/app/historical_storage.py` only if scoreboard-backed read payloads need missing source/accuracy metadata.
- `backend/README.md` only if operator behavior changes enough to need a short note.

Rules:

- Do not scatter one-off fallback rules across many endpoints if a shared helper can express the policy.
- If additional files become necessary, explain why in the task outcome.
- Do not modify unrelated files.

## Constraints

- Keep the change focused on historical endpoint source selection and fallback.
- Do not fix the RCON credential/login problem for `comunidad-hispana-03`.
- Do not add new Elo/MMR changes.
- Do not change frontend unless a minimal display adjustment is strictly required to surface already-existing fallback metadata.
- Do not tune PostgreSQL.
- Do not redesign historical ingestion or snapshot materialization.
- Do not claim exact RCON-equivalent support when `public-scoreboard` only provides partial or different semantics.
- Do not mask degraded RCON as success; make fallback visible in payload metadata.
- Preserve direct browser/static frontend compatibility if any frontend touch becomes unavoidable.

## Validation

Before completing the task ensure the evidence includes:

- Exact commands executed.
- `git branch --show-current`.
- `git rev-parse HEAD`.
- `git status --short` before and after.
- `docker compose ps -a postgres backend historical-runner rcon-historical-worker`.
- Backend `/health` response.
- PostgreSQL `SELECT 1`.
- Historical base state:

  ```sql
  SELECT
      COUNT(*) AS historical_matches,
      MIN(ended_at) AS first_ended_at,
      MAX(ended_at) AS last_ended_at
  FROM historical_matches;
  ```

- RCON target health/degradation evidence for `comunidad-hispana-03`, including the persisted status and error fields that the implementation uses:
  - `last_run_status`
  - `last_error`
  - `last_error_at`
  - `last_successful_capture_at`
  - target key / external server id
- Logs showing the real RCON failure stage, including `auth/login` or `401` for server 3.
- Before/after API comparisons for server 3 on at least:
  - one historical leaderboard/top endpoint;
  - `recent-matches` if compatible;
  - any additional endpoint changed by the implementation.
- API evidence that, when RCON for server 3 is degraded and scoreboard can answer, the response uses `public-scoreboard` and reports:
  - `primary_source`
  - `selected_source`
  - `fallback_used`
  - `fallback_reason`
  - `source_attempts`
  - `accuracy_mode` or equivalent where applicable
- API evidence that endpoints without honest scoreboard parity remain `unsupported`, `partial`, or otherwise explicitly limited rather than pretending exact support.
- Validation that healthy RCON targets still use RCON-first behavior where current policy says they should.
- `git diff --name-only`.
- `git status --short`.
- No unrelated files modified.

Suggested API probes, adjusted to actual route contracts:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/historical/snapshots/leaderboard?timeframe=monthly&metric=kills&limit=5&server=comunidad-hispana-03"
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/historical/snapshots/recent-matches?limit=5&server=comunidad-hispana-03"
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/historical/snapshots/server-summary?server=comunidad-hispana-03"
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/historical/leaderboard?timeframe=monthly&metric=kills&limit=5&server=comunidad-hispana-03"
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/historical/recent-matches?limit=5&server=comunidad-hispana-03"
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/historical/server-summary?server=comunidad-hispana-03"
```

Suggested SQL shape for RCON target status, adjusted to actual schema:

```sql
SELECT
    target_key,
    external_server_id,
    display_name,
    last_run_status,
    last_error,
    last_error_at,
    last_successful_capture_at,
    last_sample_at
FROM rcon_historical_targets
ORDER BY target_key;
```

## Explicit Exclusions

- Do not fix or rotate RCON credentials for `comunidad-hispana-03`.
- Do not change the RCON protocol client unless a small metadata classification bug is proven and required for fallback.
- Do not add new Elo/MMR changes.
- Do not change frontend except for a minimal display adjustment if required to show existing fallback metadata.
- Do not tune PostgreSQL.
- Do not redesign ingestion, daemon scheduling, writer-locking, or snapshot generation.
- Do not create fake scoreboard parity for endpoints that scoreboard cannot support honestly.
- Do not hide source degradation from API consumers.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split follow-up tasks if the endpoint matrix reveals broader source-policy redesign, new snapshot schemas, or frontend product work.

## Outcome

Status: completed.

Implemented a shared RCON historical target-health helper in `backend/app/data_sources.py`.
It reads persisted `rcon_historical_*` checkpoint status, classifies degraded
target failures for `auth/login`, `401`, timeout and connection-refused style
errors, and builds the standard historical source-policy block for compatible
`public-scoreboard` fallback.

Integrated that policy in `backend/app/payloads.py` for compatible historical
read paths:

- `/api/historical/weekly-top-kills`
- `/api/historical/leaderboard`
- `/api/historical/recent-matches`
- `/api/historical/server-summary`
- `/api/historical/monthly-mvp`
- `/api/historical/monthly-mvp-v2`
- `/api/historical/player-events`
- `/api/historical/snapshots/leaderboard`
- `/api/historical/snapshots/recent-matches`
- `/api/historical/snapshots/server-summary`

`server-summary` and `recent-matches` still use RCON first for healthy targets
because those are the only RCON historical read-model endpoints with current
coverage. Leaderboards, MVP and player-event style endpoints remain explicitly
scoreboard-backed because RCON does not have player-stat parity.

`/api/historical/snapshots/player-events` remains an explicitly limited
snapshot/public-scoreboard path with `fallback_reason =
rcon-historical-read-model-does-not-support-historical-snapshots-yet`; no fake
RCON parity was introduced.

The implementation also normalizes runtime fallback rows containing Python
`datetime` values before JSON serialization.

## Validation Evidence

Commands executed:

```powershell
git branch --show-current
git rev-parse HEAD
git status --short
python -m compileall backend\app\data_sources.py backend\app\payloads.py
powershell -ExecutionPolicy Bypass -File scripts\run-integration-tests.ps1
docker compose ps -a postgres backend historical-runner rcon-historical-worker
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/health"
docker compose exec -T postgres psql -U hll_vietnam -d hll_vietnam -c "SELECT 1;"
docker compose exec -T postgres psql -U hll_vietnam -d hll_vietnam -c "SELECT COUNT(*) AS historical_matches, MIN(ended_at) AS first_ended_at, MAX(ended_at) AS last_ended_at FROM historical_matches;"
docker compose exec -T postgres psql -U hll_vietnam -d hll_vietnam -c "SELECT targets.target_key, targets.external_server_id, targets.display_name, checkpoints.last_run_status, checkpoints.last_error, checkpoints.last_error_at, checkpoints.last_successful_capture_at, checkpoints.last_sample_at FROM rcon_historical_targets AS targets LEFT JOIN rcon_historical_checkpoints AS checkpoints ON checkpoints.target_id = targets.id ORDER BY targets.target_key;"
docker compose logs --tail=200 rcon-historical-worker
docker compose up -d --build backend
```

Repository state:

- branch: `task/elo-canonical-rating-monthly`
- HEAD: `cf419e63ee6dad0e2df1e9eac00e6a49ee280fd2`
- pre-existing dirty files were present before this task and were not reverted:
  `ai/system-metrics.md`, `backend/app/writer_lock.py`, prior task movement for
  TASK-123 and TASK-151.

Integration tests:

- `scripts/run-integration-tests.ps1` ran successfully.
- The script reports that no integration tests are configured for the current
  repository scope.

Docker and backend:

- `postgres`, `backend`, `historical-runner` and `rcon-historical-worker` were
  running.
- Backend `/health` returned:
  - `live_data_source = rcon`
  - `historical_data_source = rcon`
  - `historical_runtime_policy = rcon-first-with-public-scoreboard-fallback`
- PostgreSQL `SELECT 1` returned `1`.

Historical base state:

```text
historical_matches: 9855
first_ended_at: 2024-05-17 20:48:40+00
last_ended_at: 2026-04-15 13:59:21+00
```

RCON target status evidence:

- `comunidad-hispana-01`: `last_run_status = success`,
  `last_successful_capture_at = 2026-04-15 14:57:02.611373+00`
- `comunidad-hispana-02`: `last_run_status = success`,
  `last_successful_capture_at = 2026-04-15 14:57:02.611373+00`
- `comunidad-hispana-03`: `last_run_status = failed`,
  `last_error = [auth/login:login_response] Login failed with RCON status 401:
  Unable to perform request. Missing authentication credentials.`,
  `last_error_at = 2026-04-15 14:57:03.257304+00`,
  `last_successful_capture_at = NULL`

Worker logs showed the same server 3 failure stage:

- `error_type = auth/login`
- `error_stage = login_response`
- `message = Login failed with RCON status 401: Unable to perform request.
  Missing authentication credentials.`

After API matrix for `comunidad-hispana-03`:

| Endpoint | selected_source | fallback_used | fallback_reason | accuracy_mode | count |
| --- | --- | --- | --- | --- | --- |
| `/api/historical/snapshots/leaderboard` | `public-scoreboard` | `true` | `rcon-historical-target-degraded-auth-login` | `scoreboard-exact-player-match-stats` | 5 |
| `/api/historical/snapshots/recent-matches` | `public-scoreboard` | `true` | `rcon-historical-target-degraded-auth-login` | `scoreboard-exact-closed-match-records` | 5 |
| `/api/historical/snapshots/server-summary` | `public-scoreboard` | `true` | `rcon-historical-target-degraded-auth-login` | `scoreboard-exact-closed-match-aggregate` | 1 |
| `/api/historical/leaderboard` | `public-scoreboard` | `true` | `rcon-historical-target-degraded-auth-login` | `scoreboard-exact-player-match-stats` | 5 |
| `/api/historical/recent-matches` | `public-scoreboard` | `true` | `rcon-historical-target-degraded-auth-login` | `scoreboard-exact-closed-match-records` | 5 |
| `/api/historical/server-summary` | `public-scoreboard` | `true` | `rcon-historical-target-degraded-auth-login` | `scoreboard-exact-closed-match-aggregate` | 1 |

`source_attempts` for server 3 recent matches showed:

- RCON primary attempt with `status = degraded` and message containing
  `target_key`, `external_server_id`, `last_run_status`, `last_error`,
  `last_error_at` and `last_successful_capture_at`.
- `public-scoreboard` fallback attempt with `status = success`.

Healthy RCON target validation:

| Endpoint | server | selected_source | fallback_used | count |
| --- | --- | --- | --- | --- |
| `/api/historical/recent-matches` | `comunidad-hispana-01` | `rcon` | `false` | 5 |
| `/api/historical/server-summary` | `comunidad-hispana-01` | `rcon` | `false` | 1 |

Explicit limited endpoint validation:

| Endpoint | selected_source | fallback_used | fallback_reason | count |
| --- | --- | --- | --- | --- |
| `/api/historical/snapshots/player-events?view=teamkills` | `public-scoreboard` | `true` | `rcon-historical-read-model-does-not-support-historical-snapshots-yet` | 5 |

Before behavior was determined from code inspection and existing task context:
snapshot wrappers could label populated server 3 RCON snapshots as RCON without
checking degraded target health, while runtime summary/recent reads fell back
only after empty/error coverage rather than before source selection.
