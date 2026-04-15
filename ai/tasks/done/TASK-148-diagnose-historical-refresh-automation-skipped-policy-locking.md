# TASK-148-diagnose-historical-refresh-automation-skipped-policy-locking

## Goal

Diagnose why the automated historical refresh cycle still leaves `refresh_result.status = skipped` while a manual `--phase refresh` run can advance `historical_matches`, and determine with real evidence whether the cause is source-selection policy, writer-lock coordination, or a combination of both.

## Context

The current working branch is `task/elo-canonical-rating-monthly`. Elo/MMR rebuild stabilization has already been handled and validated through TASK-145 and TASK-147, so this task must not introduce new `app.elo_mmr_engine` changes.

The remaining operational handoff item is historical refresh automation. The automatic cycle has been observed returning `refresh_result.status = skipped` with reasons such as `rcon-primary-cycle-no-classic-fallback-needed`, while manual execution with `python -u -m app.historical_runner run --phase refresh --retries 0` can add matches and advance `historical_matches`.

There is also documented writer-lock contention between `historical-runner --hourly` and `rcon-historical-worker`. This task must clearly separate two possible failure classes:

- policy/source selection deciding that classic refresh should be skipped;
- lock aborts or flawed daemon coordination preventing the intended refresh from running.

## Scope

- Reproduce and explain the automated refresh behavior with real Docker, SQL, and log evidence.
- Compare manual one-shot behavior against the daemonized or automation-equivalent cycle.
- Identify the policy or selector path that produces `refresh_result.status = skipped`, including `policy_mode`, `fallback_reason`, source attempts, or equivalent fields.
- Identify whether writer-lock contention contributes to skipped or aborted refresh work, and whether it affects `historical-runner --hourly`, `rcon-historical-worker`, or both.
- Determine whether `historical_matches` remains stale because classic refresh is intentionally bypassed, because the worker cannot acquire the lock, or because both issues interact.
- Document the diagnosis and only then propose the smallest follow-up implementation path if one is needed.

## Steps

1. Inspect the listed files first and map the current call chain for manual historical phases and daemonized refresh cycles.
2. Capture the current baseline in Docker: service status, backend health, PostgreSQL connectivity, current `historical_matches` count/min/max, and any active writer-lock evidence.
3. Run or reproduce the manual snapshots path:
   - `python -u -m app.historical_runner run --phase snapshots --retries 0`
4. Run or reproduce the manual refresh path:
   - `python -u -m app.historical_runner run --phase refresh --retries 0`
5. Reproduce the automatic or automation-equivalent cycle used by `historical-runner --hourly`, capturing the full structured output and backend/container logs.
6. Compare manual vs automatic outputs for `refresh_result`, `policy_mode`, `fallback_reason`, selected source, source attempts, skipped reason, lock-acquisition result, and final status.
7. Query `historical_matches` before and after each run so the diagnosis can distinguish a harmless skip from stale data.
8. Inspect lock state and relevant logs when either `historical-runner` or `rcon-historical-worker` is active, without changing lock policy as part of this task.
9. Conclude honestly whether the observed issue is policy, locking, mixed, or still unproven, and document exact evidence.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `backend/app/historical_runner.py`
- `backend/app/rcon_historical_worker.py`
- `backend/app/writer_lock.py`
- `backend/app/historical_ingestion.py`
- `backend/app/config.py`

## Candidate Files

- `backend/app/historical_runner.py`
- `backend/app/rcon_historical_worker.py`
- `backend/app/historical_ingestion.py`
- `backend/app/writer_lock.py`
- `backend/app/config.py`
- `docker-compose.yml`
- `backend/README.md` only if the diagnosis changes the operator runbook

## Expected Files to Modify

This is a diagnosis task first. Prefer modifying no source files until the evidence is complete.

If implementation is explicitly approved after diagnosis, likely files are:

- `backend/app/historical_runner.py`
- `backend/app/rcon_historical_worker.py`
- `backend/app/historical_ingestion.py` only if the policy/skip reason is emitted there
- `backend/app/writer_lock.py` only if lock evidence proves a coordination bug
- `backend/README.md` only for a narrow runbook update

Rules:

- Prefer a follow-up implementation task if the fix is broader than a narrow policy/logging change.
- If source files are changed, explain exactly why the diagnosis required implementation in the task outcome.
- Do not modify unrelated files.

## Constraints

