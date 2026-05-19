# TASK-151-fix-daemon-writer-lock-coordination

## Goal

Diagnose and correct writer-lock coordination between the `historical-runner` daemon and the `rcon-historical-worker` daemon so historical automation can coexist without spurious aborts, unclear lock conflicts, or daemon races.

## Context

The current branch is `task/elo-canonical-rating-monthly`.

Recent work already resolved and validated:

- historical refresh auto-skip policy;
- `historical-runner` runtime/daemon stability;
- Elo/MMR rebuild stabilization.

The remaining operational handoff item is daemon writer-lock coordination. Earlier reproductions showed aborts with messages such as:

- `Another backend writer is active`
- `active_holder = app.rcon_historical_worker capture:all-targets`

The latest refresh-skip diagnosis did not prove writer-lock contention as the main cause of stale `historical_matches`, but contention between `historical-runner --hourly` and `rcon-historical-worker loop` remains a separate operational risk. This task must treat the issue as coordination/locking work, not as refresh policy, Elo/MMR, frontend, or database tuning work.

## Scope

- Map how `historical-runner` and `rcon-historical-worker` currently acquire, wait for, release, and report the shared backend writer lock.
- Determine whether the two daemons should:
  1. share strict mutual exclusion for all writer work;
  2. serialize with better scheduling, wait, timeout, polling, or retry behavior;
  3. split responsibilities so RCON capture and classic historical refresh do not use an overly broad global lock when narrower coordination is safe.
- Reproduce the current behavior with both daemons active and classify whether they abort, wait, serialize, collide, or run safely.
- Implement the smallest coordination fix that removes unnecessary lock aborts while preserving data safety and deterministic writer behavior.
- Improve operational logs/messages so lock conflicts clearly identify holder, waiter, phase, target scope, lock backend, wait duration, timeout, and whether the process will retry or abort.
- Preserve the existing PostgreSQL advisory lock foundation unless evidence proves a narrow change is required.

## Steps

