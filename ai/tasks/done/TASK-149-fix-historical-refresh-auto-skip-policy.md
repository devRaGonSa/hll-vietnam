# TASK-149-fix-historical-refresh-auto-skip-policy

## Goal

Correct the historical refresh automatic/full-cycle policy so useful RCON output is not treated as equivalent to a complete and current base historical dataset, and so the automatic flow advances `historical_matches` in the same relevant cases where manual `run --phase refresh --retries 0` advances it.

## Context

Verified behavior shows that manual refresh:

```bash
python -u -m app.historical_runner run --phase refresh --retries 0
```

entered the classic public-scoreboard fallback path and advanced `historical_matches` from `9840` to `9844`. The run later failed because of an upstream CRCON `500`, but the partial progress was persisted.

The automatic/full-cycle flow skipped the classic refresh when RCON produced "usable" data, leaving `historical_matches` frozen at `9844`. Current reproductions did not prove active writer-lock contention as the cause of that skip. This task must focus on the decision policy that produces `refresh_result=skipped`, not daemon/runtime fixes and not Elo/MMR.

## Scope

- Review the automatic/full-cycle policy that decides whether classic historical refresh is skipped.
- Distinguish "RCON produced useful data" from "base historical data is complete and current".
- Define minimum conditions where classic refresh must still run even if RCON capture produced partial or useful data.
- Preserve RCON-first behavior without starving the base historical dataset.
- Keep the change focused on policy/selection and observable result fields such as `refresh_result`, `policy_mode`, `fallback_reason`, selected source, and source attempts.
- Validate against real Docker/PostgreSQL data with before/after `historical_matches` evidence.

## Steps

1. Inspect the listed files first and map the automatic/full-cycle path from RCON capture through classic refresh skip/fallback decisions.
2. Identify the exact condition that emits skipped reasons such as `rcon-primary-cycle-no-classic-fallback-needed`.
3. Compare that condition with manual `run --phase refresh --retries 0`, especially why manual refresh can add rows when automatic/full-cycle skips.
4. Implement the smallest policy correction so RCON usefulness does not suppress classic refresh when base historical coverage can still advance.
5. Keep policy outputs explicit: preserve or improve `refresh_result`, `policy_mode`, `fallback_reason`, selected source, and source-attempt evidence.
6. Validate by comparing automatic/full-cycle and manual refresh behavior before and after the fix.
7. Document whether any upstream CRCON failure still allows partial persisted progress and how the automatic result reports that state.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/tasks/done/TASK-148-diagnose-historical-refresh-automation-skipped-policy-locking.md`
- `backend/app/historical_runner.py`
- `backend/app/historical_ingestion.py`
- `backend/app/config.py`

## Candidate Files

- `backend/app/historical_runner.py`
- `backend/app/historical_ingestion.py`
- `backend/app/config.py`
- `backend/README.md` only if the operator policy/runbook needs a narrow clarification

## Expected Files to Modify

- `backend/app/historical_runner.py`
- `backend/app/historical_ingestion.py` only if the skip/fallback decision or result payload is owned there
- `backend/app/config.py` only if an existing policy flag must be clarified or reused
- `backend/README.md` only for a short operator note if behavior changes

Rules:

- Prefer modifying only the policy owner file.
- Do not modify daemon/runtime wiring unless it is strictly necessary to exercise the policy path.
- If additional files become necessary, explain why in the task outcome or commit message.
- Do not modify unrelated files.

## Constraints

- Keep the change minimal.
- Preserve RCON-first historical orchestration, but do not let RCON partial usefulness imply complete classic historical coverage.
- Do not implement writer-lock fixes in this task unless a minimal adjustment is indispensable for validating the policy path.
- Do not fix `--hourly` or daemon runtime behavior here.
- Do not fix `datetime is not JSON serializable` here.
- Do not fix `no such table: historical_matches` here.
- Do not add new Elo/MMR changes.
- Do not touch frontend files.
- Do not tune PostgreSQL or Docker.
- Do not mask upstream CRCON failures as full success.

## Validation

Before completing the task ensure:

- Exact commands executed are documented.
- Docker/PostgreSQL baseline is captured.
- `historical_matches` is queried before and after each relevant run with count, min timestamp, and max timestamp.
- The manual path is captured for comparison:
  - `python -u -m app.historical_runner run --phase refresh --retries 0`
- The automatic/full-cycle path, or the closest equivalent path used by automation, is reproduced after the fix.
- Logs or structured output show the real `refresh_result`, `policy_mode`, `fallback_reason`, selected source, source attempts, and any skipped reason.
- The fixed automatic/full-cycle path no longer leaves `historical_matches` frozen in a case where manual refresh can advance it.
- If upstream CRCON returns `500`, the result clearly distinguishes partial persisted progress from terminal upstream failure.
- `git diff --name-only` and `git status --short` are reviewed.
- No unrelated files are modified.

Suggested SQL shape, adjusted to actual schema names if needed:

```sql
SELECT
    COUNT(*) AS historical_matches,
    MIN(started_at) AS first_started_at,
    MAX(started_at) AS last_started_at