- Keep the task focused on historical refresh automation diagnosis.
- Do not add new Elo/MMR changes.
- Do not reopen TASK-145, TASK-146, or TASK-147.
- Do not tune PostgreSQL globally.
- Do not change frontend behavior.
- Do not change source-selection policy or writer-lock behavior before the diagnosis is complete.
- Do not mask skipped refreshes by forcing successful output.
- Do not introduce new dependencies or frameworks.
- Preserve the Python backend baseline and current Docker workflow.

## Validation

Before completing the task ensure the final evidence includes:

- Exact commands executed.
- `docker version`.
- `docker compose ps -a` for at least `postgres`, `backend`, `historical-runner`, and `rcon-historical-worker`.
- `GET /health` response from the backend.
- PostgreSQL `SELECT 1`.
- `historical_matches` baseline query with count, minimum timestamp, and maximum timestamp before any run.
- Manual snapshots command output:
  - `python -u -m app.historical_runner run --phase snapshots --retries 0`
- Manual refresh command output:
  - `python -u -m app.historical_runner run --phase refresh --retries 0`
- Automatic or equivalent daemon-cycle output and logs for the current `historical-runner --hourly` behavior.
- Backend and/or `historical-runner` logs showing the real `refresh_result`, `policy_mode`, `fallback_reason`, selected source, source attempts, or equivalent fields.
- SQL query of `historical_matches` after each relevant run, including count, min timestamp, and max timestamp.
- Evidence of writer-lock state if locks appear, including holder, age, target path or database context, and which process attempted the lock.
- A final classification:
  - policy/source-selection issue;
  - writer-lock/daemon-coordination issue;
  - mixed policy plus lock issue;
  - inconclusive with explicit missing evidence.
- `git diff --name-only` and `git status --short` reviewed.
- No unrelated files modified.

Suggested SQL shape, adjusted to the actual PostgreSQL schema if column names differ:

```sql
SELECT
    COUNT(*) AS historical_matches,
    MIN(started_at) AS first_started_at,
    MAX(started_at) AS last_started_at
FROM historical_matches;
```

## Explicit Exclusions

- Do not implement new Elo/MMR logic.
- Do not modify `backend/app/elo_mmr_engine.py`.
- Do not tune PostgreSQL `max_wal_size`, checkpoint settings, memory settings, or Docker Desktop resources.
- Do not change frontend files.
- Do not implement the final solution before the diagnosis is complete.
- Do not collapse this task into TASK-145, TASK-146, or TASK-147.
- Do not remove or bypass writer locking without a separate implementation task.

## Change Budget

- Prefer zero source-code changes during diagnosis.
- If a small diagnostic instrumentation patch becomes necessary, prefer fewer than 3 modified files and fewer than 100 lines.
- Split follow-up implementation into a new task if the fix requires policy redesign, daemon scheduling changes, Docker Compose changes, or lock behavior changes.

## Outcome

Status: diagnosed. No backend source files were changed.

Classification: mixed policy plus daemon/automation configuration issue. The evidence does not prove active writer-lock contention in the reproduced runs.

### Evidence Commands Executed

