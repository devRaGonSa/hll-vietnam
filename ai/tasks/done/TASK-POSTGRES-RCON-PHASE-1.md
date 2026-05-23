---
id: TASK-POSTGRES-RCON-PHASE-1
title: Migrate RCON historical persistence phase 1
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto de Base de Datos
  - Frontend Senior
roadmap_item: foundation
priority: high
---

# TASK-POSTGRES-RCON-PHASE-1 - Migrate RCON historical persistence phase 1

## Goal

Move the lock-prone RCON historical pipeline to PostgreSQL in Docker while
keeping local SQLite fallback and fixing the requested match-detail and server
card frontend regressions.

## Context

AdminLog ingestion and materialization currently share SQLite files with
multiple services and materialization can fail with `database is locked`.
PostgreSQL must become authoritative for RCON capture, AdminLog events,
materialized matches, player stats and the detail/recent read model in the
advanced Docker flow. Scoreboard historical persistence may remain on SQLite in
this phase when it is used only as fallback or correlation source.

## Steps

1. Inspect the storage, read-model and frontend files named in the request.
2. Add a deterministic PostgreSQL schema and route the phase-1 RCON storage
   domains through it when `HLL_BACKEND_DATABASE_URL` is set.
3. Wire Compose diagnostics and required frontend fixes without expanding Elo,
   backend scope outside RCON persistence, or Comunidad Hispana #03 targets.
4. Validate the requested commands, document what remains SQLite-backed, and
   complete the task record.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `backend/app/config.py`
- `backend/app/rcon_admin_log_storage.py`
- `backend/app/rcon_admin_log_materialization.py`
- `frontend/assets/js/historico-partida.js`

## Expected Files to Modify

- `backend/app/config.py`
- `backend/app/postgres_rcon_storage.py`
- `backend/app/rcon_admin_log_storage.py`
- `backend/app/rcon_admin_log_materialization.py`
- `backend/app/rcon_historical_storage.py`
- `backend/app/rcon_scoreboard_correlation.py`
- `backend/app/storage_diagnostics.py`
- `backend/README.md`
- `backend/requirements.txt`
- `backend/.env.example`
- `docker-compose.yml`
- `frontend/assets/js/historico-partida.js`
- `frontend/assets/js/historico.js`
- `frontend/assets/js/historico-recent-live.js`
- `frontend/assets/js/main.js`
- `frontend/assets/css/historico-scoreboard-detail.css`
- `docs/decisions.md`
- `scripts/run-historical-ui-regression-tests.ps1`

## Constraints

- PostgreSQL is the Docker default for migrated RCON domains.
- SQLite remains only fallback or source material for domains not migrated in
  this phase.
- Do not add SQLite lock workarounds as the main solution.
- Keep external scoreboard URLs on the trusted scoreboard allowlist.
- Do not modify unrelated files or add runtime database artifacts.

## Validation

- `python -m compileall backend/app`
- `python -m app.storage_diagnostics`
- `node --check frontend/assets/js/main.js`
- `node --check frontend/assets/js/historico.js`
- `node --check frontend/assets/js/historico-recent-live.js`
- `node --check frontend/assets/js/historico-partida.js`
- `powershell -ExecutionPolicy Bypass -File scripts/run-rcon-data-pipeline-tests.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- Requested Docker Compose and endpoint checks when local Docker/RCON
  credentials permit them.

## Outcome

Implemented phase-1 PostgreSQL delegation for RCON capture samples/windows,
AdminLog events/profile snapshots, materialized RCON matches/player stats, and
safe scoreboard candidate caching. Docker Compose now configures PostgreSQL as
the RCON storage backend for `backend`, `historical-runner` and
`rcon-historical-worker`; local code paths with explicit SQLite paths or no
database URL retain SQLite fallback behavior.

Frontend changes remove hover-driven player panel expansion in the internal
match detail table, keep the scoreboard link on the internal detail action area
only, and suppress pending-style region placeholders on server cards.

Validation completed:

- `python -m compileall backend/app`
- `python -m app.storage_diagnostics` from `backend/`
- `node --check frontend/assets/js/main.js`
- `node --check frontend/assets/js/historico.js`
- `node --check frontend/assets/js/historico-recent-live.js`
- `node --check frontend/assets/js/historico-partida.js`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- `docker compose --profile advanced config --quiet`
- local fallback HTTP smoke for `/health`,
  `/api/historical/recent-matches`, and the requested known match detail URL
- direct known-match detail payload check confirmed safe URL
  `https://scoreboard.comunidadhll.es:5443/games/1562094`

`scripts/run-rcon-data-pipeline-tests.ps1` completed parser/storage and
unittest work, then exited nonzero when its optional Docker smoke step could
not reach the Docker Desktop Linux engine. The requested `docker compose
--profile advanced up ...` and `docker compose --profile advanced ps` checks
failed for the same local engine-unavailable reason, so container diagnostics,
container RCON commands and Docker-backed HTTP probes remain to rerun when
Docker is available. The Browser plugin is listed but its required JavaScript
control tool was not exposed in this session, so rendered interaction QA remains
manual or follow-up Browser verification.

Phase boundary documented in `docs/decisions.md` and diagnostics: live server
snapshot cache, public-scoreboard `historical_*` data/rankings, historical
snapshot files, player-event ledger and paused Elo/MMR storage remain SQLite or
file-backed in this phase.

## Change Budget

This phase intentionally exceeds the default change budget because PostgreSQL
wiring crosses schema initialization, Compose runtime, RCON storage domains,
diagnostics, docs, and the requested frontend regressions. Keep the migration
surface limited to the RCON path and leave remaining SQLite domains documented.