FROM historical_matches;
```

## Explicit Exclusions

- Do not fix writer-lock coordination except for the smallest validation unblocker if absolutely required.
- Do not fix `historical-runner --hourly`.
- Do not fix Docker Compose daemon wiring.
- Do not fix `datetime is not JSON serializable`.
- Do not fix `no such table: historical_matches`.
- Do not change Elo/MMR code.
- Do not change frontend files.
- Do not tune PostgreSQL.

## Change Budget

- Prefer fewer than 3 modified files.
- Prefer changes under 150 lines.
- Split follow-up work if the policy fix exposes daemon/runtime or lock bugs outside this task.

## Outcome

Status: completed.

Changed `backend/app/historical_runner.py` only.

Implemented a runner-level base historical coverage policy before the automatic/full-cycle skip decision. RCON capture still runs first, but useful RCON output no longer suppresses classic public-scoreboard refresh when the persisted `historical_matches` archive is missing, unreadable, has an unknown latest match timestamp, or has a server whose latest persisted match is older than `HLL_HISTORICAL_REFRESH_OVERLAP_HOURS`. The previous cadence fallback remains in place for cases where base coverage is already fresh.

Added an observable runner event:

- `historical-runner-classic-fallback-policy-resolved`

It reports:

- `classic_fallback_used`
- `classic_fallback_reason`
- `rcon_capture_status`

Validation commands executed:

- `python -m py_compile app/historical_runner.py`
- `docker version`
- `docker compose ps -a postgres backend historical-runner rcon-historical-worker`
- `Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health -TimeoutSec 10`
- `docker compose exec -T postgres psql -U hll_vietnam -d hll_vietnam -c "SELECT 1 AS postgres_ok;"`
- `docker compose exec -T postgres psql -U hll_vietnam -d hll_vietnam -c "SELECT COUNT(*) AS historical_matches, MIN(started_at) AS first_started_at, MAX(started_at) AS last_started_at FROM historical_matches;"`
- `docker compose run --rm --build backend python -u -m app.historical_runner run --phase full --retries 0`
- `docker compose run --rm --build backend python -u -m app.historical_runner loop --hourly --max-runs 1 --retries 0`
- `docker compose run --rm --build backend python -u -m app.historical_runner run --phase refresh --retries 0`
- `docker compose run --rm --build backend python -u -m app.historical_runner loop --hourly --max-runs 1 --retries 0 --max-pages 1 --page-size 1`
- `docker logs --tail 200 hllvietnam-backend-run-1046e2b39008`
- `docker stop hllvietnam-backend-run-1046e2b39008`
- `docker compose exec -T postgres psql -U hll_vietnam -d hll_vietnam -c "SELECT l.pid AS postgres_pid, a.application_name, a.state, a.wait_event_type, a.wait_event, a.query_start, LEFT(REGEXP_REPLACE(COALESCE(a.query,''), '\\s+', ' ', 'g'), 240) AS query FROM pg_locks AS l LEFT JOIN pg_stat_activity AS a ON a.pid = l.pid WHERE l.locktype = 'advisory' AND l.granted = TRUE ORDER BY a.backend_start ASC NULLS LAST, l.pid ASC;"`
- `docker compose exec -T postgres psql -U hll_vietnam -d hll_vietnam -c "SELECT id, mode, target_server_slug, status, pages_processed, matches_inserted, matches_updated, notes, started_at, completed_at FROM historical_ingestion_runs ORDER BY id DESC LIMIT 8;"`
- `git diff --name-only`
- `git status --short`

Evidence:

- Docker client/server version: `29.3.1`; Docker Desktop `4.68.0`.
- Baseline before fixed automatic validation:
  - `historical_matches = 9844`
  - first `started_at = 2024-05-17 20:20:17+00`
  - last `started_at = 2026-04-14 14:09:58+00`
- Backend health was `ok`; PostgreSQL `SELECT 1` returned `1`.
- The rebuilt automatic loop path emitted:
  - `classic_fallback_used = true`
  - `classic_fallback_reason = classic-historical-coverage-stale-for-comunidad-hispana-02`
  - `rcon_capture_status = ok`
  - `selected_source = public-scoreboard`
  - `fallback_used = true`
  - `fallback_reason = rcon-primary-writer-succeeded-but-classic-match-archive-still-needs-fallback`
- The bounded automatic loop path advanced persisted data:
  - `historical_matches` moved from `9844` to `9846`
  - last `started_at` moved from `2026-04-14 14:09:58+00` to `2026-04-14 15:16:41+00`
  - latest successful ingestion rows inserted one match for `comunidad-hispana-02` and one for `comunidad-hispana-03`
- Earlier unbounded automatic/full and manual refresh comparison runs both entered public-scoreboard fallback after RCON and then hit upstream CRCON `500` responses from `scoreboard.comunidadhll.es:5443`; those failures were surfaced as terminal command errors while already-persisted per-server progress remained visible in `historical_ingestion_runs`.
- The final advisory-lock query returned zero rows after stopping the timed-out validation container.

Notes:

- One bounded loop validation reached the post-refresh Elo/MMR follow-up and exceeded the 15-minute tool timeout. It was stopped with `docker stop hllvietnam-backend-run-1046e2b39008` after the policy and historical refresh evidence had already been captured. No writer advisory lock remained afterward.
- The upstream CRCON `500` behavior is still external/source failure, not masked as success.