- `docker version`
- `docker compose ps -a postgres backend historical-runner rcon-historical-worker`
- `Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health -TimeoutSec 10`
- `docker compose logs --tail=120 historical-runner`
- `docker compose logs --tail=120 rcon-historical-worker`
- `docker compose exec -T postgres psql -U hll_vietnam -d hll_vietnam -c "SELECT 1 AS postgres_ok;"`
- `docker compose exec -T postgres psql -U hll_vietnam -d hll_vietnam -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'historical_matches' ORDER BY ordinal_position;"`
- `docker compose exec -T postgres psql -U hll_vietnam -d hll_vietnam -c "SELECT COUNT(*) AS historical_matches, MIN(started_at) AS first_started_at, MAX(started_at) AS last_started_at FROM historical_matches;"`
- `docker compose exec -T postgres psql -U hll_vietnam -d hll_vietnam -c "SELECT l.pid AS postgres_pid, a.application_name, a.usename, a.client_addr::text AS client_addr, a.backend_start, a.state, a.wait_event_type, a.wait_event, a.query_start, LEFT(REGEXP_REPLACE(COALESCE(a.query,''), '\\s+', ' ', 'g'), 240) AS query FROM pg_locks AS l LEFT JOIN pg_stat_activity AS a ON a.pid = l.pid WHERE l.locktype = 'advisory' AND l.granted = TRUE ORDER BY a.backend_start ASC NULLS LAST, l.pid ASC;"`
- `docker compose exec -T backend python -u -m app.historical_runner run --phase snapshots --retries 0`
- `docker compose exec -T backend python -u -m app.historical_runner run --phase refresh --retries 0`
- `docker compose run --rm historical-runner python -u -m app.historical_runner --hourly`
- `docker compose exec -T backend python -u -m app.historical_runner --hourly`
- `docker compose exec -T backend python -u -m app.historical_runner loop --hourly --max-runs 1`
- `docker compose exec -T postgres psql -U hll_vietnam -d hll_vietnam -c "SELECT id, mode, target_server_slug, status, pages_processed, matches_inserted, matches_updated, notes, started_at, completed_at FROM historical_ingestion_runs ORDER BY id DESC LIMIT 8;"`
- `docker compose exec -T postgres psql -U hll_vietnam -d hll_vietnam -c "SELECT id, status, targets_seen, samples_inserted, duplicate_samples, failed_targets, started_at, completed_at, LEFT(COALESCE(notes,''), 220) AS notes FROM rcon_historical_capture_runs ORDER BY id DESC LIMIT 5;"`
- `git diff --name-only`
- `git status --short`

### Docker And Service State

- Docker client/server version: `29.3.1`.
- Docker Desktop: `4.68.0 (223695)`.
- `docker compose ps -a postgres backend historical-runner rcon-historical-worker` showed:
  - `hll-vietnam-postgres`: up and healthy.
  - `hll-vietnam-backend`: up and healthy on `0.0.0.0:8000->8000/tcp`.
  - `hll-vietnam-historical-runner`: `Exited (137) 26 hours ago`.
  - `hll-vietnam-rcon-historical-worker`: `Exited (137) 26 hours ago`.
- Backend health response:
  - `{"status": "ok", "service": "hll-vietnam-backend", "phase": "bootstrap", "live_data_source": "rcon", "historical_data_source": "rcon", "historical_runtime_policy": "rcon-first-with-public-scoreboard-fallback", "live_runtime_policy": "rcon-first-with-a2s-fallback"}`
- PostgreSQL `SELECT 1` returned `1`.
- No active PostgreSQL advisory locks were visible before the manual runs, after the manual refresh failure, or after the automation-equivalent runs.

### Baseline And Run Results

- Baseline `historical_matches` before any run:
  - count: `9840`
  - min `started_at`: `2024-05-17 20:20:17+00`
  - max `started_at`: `2026-04-12 22:03:10+00`
- After manual snapshots:
  - count: `9840`
  - min `started_at`: `2024-05-17 20:20:17+00`
  - max `started_at`: `2026-04-12 22:03:10+00`
  - expected no-op for `historical_matches`.
- Manual snapshots output:
  - `status = ok`
  - `phase = snapshots`
  - `classic_fallback_used = false`
  - `classic_fallback_reason = manual-phase-snapshots-only`
  - `refresh_result.status = skipped`
  - `refresh_result.reason = manual-phase-snapshots-only`
  - `snapshot_result.snapshot_count = 44`
  - writer lock acquired and released through PostgreSQL advisory lock.
- Manual refresh output:
  - entered `historical-ingestion-rcon-primary-started`
  - then `historical-ingestion-rcon-primary-succeeded`
  - selected classic fallback with `selected_source = public-scoreboard`
  - `fallback_used = true`
  - `fallback_reason = rcon-primary-writer-succeeded-but-classic-match-archive-still-needs-fallback`
  - inserted `4` matches for `comunidad-hispana-01`, then failed on upstream CRCON detail request `https://scoreboard.comunidadhll.es:5443/api/get_map_scoreboard?map_id=1561521 (500)`.
- After manual refresh:
  - count: `9844`
  - min `started_at`: `2024-05-17 20:20:17+00`
  - max `started_at`: `2026-04-14 14:09:58+00`
  - this proves the manual refresh path can advance `historical_matches` when it reaches the classic fallback path, even though this run ended with an upstream source error.
- Latest ingestion rows after manual refresh:
  - `id = 82`, `target_server_slug = comunidad-hispana-01`, `status = success`, `matches_inserted = 4`, `matches_updated = 12`.
  - `id = 83`, `target_server_slug = comunidad-hispana-02`, `status = failed`, `matches_inserted = 4`, `matches_updated = 12`, notes contained the CRCON `500` for `map_id=1561521`.

