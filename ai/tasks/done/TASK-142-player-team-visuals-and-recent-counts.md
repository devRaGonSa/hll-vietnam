---
id: TASK-142
title: Player team visuals and recent counts
status: done
type: frontend
team: Frontend Senior
supporting_teams: [Backend Senior, Experto en interfaz]
roadmap_item: foundation
priority: high
---

# TASK-142 - Player team visuals and recent counts

## Goal

Fix historical UI/data consistency by visually distinguishing player teams in internal match detail tables and exposing meaningful recent-match player counts for RCON materialized matches.

## Context

Recent match cards can show `Jugadores = 0` even when the corresponding internal detail page has materialized player rows. The detail player table also needs an additive visual distinction for Allies/Aliados and Axis/Eje rows while preserving all existing stats and detail-page behavior.

## Steps

1. Inspect the listed files first.
2. Fix the backend RCON recent-match read model to expose a non-zero materialized player count when player stats exist.
3. Add team-specific visual styling to all internal match detail player rows or team cells.
4. Validate backend, frontend syntax, RCON pipeline, integration scripts, advanced Compose services and rendered UI behavior.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/backend-senior.md`
- `ai/orchestrator/frontend-senior.md`
- `backend/app/rcon_historical_read_model.py`
- `backend/app/rcon_admin_log_materialization.py`
- `backend/app/rcon_admin_log_storage.py`
- `frontend/assets/js/historico-partida.js`
- `frontend/assets/css/historico-scoreboard-detail.css`
- `frontend/assets/css/historico.css`

## Expected Files to Modify

- `backend/app/rcon_historical_read_model.py`
- `backend/app/rcon_admin_log_materialization.py`
- `frontend/assets/js/historico-partida.js`
- `frontend/assets/css/historico-scoreboard-detail.css`
- `ai/tasks/done/TASK-142-player-team-visuals-and-recent-counts.md`

## Constraints

- Do not modify public scoreboard behavior.
- Do not modify frontend recent-card layout beyond consuming corrected backend data.
- Do not reintroduce raw match id, Estado, Resultado confirmado, Fuente, RCON/debug text, timeline/events, confidence/source/base, Elo/MVP blocks or Comunidad Hispana #03.
- Do not commit runtime DB files.

## Validation

- `python -m compileall backend/app`
- `node --check frontend/assets/js/historico.js`
- `node --check frontend/assets/js/historico-recent-live.js`
- `node --check frontend/assets/js/historico-partida.js`
- `powershell -ExecutionPolicy Bypass -File scripts/run-rcon-data-pipeline-tests.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- `docker compose --profile advanced up -d --build backend frontend historical-runner rcon-historical-worker`
- `docker compose --profile advanced ps`
- `Invoke-WebRequest "http://localhost:8000/health" | Select-Object -ExpandProperty Content`
- `Invoke-WebRequest "http://localhost:8000/api/historical/recent-matches?server=all-servers&limit=20" | Select-Object -ExpandProperty Content`
- Browser verification on `http://localhost:8080/historico.html?nocache=player-counts`
- Browser verification on an internal match detail page with materialized players

## Outcome

Implemented. Materialized RCON recent-match rows now include player-stat counts and the RCON historical read model exposes those counts as `player_count` for recent cards and detail payloads. The internal match detail player table now renders localized team badges and team-specific row accents for Aliados, Eje and No disponible while preserving the existing stats columns and detail-page scoreboard link.

Validation passed:

- `python -m compileall backend/app`
- `node --check frontend/assets/js/historico.js`
- `node --check frontend/assets/js/historico-recent-live.js`
- `node --check frontend/assets/js/historico-partida.js`
- `powershell -ExecutionPolicy Bypass -File scripts/run-rcon-data-pipeline-tests.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- `docker compose --profile advanced up -d --build backend frontend historical-runner rcon-historical-worker`
- `docker compose --profile advanced ps`
- `Invoke-WebRequest "http://localhost:8000/health" | Select-Object -ExpandProperty Content`
- `Invoke-WebRequest "http://localhost:8000/api/historical/recent-matches?server=all-servers&limit=20" | Select-Object -ExpandProperty Content`
- Browser verification on `http://localhost:8080/historico.html?nocache=player-counts`
- Browser verification on `historico-partida.html` for `comunidad-hispana-02:1779178461:1779183861:carentanwarfare`

Notes:

- The RCON pipeline test reports existing SQLite `ResourceWarning` messages from its test harness, but both unittest suites return `OK` and the script reports validation passed.
- The browser plugin was not exposed by tool discovery in this session, so rendered UI verification used local Chrome/Selenium fallback.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
