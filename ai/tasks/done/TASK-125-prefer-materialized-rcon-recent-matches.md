---
id: TASK-125
title: Prefer materialized RCON recent matches
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Frontend Senior
roadmap_item: rcon-full-data
priority: high
---

# TASK-125 - Prefer materialized RCON recent matches

## Goal

Update the recent matches API to prefer materialized RCON match records over approximate competitive windows and public-scoreboard fallback.

## Background

End users should see correct scores as consistently as possible. RCON AdminLog `MATCH ENDED` data should be the primary source when available, with active RCON sessions next and public scoreboard only as fallback or degraded enrichment.

## Constraints

- No frontend changes unless strictly necessary for contract compatibility.
- Do not show stale public scoreboard as selected source when RCON is healthy.
- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.
- Do not store secrets, runtime DB files or `backend/runtime`.
- Preserve RCON-first policy.

## Allowed Changes

- backend recent matches read model modules
- backend route tests or read-model tests
- minimal compatibility-only frontend changes if unavoidable and justified
- this task file when moving it through the workflow

## Implementation Requirements

- Work from a dedicated branch for this task.
- Read first:
  - `AGENTS.md`
  - `ai/architecture-index.md`
  - `ai/repo-context.md`
  - `ai/orchestrator/backend-senior.md`
  - `backend/app/routes.py`
  - `backend/app/rcon_historical_read_model.py`
  - existing recent matches read-model/storage modules
  - materialized match code from TASK-122
- Use priority:
  - materialized RCON matches with `MATCH ENDED` result
  - active/partial RCON session windows with current gamestate
  - public-scoreboard fallback only if RCON is unavailable or explicitly degraded
- Recent match items should expose result scores/winner when available.
- Add `result_source` values: `admin-log-match-ended`, `rcon-session`, `public-scoreboard-fallback`, `unavailable`.
- Include `match_url` only when safe external link exists.
- Include internal detail link data whenever match id and server allow it.

## Validation Commands

- `python -m compileall backend/app`
- `python -m pytest backend/tests/<new_or_relevant_recent_matches_tests>.py`
- `docker compose up -d --build backend`
- `docker compose exec backend python -m app.rcon_admin_log_ingestion --minutes 1440`
- `Invoke-WebRequest "http://localhost:8000/api/historical/recent-matches?server=all-servers&limit=10"`

## Manual Verification Steps

- Confirm recent matches show RCON/AdminLog scores where available.
- Confirm source priority uses AdminLog over stale public scoreboard.
- Confirm internal detail data exists for match cards.
- Confirm `/health` and `frontend/historico.html` are not broken.
- Confirm `git diff --name-only` matches the allowed scope.

## Git Requirements

- Create a dedicated branch for this task, for example `codex/task-125-rcon-recent-matches-priority`.
- Run relevant validation before committing.
- Stage only intended files.
- Commit the completed implementation.
- Push the branch to origin.

## Outcome

Updated the RCON historical recent-matches read model to prefer materialized AdminLog matches with authoritative `MATCH ENDED` results before using active/session competitive windows. Public-scoreboard recent matches remain fallback only when RCON read coverage is unavailable or empty.

Recent match rows now include `result_source` values for the implemented paths:

- `admin-log-match-ended`
- `rcon-session`
- `public-scoreboard-fallback`

The payload builder no longer selects the public scoreboard merely to fill the requested limit when RCON has usable materialized/session results. Stale local historical targets such as `comunidad-hispana-03` are not re-added to configuration or shown as configured RCON targets by this batch.

## Validation Result

- Passed: `python -m compileall backend/app`
- Pytest was not installed in the local Python environment.
- Passed deterministic fallback: `$env:PYTHONPATH='backend'; python -m unittest backend.tests.test_rcon_materialization_pipeline backend.tests.test_scoreboard_match_links`
- Passed API recent-matches check: `Invoke-WebRequest "http://localhost:8000/api/historical/recent-matches?server=all-servers&limit=10"` returned `selected_source: rcon`, `fallback_used: false`, and materialized rows with `result_source: admin-log-match-ended`.
