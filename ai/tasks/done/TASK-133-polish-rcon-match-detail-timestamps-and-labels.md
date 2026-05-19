---
id: TASK-133
title: Polish RCON match detail timestamps and labels
status: done
type: frontend
team: Frontend Senior
supporting_teams:
  - Backend Senior
  - Arquitecto Python
roadmap_item: rcon-full-data
priority: medium
---

# TASK-133 - Polish RCON Match Detail Timestamps And Labels

## Goal

Fix the small but confusing presentation issues in the internal match detail page for materialized RCON matches: misleading equal start/end timestamps, a raw technical match id in the main header, and overly technical visible labels.

## Background

HLL Vietnam now has a RCON-first materialized match pipeline. AdminLog events are parsed, stored, deduplicated and materialized; recent matches prefer materialized RCON AdminLog results; and the internal match detail page renders simplified scoreboard-style data.

The known detail URL works:

- `historico-partida.html?server=comunidad-hispana-02&match=comunidad-hispana-02%3A1779178461%3A1779183861%3Acarentanwarfare`

The current page shows the expected match content, including map, server, score, winner, duration, player stats, weapons, victim/death_by rows and event counts. However, the page currently shows identical `Inicio` and `Fin` timestamps even when `duration_seconds` is correct, and the main header exposes the internal match id.

## Constraints

- Keep the change small and focused.
- Preserve RCON as the source of truth.
- Prefer backend/read-model correctness where possible.
- Do not change the data model more than necessary.
- Do not reactivate Elo/MMR.
- Do not touch Elo/MVP blocks.
- Do not reintroduce Comunidad Hispana #03.
- Do not show `snapshot` wording.
- Do not implement charts.
- Do not break recent match cards.
- Do not break match detail.
- Keep public scoreboard optional enrichment/fallback only.
- Preserve frontend compatibility with direct browser opening where applicable.

## Allowed Changes

- Backend read-model/API code needed to avoid misleading match timestamps or expose timestamp confidence.
- Frontend match detail code needed to render safer timestamp states and friendlier labels.
- Recent-match frontend code only if needed to preserve existing cards after read-model changes.
- This task file when moving it through the workflow.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/frontend-senior.md`
- `ai/orchestrator/backend-senior.md`
- `frontend/historico-partida.html`
- `frontend/assets/js/historico-partida.js`
- `frontend/assets/js/historico-recent-live.js`
- relevant backend historical/read-model modules serving recent matches and match detail

## Implementation Requirements

1. Work from a dedicated branch: `codex/task-133-polish-rcon-match-detail`.
2. Inspect the existing materialized RCON match detail response and frontend rendering before changing behavior.
3. Fix or gracefully handle misleading identical `started_at` / `ended_at` values for materialized RCON matches.
4. Prefer deriving sensible backend/read-model values from reliable `server_time` range and `duration_seconds` when possible.
5. If real absolute timestamps cannot be reliably reconstructed, expose and/or use timestamp confidence so the UI shows a controlled partial state such as `No disponible` or `Estimado`, instead of equal start/end times.
6. Keep `duration_seconds` visible because the duration is reliable from the server_time range.
7. Update the match detail hero/header so it no longer displays the raw technical match id as the main subtitle.
8. Replace the raw id with a user-friendly subtitle such as `Comunidad Hispana #02 - Partida RCON materializada`, or an equivalent Spanish label.
9. Optionally expose the technical match id in a small debug/technical section only if useful and visually secondary.
10. Polish visible labels around source, basis and confidence so they are consistent and understandable for end users.
11. Polish RCON materialized wording, including labels like `cierre de partida RCON` and `Registro RCON materializado`, without exposing implementation terms too prominently.
12. Ensure recent match cards still work after any backend/read-model adjustment.
13. Ensure the known Carentan match detail still renders.
14. Ensure AntonioPruna still renders with 1 kill, 0 deaths and `M1 GARAND`.
15. Ensure the victim row still shows 1 death and `death_by` AntonioPruna.

