---
id: TASK-144
title: Home region cleanup and RCON freshness diagnostics
status: done
type: integration
team: Backend Senior
supporting_teams: [Frontend Senior]
roadmap_item: foundation
priority: high
---

# TASK-144 - Home region cleanup and RCON freshness diagnostics

## Goal

Hide placeholder region values on the home page server cards and improve RCON historical freshness diagnostics so stale recent matches are explainable from worker/runner logs.

## Context

The home page currently renders `Region pendiente` when a server region is missing. Recent RCON materialized matches can also appear stale without clear logs showing whether AdminLog events were seen, inserted, duplicated or materialized.

## Steps

1. Inspect home server-card rendering and RCON runner/worker/ingestion/materialization paths.
2. Hide placeholder/missing region quick facts while preserving map data.
3. Determine whether historical-runner refreshes RCON AdminLog materialization or whether rcon-historical-worker owns it.
4. Add minimal logging/summary output for AdminLog ingestion/materialization and latest materialized match freshness.
5. Validate frontend syntax, backend compile, pipeline scripts, Compose services, logs, manual commands and rendered pages.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/backend-senior.md`
- `ai/orchestrator/frontend-senior.md`
- `frontend/assets/js/main.js`
- `backend/app/rcon_historical_worker.py`
- `backend/app/rcon_admin_log_ingestion.py`
- `backend/app/rcon_admin_log_materialization.py`
- `backend/app/historical_runner.py`
- `docker-compose.yml`

## Expected Files to Modify

- `frontend/assets/js/main.js`
- `backend/app/rcon_historical_worker.py`
- `backend/app/rcon_admin_log_ingestion.py`
- `backend/app/rcon_admin_log_materialization.py`
- `ai/tasks/done/TASK-144-home-region-and-rcon-freshness.md`

## Constraints

- Do not expose secrets.
- Do not reintroduce Comunidad Hispana #03.
- Do not change recent-card visual design.
- Do not commit runtime DB files.
- Preserve manual RCON commands.

## Validation

- `python -m compileall backend/app`
- `node --check frontend/assets/js/main.js`
- `node --check frontend/assets/js/historico.js`
- `node --check frontend/assets/js/historico-recent-live.js`
- `node --check frontend/assets/js/historico-partida.js`
- `powershell -ExecutionPolicy Bypass -File scripts/run-rcon-data-pipeline-tests.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- `docker compose --profile advanced up -d --build backend frontend historical-runner rcon-historical-worker`
- `docker compose --profile advanced ps`
- `docker compose logs --tail=150 historical-runner`
- `docker compose logs --tail=150 rcon-historical-worker`
- `docker compose exec backend python -m app.rcon_admin_log_ingestion --minutes 360`
- `docker compose exec backend python -m app.rcon_admin_log_materialization`
- `Invoke-WebRequest "http://localhost:8000/health" | Select-Object -ExpandProperty Content`
- `Invoke-WebRequest "http://localhost:8000/api/historical/recent-matches?server=all-servers&limit=20" | Select-Object -ExpandProperty Content`
- Browser verification on `index.html?nocache=region`
- Browser verification on `historico.html?nocache=freshness`

## Outcome

Implemented. Home server cards now omit the Region quick fact when the region is missing or a placeholder such as `Region pendiente`, while preserving the Mapa quick fact. RCON capture now runs AdminLog materialization after AdminLog ingestion and emits freshness diagnostics in the worker result, including event counters, materialized match counters and latest materialized/AdminLog match-end timestamps per configured server.

Findings:

- `historical-runner` already calls the RCON capture path when historical data source is RCON, but the capture path previously ingested AdminLog entries without materializing them into recent matches.
- `rcon-historical-worker` owns the 10-minute capture loop and now materializes after ingestion, so recent matches can advance without requiring a manual materialization command.
- The live diagnostics show new recent data after the previously stale `17:38` item. Recent matches now include `comunidad-hispana-01:1779299747:1779305147:carentanwarfare` closed at `2026-05-20T19:26:46.519Z` and `comunidad-hispana-02:1779296626:1779301626:carentanwarfare` closed at `2026-05-20T18:41:59.219Z`.

Validation passed:

- `python -m compileall backend/app`
- `node --check frontend/assets/js/main.js`
- `node --check frontend/assets/js/historico.js`
- `node --check frontend/assets/js/historico-recent-live.js`
- `node --check frontend/assets/js/historico-partida.js`
- `powershell -ExecutionPolicy Bypass -File scripts/run-rcon-data-pipeline-tests.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- `docker compose --profile advanced up -d --build backend frontend historical-runner rcon-historical-worker`
- `docker compose --profile advanced ps`
- `docker compose logs --tail=150 historical-runner`
- `docker compose logs --tail=150 rcon-historical-worker`
- `docker compose exec backend python -m app.rcon_admin_log_ingestion --minutes 360`
- `docker compose exec backend python -m app.rcon_admin_log_materialization`
- `Invoke-WebRequest "http://localhost:8000/health" | Select-Object -ExpandProperty Content`
- `Invoke-WebRequest "http://localhost:8000/api/historical/recent-matches?server=all-servers&limit=20" | Select-Object -ExpandProperty Content`
- Browser verification on `http://localhost:8080/index.html?nocache=region`
- Browser verification on `http://localhost:8080/historico.html?nocache=freshness`

Notes:

- The RCON pipeline script reports existing SQLite `ResourceWarning` messages from its test harness, but the unittest suites return `OK` and the script reports validation passed.
- The integration script exits successfully, but the local runtime DB emits an existing `database disk image is malformed` traceback after the pass message. Runtime DB files were not modified for commit.
- Browser plugin runtime tools were not exposed by tool discovery in this session, so rendered validation used local Chrome/Selenium fallback.
