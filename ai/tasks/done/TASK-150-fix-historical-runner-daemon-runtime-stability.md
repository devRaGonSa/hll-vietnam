# TASK-150-fix-historical-runner-daemon-runtime-stability

## Goal

Fix historical runner daemon/runtime stability issues that prevent reliable automation, independently of the classic-refresh skip policy.

## Context

A separate diagnosis concluded that the main cause of frozen base history appears to be the automatic refresh skip policy. However, distinct runtime and daemon issues were also observed and must be handled separately:

1. Docker Compose runs `python -m app.historical_runner --hourly` without entering a real loop as expected.
2. The service/image/runtime has returned `no such table: historical_matches`, suggesting the daemon may point at the wrong runtime database or miss initialization.
3. Current backend full/loop paths can fail with `TypeError: Object of type datetime is not JSON serializable`.

This task must not change the refresh skip policy and must not touch Elo/MMR.

## Scope

- Correct the daemonized/automatic historical runner entrypoint and CLI mode so the service runs continuously or on the intended schedule.
- Verify Docker Compose wiring for the `historical-runner` service and align it with the current CLI contract.
- Ensure the service points at the intended runtime/database and initializes or validates required schema before use.
- Fix JSON serialization for `datetime` objects in automatic/full/loop outputs and logs.
- Preserve manual one-shot behavior while making the service path stable and observable.
- Validate in Docker with logs and database checks.

## Steps

1. Inspect the listed files first and map current manual, full, loop, and `--hourly` execution paths.
2. Inspect Docker Compose wiring for the `historical-runner` service and compare it with the current `app.historical_runner` CLI parser.
3. Reproduce or explain why `python -m app.historical_runner --hourly` does not enter the intended daemon loop.
4. Trace runtime database configuration for manual and daemonized runs, including environment variables, mounted paths, and initialization path.
5. Identify where `datetime` objects are serialized in automatic/full/loop paths and add the smallest safe JSON serialization fix.
6. Implement only daemon/runtime stability fixes, leaving skip-policy behavior unchanged.
7. Validate the service in Docker Compose with observable logs and database state.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `backend/app/historical_runner.py`
- `backend/app/config.py`
- `backend/app/historical_storage.py`
- `backend/app/postgres_utils.py`
- `docker-compose.yml`

## Candidate Files

- `backend/app/historical_runner.py`
- `backend/app/config.py`
- `backend/app/historical_storage.py`
- `backend/app/postgres_utils.py` only if schema/runtime validation belongs there
- `docker-compose.yml`
- `backend/README.md` only if the daemon runbook changes

## Expected Files to Modify

- `backend/app/historical_runner.py`
- `docker-compose.yml`
- `backend/app/config.py` only if runtime path/environment alignment requires it
- `backend/app/historical_storage.py` only if initialization validation is missing in the daemon path
- `backend/README.md` only for a narrow operational note

Rules:

- Do not modify refresh skip policy logic in this task.
- Prefer the smallest change that makes the daemon/service path executable and observable.
- If additional files become necessary, explain why in the task outcome or commit message.
- Do not modify unrelated files.

## Constraints

- Keep the task focused on runtime/daemon stability.
- Do not change policy for whether classic refresh runs after useful RCON output.
- Do not change Elo/MMR code.
- Do not change frontend files.
- Do not tune PostgreSQL globally.
- Do not redesign writer-lock behavior except for a minimal compatibility fix if the daemon cannot be validated otherwise.
- Preserve manual `run --phase ...` behavior.
- Keep output machine-readable and operator-friendly.

## Validation

Before completing the task ensure:

- Exact commands executed are documented.
- `docker compose up -d --build historical-runner` or the full required service set starts successfully.
- Docker Compose service status shows `historical-runner` is running or exits only when explicitly configured as a bounded validation command.
- Logs prove `--hourly` or its replacement enters the intended loop/daemon behavior.
- Logs no longer show `no such table: historical_matches`.
- Logs no longer show `TypeError: Object of type datetime is not JSON serializable`.
- The runner emits observable structured logs for startup, loop iteration or scheduled run, result, and errors.
- Database connectivity and required schema are verified from the same runtime context used by the service.
- Manual one-shot commands still work after the daemon fix.
- `git diff --name-only` and `git status --short` are reviewed.
- No unrelated files are modified.

Suggested validation commands include:

```bash
docker compose up -d --build postgres backend historical-runner
docker compose ps -a postgres backend historical-runner rcon-historical-worker
docker compose logs --tail=200 historical-runner
docker compose exec postgres psql -U hll_vietnam -d hll_vietnam -c "SELECT 1;"
```