## Validation Commands

- `python -m compileall backend/app`
- `node --check frontend/assets/js/historico.js`
- `node --check frontend/assets/js/historico-partida.js`
- `node --check frontend/assets/js/historico-recent-live.js`
- `docker compose up -d --build backend frontend`
- `Invoke-WebRequest "http://localhost:8000/health" | Select-Object -ExpandProperty Content`
- `Invoke-WebRequest "http://localhost:8000/api/historical/recent-matches?server=all-servers&limit=10" | Select-Object -ExpandProperty Content`

Use encoded match id:

- `comunidad-hispana-02%3A1779178461%3A1779183861%3Acarentanwarfare`

Open:

- `http://localhost:8080/historico-partida.html?server=comunidad-hispana-02&match=comunidad-hispana-02%3A1779178461%3A1779183861%3Acarentanwarfare`

## Manual Verification Steps

- Detail page no longer shows the raw technical match id in the hero/header.
- Start/end values are not misleading.
- If exact timestamps are unavailable, the UI says `No disponible` or `Estimado`.
- Duration remains visible as `1 h 30 min`.
- Score remains `3 - 2`.
- Winner remains `Aliados`.
- AntonioPruna still shows 1 kill, 0 deaths and `M1 GARAND`.
- Victim row still shows 1 death and `death_by` AntonioPruna.
- Recent match cards still render.
- No `snapshot` wording appears.
- No Elo/MVP blocks appear.
- No server #03 appears.
- `git diff --name-only` matches the scoped implementation.

## Git Requirements

- Create a dedicated branch: `codex/task-133-polish-rcon-match-detail`.
- Run all validation listed above.
- Stage only intended files.
- Commit the completed implementation.
- Push the branch to origin.
- Final git status must be clean.

## Outcome

- Added `timestamp_confidence` for materialized RCON read-model rows.
- When materialized AdminLog start/end absolute timestamps are identical while server-time duration is positive, the read model exposes `started_at`/`ended_at` as unavailable and keeps `closed_at` only for ordering/recent-card continuity.
- The detail UI now hides the raw technical match id from the hero subtitle and shows a friendly RCON materialized subtitle.
- The detail UI shows unreliable start/end values as `No disponible` while preserving reliable duration.
- Polished source/action wording, including `cierre RCON confirmado` and `Abrir en scoreboard`.
- Kept recent match cards rendering and restored the static `Ver partida` external-action label expected by the UI regression check.
- Browser plugin note: Browser was available, but the required browser-control execution tool was not exposed in this session; Playwright fallback via `npx` was blocked by npm certificate verification. Rendered validation used local headless Chrome instead.
- Validation passed: `python -m compileall backend/app`.
- Validation passed: `node --check frontend/assets/js/historico.js`.
- Validation passed: `node --check frontend/assets/js/historico-partida.js`.
- Validation passed: `node --check frontend/assets/js/historico-recent-live.js`.
- Validation passed: `$env:PYTHONPATH='backend'; python -m unittest backend.tests.test_rcon_materialization_pipeline`.
- Validation blocked: `python -m pytest backend/tests/test_rcon_materialization_pipeline.py` because `pytest` is not installed.
- Validation passed: `docker compose up -d --build backend frontend`.
- Validation passed: `/health` and `/api/historical/recent-matches?server=all-servers&limit=10`.
- Manual/API verification passed for known Carentan match: duration `5400`, score `3 - 2`, winner `allied`, AntonioPruna `1/0` with `M1 GARAND`, victim death_by AntonioPruna.
- Rendered Chrome validation passed for detail and recent pages at desktop/mobile screenshot sizes; visible text contains no `snapshot`, Elo/MMR block or Comunidad Hispana #03.
- Operational note: an already-running advanced `rcon-historical-worker` caused transient SQLite open errors during Docker validation; it was stopped because the default deployment for this repo is `backend` + `frontend`.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