### Automation-Equivalent Evidence

- Running the current service image with `docker compose run --rm historical-runner python -u -m app.historical_runner --hourly` returned:
  - `status = error`
  - `attempts_used = 3`
  - `max_retries = 2`
  - `error = no such table: historical_matches`
- This indicates the stopped `historical-runner` service image/runtime is stale or pointed at a mismatched schema/storage boundary relative to the healthy backend container.
- Running the same command inside the healthy backend container with `docker compose exec -T backend python -u -m app.historical_runner --hourly` produced:
  - `mode = manual`
  - `phase = full`
  - `classic_fallback_used = false`
  - `classic_fallback_reason = rcon-primary-cycle-succeeded-without-needing-classic-fallback`
  - then crashed while printing the final payload with `TypeError: Object of type datetime is not JSON serializable`.
- Running the explicit daemon-style form with `docker compose exec -T backend python -u -m app.historical_runner loop --hourly --max-runs 1` produced:
  - `event = historical-refresh-loop-started`
  - `mode = loop`
  - `phase = full`
  - `classic_fallback_used = false`
  - `classic_fallback_reason = rcon-primary-cycle-succeeded-without-needing-classic-fallback`
  - then the same `TypeError: Object of type datetime is not JSON serializable`.
- After both automation-equivalent runs:
  - `historical_matches` remained `9844`
  - max `started_at` remained `2026-04-14 14:09:58+00`
  - no active advisory writer lock remained.
- RCON capture rows were still being inserted by the automation-equivalent runs:
  - latest capture run `id = 112`, `status = partial`, `targets_seen = 3`, `samples_inserted = 2`, `failed_targets = 1`.
  - failure note for `comunidad-hispana-03`: `auth/login`, `login_response`, `Login failed with RCON status 401: Unable to perform request. Missing authentication credentials.`

### Code Path Diagnosis

- In `backend/app/historical_runner.py`, `--hourly` only sets `args.interval = HOURLY_INTERVAL_SECONDS`; it does not switch `args.mode` to `loop`.
- `docker-compose.yml` configures `historical-runner` as:
  - `command: ["python", "-m", "app.historical_runner", "--hourly"]`
- Therefore Compose does not actually invoke the explicit loop mode. It invokes the default `run` mode with `phase = full`.
- In both `run --phase full` and `loop --hourly --max-runs 1`, once RCON capture has usable results and there is no `--server` scope and `run_number` is not on the full fallback cadence, `_resolve_classic_fallback_policy` returns no classic fallback.
- The full-cycle else branch then sets:
  - `refresh_result.status = skipped`
  - `refresh_result.reason = rcon-primary-cycle-no-classic-fallback-needed`
- That matches the observed stale `historical_matches` behavior.
- Manual `run --phase refresh` bypasses that policy by setting:
  - `classic_fallback_used = true`
  - `classic_fallback_reason = manual-phase-refresh-only`
  - `refresh_result = _run_classic_refresh(...)`
- That is why the manual refresh can advance `historical_matches` while the full/loop cycle skips classic refresh.

### Lock Diagnosis

- Writer locks were not the reproduced cause in this session.
- No active advisory locks appeared in PostgreSQL during baseline checks or after the failed/crashed runs.
- Manual phases acquired and released the PostgreSQL advisory writer lock.
- The stopped service state also means there was no live `historical-runner` or `rcon-historical-worker` daemon contending for the lock during reproduction.
- Historical runner/rcon worker logs showed prior RCON captures and skipped classic refresh, but the current run did not prove active lock contention.

### Recommended Follow-Up Implementation Path

Create a narrow implementation task to:

1. Fix the Compose command to run explicit daemon mode, likely `python -m app.historical_runner loop --hourly`.
2. Decide the intended classic fallback policy for automation when RCON capture succeeds but `historical_matches` still needs public-scoreboard catch-up. The evidence suggests the current policy is too aggressive for `historical_matches` freshness because RCON prospective samples do not replace the classic match archive.
3. Fix JSON serialization for final `historical_runner` payloads that include datetime values from RCON storage status.
4. Rebuild/recreate the `historical-runner` service image/container so it no longer fails with `no such table: historical_matches`.

Do not change `app.elo_mmr_engine` as part of that follow-up.