## Explicit Exclusions

- Do not change classic-refresh skip policy.
- Do not implement TASK-149 in this task.
- Do not make Elo/MMR changes.
- Do not change frontend files.
- Do not tune PostgreSQL.
- Do not broadly redesign writer locking.
- Do not treat upstream CRCON availability as a daemon runtime bug unless it prevents validating service stability.

## Change Budget

- Prefer fewer than 4 modified files.
- Prefer changes under 200 lines.
- Split follow-up work if runtime stability exposes a separate schema migration, lock-coordination, or policy problem.

## Outcome

Status: completed.

Changed files:

- `backend/app/historical_runner.py`
- `docker-compose.yml`
- `backend/README.md`

Runtime fixes:

- `--hourly` now enters `loop` mode when used as the top-level shortcut instead of running one default one-shot `run --phase full` cycle.
- The Compose `historical-runner` service now uses the explicit command `python -m app.historical_runner loop --hourly`.
- Runner JSON output now uses a shared JSON fallback for `datetime` values in loop startup output, per-run loop output, progress output, and one-shot final payloads.
- The backend runbook now documents `python -m app.historical_runner loop --hourly` for daemon use.

Validation commands executed:

- `python -m py_compile app/historical_runner.py`
- `docker compose run --rm --build -e HLL_HISTORICAL_ELO_MMR_MIN_NEW_SAMPLES=999999 backend python -u -m app.historical_runner --hourly --max-runs 1 --retries 0 --max-pages 1 --page-size 1`
- `docker compose up -d --build postgres backend historical-runner`
- `docker compose ps -a postgres backend historical-runner rcon-historical-worker`
- `docker compose logs --tail=160 historical-runner`
- `docker compose logs historical-runner | Select-String -Pattern "historical-refresh-loop-started|historical-runner-phase-started|no such table|datetime is not JSON serializable|TypeError"`
- `docker compose exec -T postgres psql -U hll_vietnam -d hll_vietnam -c "SELECT COUNT(*) AS historical_matches, MIN(started_at) AS first_started_at, MAX(started_at) AS last_started_at FROM historical_matches;"`
- `docker compose exec -T postgres psql -U hll_vietnam -d hll_vietnam -c "SELECT l.pid AS postgres_pid, a.application_name, a.state, a.wait_event_type, a.wait_event, a.query_start, LEFT(REGEXP_REPLACE(COALESCE(a.query,''), '\\s+', ' ', 'g'), 240) AS query FROM pg_locks AS l LEFT JOIN pg_stat_activity AS a ON a.pid = l.pid WHERE l.locktype = 'advisory' AND l.granted = TRUE ORDER BY a.backend_start ASC NULLS LAST, l.pid ASC;"`
- `Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health -TimeoutSec 10`
- `docker compose exec -T backend python -u -m app.historical_runner run --phase snapshots --retries 0`
- `git diff --name-only`
- `git status --short`

Evidence:

- The bounded `--hourly --max-runs 1` validation emitted `historical-refresh-loop-started` and `historical-runner-phase-started` with `mode = loop`.
- The bounded validation completed with `status = ok` and printed a full JSON payload containing datetime-bearing `storage_status` and `writer_lock_metadata` fields without `TypeError: Object of type datetime is not JSON serializable`.
- `docker compose up -d --build postgres backend historical-runner` rebuilt and recreated the backend and historical-runner services successfully.
- `docker compose ps -a` showed:
  - `postgres`: up and healthy
  - `backend`: up and healthy
  - `historical-runner`: up
  - `rcon-historical-worker`: still exited from prior state and not changed by this task
- `historical-runner` logs contained `historical-refresh-loop-started` and `historical-runner-phase-started` with `mode = loop`.
- The log search returned no `no such table`, no `datetime is not JSON serializable`, and no `TypeError`.
- PostgreSQL state after validation:
  - `historical_matches = 9846`
  - first `started_at = 2024-05-17 20:20:17+00`
  - last `started_at = 2026-04-14 15:16:41+00`
- The advisory-lock query returned zero rows after the service iteration completed.
- Manual one-shot snapshots still worked after the daemon fix:
  - `status = ok`
  - `mode = manual`
  - `phase = snapshots`
  - `classic_fallback_reason = manual-phase-snapshots-only`
  - `snapshot_count = 44`

Notes:

- No refresh skip policy was changed as part of this task beyond the already-completed TASK-149 changes in the same touched file.
- The historical-runner service was left running after validation because the task required the daemon service path to be running and observable.
