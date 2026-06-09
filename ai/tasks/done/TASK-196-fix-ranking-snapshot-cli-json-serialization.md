---
id: TASK-196-fix-ranking-snapshot-cli-json-serialization
title: Fix ranking snapshot CLI JSON serialization
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto Python
roadmap_item: foundation
priority: high
---

# TASK-196 - Fix ranking snapshot CLI JSON serialization

## Goal

Correct the `generate-ranking-snapshot` CLI output path so it can print the generated payload as JSON without failing on `datetime` or `date` values.

## Context

The weekly ranking snapshot command already generates and persists snapshots correctly in PostgreSQL. Production validation confirmed `ranking_snapshots.snapshot_status=ready`, `item_count=20`, `source_matches_count=41`, and `/api/ranking?timeframe=weekly&metric=kills&limit=20` returns `snapshot_status=ready` with `fallback_used=false`.

The remaining bug is only in the CLI print path inside `backend/app/rcon_historical_leaderboards.py`, where `_main()` currently calls `json.dumps({"status": "ok", "data": payload}, ensure_ascii=True, indent=2)` and can still receive native `datetime` values inside `payload`.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Read the listed files first.
2. Apply only the scoped JSON serialization fix for the CLI output path.
3. Reuse an existing serialization pattern if a safe local helper already exists.
4. Validate scripts, local serialization behavior and CLI output behavior when possible.
5. Document root cause, applied change and validation results.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/main.py`
- `scripts/run-stats-validation.ps1`

## Expected Files to Modify

- `backend/app/rcon_historical_leaderboards.py`
- `scripts/run-stats-validation.ps1`
- `ai/tasks/done/TASK-196-fix-ranking-snapshot-cli-json-serialization.md`

## Constraints

- Keep the change minimal.
- Fix only the CLI JSON serialization path.
- Do not change snapshot generation logic.
- Do not change `/api/ranking`.
- Do not touch frontend, assets or design.
- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.
- Do not change annual behavior except reusing a generic serializer pattern if it already exists.

## Validation

Before completing the task ensure:

- `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- local import validation proves the payload from `generate_ranking_snapshot(...)` can be serialized with `json.dumps`
- if the environment allows it, execute the CLI and confirm it prints JSON without `TypeError`
- `git diff --name-only` matches the expected scope

## Outcome

Document:

- Root cause:
  - `generate_ranking_snapshot(...)` already generated and persisted the snapshot correctly.
  - the CLI failure happened afterwards in `_main()`, when `json.dumps({"status": "ok", "data": payload}, ensure_ascii=True, indent=2)` received native `datetime` / `date` objects inside `payload`.
  - the bug only affected CLI JSON printing and did not affect PostgreSQL snapshot persistence or `/api/ranking`.

- Applied change:
  - `backend/app/rcon_historical_leaderboards.py`
    - added a local controlled `_json_default(...)` serializer for `datetime` and `date`
    - serializes `datetime` through the module's existing `_to_iso(...)` helper
    - serializes `date` with `isoformat()`
    - updated the CLI `json.dumps(...)` call to use `default=_json_default`
  - `scripts/run-stats-validation.ps1`
    - extended the CLI regression to return a payload containing both `datetime` and `date`
    - verifies `_main(...)` exits successfully
    - verifies stdout JSON contains ISO strings instead of failing with `TypeError`

- Validation executed:
  - `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
  - `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
  - local import validation with `json.dumps(..., default=app.rcon_historical_leaderboards._json_default)`
  - local `_main(...)` validation with a monkeypatched `generate_ranking_snapshot(...)` payload containing `datetime` and `date`
  - local CLI execution:
    - `python -m app.rcon_historical_leaderboards generate-ranking-snapshot --timeframe weekly --server-key all --metric kills --limit 20 --sqlite-path backend/data/hll_vietnam_dev.sqlite3`

- Validation notes:
  - the live backend at `http://127.0.0.1:8000` was not available in this environment, so route-contract validation completed through local Python imports.
  - the local CLI command printed JSON successfully and no longer raised `TypeError: Object of type datetime is not JSON serializable`.
  - production behavior described in the task context remains confirmed: snapshot generation already worked, and the observed failure was only the final CLI JSON print step.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
