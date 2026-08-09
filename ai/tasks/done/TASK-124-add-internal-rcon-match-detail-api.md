---
id: TASK-124
title: Add internal RCON match detail API
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto Python
  - Frontend Senior
roadmap_item: rcon-full-data
priority: high
---

# TASK-124 - Add internal RCON match detail API

## Goal

Expose internal match detail data from materialized RCON matches and player stats.

## Background

`frontend/historico-partida.html` needs a reliable internal backend payload when an external scoreboard link is unavailable or not safely correlated. The API should be RCON-first and graceful for partial or old data.

## Constraints

- No UI changes in this task.
- Preserve existing query params and fallback behavior.
- If no materialized RCON detail exists, return a controlled empty or partial payload, not a 500.
- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.
- Do not store secrets, runtime DB files or `backend/runtime`.
- Public scoreboard URL is optional enrichment only.

## Allowed Changes

- `backend/app/routes.py` or existing route modules
- backend read-model modules for historical match detail
- backend tests for response builder/read model
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
  - materialized match/player stats code from TASK-122 and TASK-123
  - `frontend/historico-partida.html`
  - `frontend/assets/js/historico-partida.js`
- Extend or add `/api/historical/matches/detail?server=...&match=...`.
- Prefer an existing endpoint if present and do not break current query params.
- Response should include server, match id, map, game mode, start/end, duration, result, winner, confidence/source basis, optional external `match_url`, player rows and timeline/event summary.
- Player rows should include display name, team, kills, deaths, teamkills, K/D, top weapons, most killed and death-by summary.
- Keep old data fallbacks controlled and backwards-compatible.

## Validation Commands

- `python -m compileall backend/app`
- `python -m pytest backend/tests/<new_or_relevant_match_detail_api_tests>.py`
- `docker compose up -d --build backend`
- `Invoke-WebRequest "http://localhost:8000/api/historical/matches/detail?server=<server>&match=<match>"`
- `Invoke-WebRequest "http://localhost:8000/health"`

## Manual Verification Steps

- Confirm known materialized match detail returns the expected summary and players.
- Confirm missing materialized data returns a controlled partial payload.
- Confirm `/health` still works.
- Confirm no server #03, Elo/MMR or secrets were introduced.
- Confirm `git diff --name-only` matches the allowed scope.

## Git Requirements

- Create a dedicated branch for this task, for example `codex/task-124-rcon-match-detail-api`.
- Run relevant validation before committing.
- Stage only intended files.
- Commit the completed implementation.
- Push the branch to origin.

## Outcome

Extended the existing RCON historical read model behind `/api/historical/matches/detail?server=...&match=...` to prefer materialized RCON AdminLog match detail when available, while preserving the existing competitive-window and public-scoreboard fallback behavior.

Materialized detail payloads now include server, match id, map, game mode, start/end, duration, result, winner, confidence/source basis, safe optional `match_url`, player rows and timeline event counts. Player rows expose display names and derived summaries only, not raw player IDs.

Missing materialized detail remains controlled: the endpoint falls back to the existing paths and returns `found: false` instead of raising a 500 when no detail is available.

## Validation Result

- Passed: `python -m compileall backend/app`
- Pytest was not installed in the local Python environment.
- Passed deterministic fallback: `$env:PYTHONPATH='backend'; python -m unittest backend.tests.test_rcon_materialization_pipeline backend.tests.test_scoreboard_match_links`
- Passed API smoke: `Invoke-WebRequest "http://localhost:8000/health"`.
- Passed API detail check: `Invoke-WebRequest "http://localhost:8000/api/historical/matches/detail?server=comunidad-hispana-02&match=comunidad-hispana-02:1779108337:1779111786:stmariedumontwarfare"` returned `found: true`, `result_source: admin-log-match-ended`, players and timeline counts.