1. Inspect the listed files first and map current lock acquisition paths for both daemons.
2. Capture baseline Docker, backend health, PostgreSQL connectivity, service status, and current advisory-lock state.
3. Reproduce the current behavior with both `historical-runner` and `rcon-historical-worker` active.
4. Record whether each process acquires the writer lock, waits, retries, times out, aborts, or proceeds.
5. Decide whether the correct fix is stricter serialization, better retry/backoff, narrower lock scope, daemon scheduling changes, or clearer conflict handling.
6. Implement only the smallest coordination change needed for the proven failure mode.
7. Validate with both daemons active and real PostgreSQL state/log evidence.
8. Document the observed before/after behavior and any remaining operational limits.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/tasks/done/TASK-137-postgresql-concurrency-job-locking-and-operator-runbook-migration.md`
- `ai/tasks/done/TASK-148-diagnose-historical-refresh-automation-skipped-policy-locking.md`
- `ai/tasks/done/TASK-150-fix-historical-runner-daemon-runtime-stability.md`
- `backend/app/historical_runner.py`
- `backend/app/rcon_historical_worker.py`
- `backend/app/writer_lock.py`
- `backend/app/config.py`
- `docker-compose.yml`

## Candidate Files

- `backend/app/writer_lock.py`
- `backend/app/historical_runner.py`
- `backend/app/rcon_historical_worker.py`
- `backend/app/config.py`
- `docker-compose.yml`
- `backend/README.md`

## Expected Files to Modify

- `backend/app/writer_lock.py` if conflict handling, wait behavior, holder payloads, timeout behavior, or lock diagnostics need correction.
- `backend/app/historical_runner.py` only if runner daemon acquisition/retry behavior or lock-scoped logging needs adjustment.
- `backend/app/rcon_historical_worker.py` only if RCON worker acquisition/retry behavior or lock-scoped logging needs adjustment.
- `backend/app/config.py` only if existing lock timeout/polling settings need a narrow compatibility clarification or an explicit daemon coordination setting.
- `docker-compose.yml` only if daemon cadence, startup ordering, or service-level coordination needs a minimal correction.
- `backend/README.md` only for a narrow operational note if daemon lock behavior changes.

Rules:

- Prefer fewer modified files than the candidate list.
- Do not modify unrelated files.
- If a narrower lock scope is proposed, justify why it is safe for PostgreSQL writes and historical data consistency.
- If strict serialization remains the correct model, make waiting/retry behavior and logs deterministic rather than bypassing the lock.

## Constraints

- Keep the change focused on daemon writer-lock coordination.
- Do not change the historical refresh auto-skip policy.
- Do not change Elo/MMR logic, scoring, rebuild phases, or ranking materialization.
- Do not change frontend files.
- Do not tune PostgreSQL globally.
- Do not remove writer locking or bypass it to make validation pass.
- Do not mask real conflicts as success.
- Do not introduce new frameworks or dependencies.
- Preserve manual one-shot behavior for `historical_runner` and `rcon_historical_worker`.
- Preserve PostgreSQL as the primary runtime storage foundation.

## Validation

Before completing the task ensure the evidence includes:

- Exact commands executed.
- `git branch --show-current`.
- `git rev-parse HEAD`.
- `git status --short` before and after.
- `docker compose ps -a postgres backend historical-runner rcon-historical-worker`.
- Backend `/health` response.
- PostgreSQL `SELECT 1`.
- Current historical database baseline, including at least:

  ```sql
  SELECT
      COUNT(*) AS historical_matches,
      MIN(ended_at) AS first_ended_at,
      MAX(ended_at) AS last_ended_at
  FROM historical_matches;
  ```

- Active PostgreSQL advisory-lock state before, during, and after reproduction, including holder application name, state, wait event, query start, and query snippet.
- Logs from `historical-runner` and `rcon-historical-worker` showing lock acquisition, release, waiting, timeout, retry, or abort behavior.
- A controlled reproduction with both services active:

  ```powershell
  docker compose up -d --build postgres backend historical-runner rcon-historical-worker
  docker compose logs --tail=250 historical-runner
  docker compose logs --tail=250 rcon-historical-worker
  ```

- Manual or bounded commands, if needed, to force overlap without leaving unbounded jobs running:

  ```powershell
  docker compose exec -T backend python -u -m app.historical_runner loop --hourly --max-runs 1 --retries 0 --max-pages 1 --page-size 1
  docker compose exec -T backend python -u -m app.rcon_historical_worker loop --max-runs 1
  docker compose exec -T backend python -u -m app.rcon_historical_worker capture
  ```

- Before/after proof that coordination improved:
  - fewer spurious aborts;
  - deterministic wait/retry/serialize behavior;
  - clear holder/waiter logs;
  - no lock leaked after completion;
  - no data corruption or duplicate/racy writes visible in relevant run tables;
  - no broad regression in manual one-shot runner or worker commands.
- Final classification:
  - fixed;
  - partial, with explicit remaining edge cases;
  - blocked by external/runtime constraints;
  - inconclusive, with missing evidence listed.

## Explicit Exclusions

- Do not add new historical refresh auto-skip policy changes.
- Do not add new Elo/MMR changes.
- Do not change frontend files.
- Do not tune PostgreSQL server settings.
- Do not redesign the whole backend job system.
- Do not replace Docker Compose orchestration with a new scheduler.
- Do not remove the PostgreSQL advisory writer lock as a shortcut.
- Do not treat RCON authentication failures or upstream CRCON `500` responses as lock bugs unless they directly affect lock release or daemon coordination.

## Change Budget

- Prefer fewer than 4 modified files.
- Prefer changes under 200 lines when feasible.
- Split follow-up tasks if the diagnosis points to a larger job scheduler, per-resource lock hierarchy, or separate storage redesign.

## Outcome

Status: completed.

Final classification: fixed. The observed daemon behavior is strict PostgreSQL advisory-lock serialization. No evidence justified narrowing or bypassing the global writer lock. The operational defect was insufficient lock telemetry: a daemon could wait inside the polling loop with no structured log until acquisition or timeout, making healthy serialization hard to distinguish from a race or abort.

### Decision

- Keep the shared `hll-vietnam:backend-single-writer` PostgreSQL session advisory lock.
- Preserve manual preflight fail-fast behavior for one-shot commands.
- Preserve daemon wait/retry behavior.
- Add structured lock lifecycle telemetry at the shared lock layer so all writer participants report the same lock backend, scope, holder, waiter, wait duration, retry/abort action, active holder metadata and release.

### Modified Files

- `backend/app/writer_lock.py`

### Commands Executed

- `git branch --show-current`
- `git rev-parse HEAD`
- `git status --short`
- `python -m py_compile app/writer_lock.py app/historical_runner.py app/rcon_historical_worker.py app/config.py`
- `docker compose ps -a postgres backend historical-runner rcon-historical-worker`
- `Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health -TimeoutSec 10 | Select-Object -ExpandProperty Content`
- `docker compose exec -T postgres psql -U hll_vietnam -d hll_vietnam -c "SELECT 1 AS postgres_ok;"`
- `docker compose exec -T postgres psql -U hll_vietnam -d hll_vietnam -c "SELECT COUNT(*) AS historical_matches, MIN(ended_at) AS first_ended_at, MAX(ended_at) AS last_ended_at FROM historical_matches;"`
- `docker compose exec -T postgres psql -U hll_vietnam -d hll_vietnam -c "SELECT l.pid AS postgres_pid, a.application_name, a.usename, a.client_addr::text AS client_addr, a.backend_start, a.state, a.wait_event_type, a.wait_event, a.query_start, LEFT(REGEXP_REPLACE(COALESCE(a.query,''), '\\s+', ' ', 'g'), 240) AS query FROM pg_locks AS l LEFT JOIN pg_stat_activity AS a ON a.pid = l.pid WHERE l.locktype = 'advisory' AND l.granted = TRUE ORDER BY a.backend_start ASC NULLS LAST, l.pid ASC;"`
- `docker compose logs --tail=160 historical-runner`
- `docker compose logs --tail=160 rcon-historical-worker`
- `docker compose up -d --build postgres backend historical-runner rcon-historical-worker`
- `docker compose logs --tail=400 rcon-historical-worker | Select-String -Pattern 'backend-writer-lock-acquire-started','backend-writer-lock-waiting','backend-writer-lock-acquired','backend-writer-lock-released','backend-writer-lock-timed-out','Another backend writer'`
- `docker compose logs --tail=1000 historical-runner | Select-String -Pattern 'backend-writer-lock-acquire-started','backend-writer-lock-waiting','backend-writer-lock-acquired','backend-writer-lock-released','backend-writer-lock-timed-out','Another backend writer'`
- `docker compose exec -T backend python -u -m app.historical_runner loop --hourly --max-runs 1 --retries 0 --max-pages 1 --page-size 1`
- `docker compose exec -T postgres psql -U hll_vietnam -d hll_vietnam -c "SELECT id, status, targets_seen, samples_inserted, duplicate_samples, failed_targets, started_at, completed_at, LEFT(COALESCE(notes,''), 220) AS notes FROM rcon_historical_capture_runs ORDER BY id DESC LIMIT 5;"`
- `docker compose exec -T postgres psql -U hll_vietnam -d hll_vietnam -c "SELECT id, mode, target_server_slug, status, pages_processed, matches_inserted, matches_updated, notes, started_at, completed_at FROM historical_ingestion_runs ORDER BY id DESC LIMIT 8;"`
- Controlled manual conflict check with a temporary sleeping holder and `docker compose exec -e HLL_BACKEND_POSTGRES_ADVISORY_LOCK_TIMEOUT_SECONDS=2 -e HLL_BACKEND_POSTGRES_ADVISORY_LOCK_POLL_INTERVAL_SECONDS=0.5 -T backend python -u -m app.rcon_historical_worker capture`
- `git diff --name-only`
- `git status --short`

### Evidence

- Branch: `task/elo-canonical-rating-monthly`
- Commit SHA during validation: `cf419e63ee6dad0e2df1e9eac00e6a49ee280fd2`
- Backend health returned `{"status":"ok","service":"hll-vietnam-backend","phase":"bootstrap","live_data_source":"rcon","historical_data_source":"rcon","historical_runtime_policy":"rcon-first-with-public-scoreboard-fallback","live_runtime_policy":"rcon-first-with-a2s-fallback"}`.
- PostgreSQL `SELECT 1` returned `1`.
- Baseline `historical_matches`: `9851`, first `ended_at = 2024-05-17 20:48:40+00`, last `ended_at = 2026-04-14 21:36:54+00`.
- Before the patch, both daemons serialized through the advisory lock, but the waiting side did not emit a clear wait lifecycle event. PostgreSQL showed a single active holder with `application_name = app.historical_runner full:all-servers ...` and no leaked competing advisory lock.
- After the patch, `rcon-historical-worker` logs showed:
  - `backend-writer-lock-acquire-started`
  - `backend-writer-lock-waiting` with `active_holder = app.historical_runner full:all-servers ...`, `action = retry`, wait duration, timeout, poll interval, PostgreSQL backend pid, state, wait event and query snippet.
  - `backend-writer-lock-acquired` after about `10.034` seconds and `11` attempts.
  - `backend-writer-lock-released`.
- `historical-runner` logs showed `backend-writer-lock-acquire-started`, `backend-writer-lock-acquired` and `backend-writer-lock-released` for its loop run.
- The bounded `historical_runner loop --hourly --max-runs 1 --retries 0 --max-pages 1 --page-size 1` command completed successfully and emitted lock acquire/release events.
- A controlled manual conflict with a temporary sleeping holder still failed fast as intended with `status = aborted-conflict-detected-before-wait` and active holder metadata for `validation.lock-holder sleep`.
- Advisory lock state after validation returned zero rows, proving no leaked lock remained.
- Latest `rcon_historical_capture_runs` rows completed as `partial` with `samples_inserted = 2` and the known `comunidad-hispana-03` auth failure.
- Latest `historical_ingestion_runs` rows completed as `success` with bounded page processing and no duplicate/racy writer failure visible.

### Validation Results

- `py_compile`: passed.
- Docker rebuild and two-daemon startup: passed.
- Backend health: passed.
- PostgreSQL connectivity: passed.
- Advisory-lock state checks: passed, no leaked lock after runs.
- Daemon coordination: passed, observed deterministic wait/retry/serialize behavior instead of a spurious abort.
- Manual one-shot behavior: preserved; manual conflict preflight still aborts before waiting and reports the active holder.
- Changed source scope: only `backend/app/writer_lock.py`.

### Remaining Operational Limits

- Manual commands intentionally still fail fast when another writer is already active.
- The shared global writer lock remains broad by design. A future per-resource lock hierarchy should be a separate task if write domains become provably independent.
- RCON authentication failures for `comunidad-hispana-03` remain unrelated to lock coordination.
