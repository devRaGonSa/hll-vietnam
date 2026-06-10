---
id: TASK-229
title: Fix legacy historical summary and recent matches timeouts
status: done
type: backend
team: Backend Senior
supporting_teams: []
roadmap_item: foundation
priority: high
---

# TASK-229 - Fix legacy historical summary and recent matches timeouts

## Goal

Corregir los endpoints historicos legacy agregados que seguian agotando el timeout de 30 s en produccion:

- `GET /api/historical/server-summary?server=all-servers`
- `GET /api/historical/recent-matches?server=all-servers&limit=20`

## Context

La auditoria posterior a `TASK-228` confirmo que `/api/servers`, `/api/servers/latest` y `/api/servers/history` ya respondian correctamente, pero dos probes legacy de `historico.html legacy` seguian bloqueando:

- `historical-server-summary-all-servers`: timeout 30024 ms.
- `historical-recent-matches-all-servers`: timeout 30045 ms.

No se debian tocar `/api/servers`, `/api/current-match/kills` ni `/api/current-match/players`.

## Files Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/backend-senior.md`
- `scripts/audit_public_requests.py`
- `backend/app/routes.py`
- `backend/app/payloads.py`
- `backend/app/historical_storage.py`
- `backend/app/postgres_display_storage.py`
- `backend/tests/test_historical_snapshot_refresh.py`

## Call Chain Analysis

Cadena de auditoria:

1. `scripts/audit_public_requests.py` genera `historical-server-summary-all-servers` como `GET /api/historical/server-summary?server=all-servers`.
2. El mismo script genera `historical-recent-matches-all-servers` como `GET /api/historical/recent-matches?server=all-servers&limit=20`.
3. `backend/app/routes.py` mapea esas rutas a `build_historical_server_summary_payload()` y `build_recent_historical_matches_payload()`.
4. Los builders legacy intentaban usar el read model historico RCON y, si no cubria la peticion, caian a storage legacy publico.
5. Para `server=all-servers`, el fallback ejecutaba agregaciones globales:
   - SQLite: `list_historical_server_summaries()` llama a `_build_all_servers_summary()` y esta recalcula conteos globales sobre tablas historicas.
   - PostgreSQL: `list_scoreboard_server_summaries(server_slug=all-servers)` inicializa display storage y agrega tablas migradas de public-scoreboard.
   - Recent matches puede completar desde `list_recent_historical_matches()`, tambien sobre storage legacy.
6. Los endpoints snapshot equivalentes (`/api/historical/snapshots/server-summary` y `/api/historical/snapshots/recent-matches`) ya respondian rapido porque solo leen snapshots precomputados con politica `read-only-fast-path`.

## Root Cause

Los endpoints legacy agregados para `all-servers` conservaban fallback runtime hacia CRCON/PostgreSQL display storage. En produccion, cuando el read model RCON no cubria la respuesta o necesitaba completar datos, el request publico entraba en agregaciones globales y/o inicializacion de storage, agotando el timeout de 30 s.

## Changes

- `backend/app/payloads.py`
  - `build_recent_historical_matches_payload(server_slug="all-servers")` pasa a delegar en `build_recent_historical_matches_snapshot_payload()`.
  - `build_historical_server_summary_payload(server_slug="all-servers")` pasa a delegar en `build_historical_server_summary_snapshot_payload()`.
  - Ambos wrappers conservan `context` legacy y campos basicos (`items`, `limit`, `server_slug`, `summary_basis`) pero exponen `source: historical-precomputed-snapshots` y `legacy_endpoint_policy: snapshot-read-only-fast-path`.
  - Si no existe snapshot, responden JSON controlado con snapshot missing y lista vacia, sin read model RCON ni fallback runtime pesado.
- `backend/tests/test_historical_snapshot_refresh.py`
  - Cubre que los dos endpoints legacy `all-servers` usan snapshots.
  - Verifica que no llaman a `get_rcon_historical_read_model()`.
  - Verifica que no llaman a `list_recent_historical_matches()` ni `list_historical_server_summaries()`.
- `docs/FULL_APPLICATION_REQUEST_AUDIT.md`
  - Documenta el estado post-fix de `TASK-229`.
- `docs/PERFORMANCE_PUBLIC_QUERY_AUDIT.md`
  - Actualiza la politica de los endpoints legacy agregados.

## Validation

Validaciones ejecutadas:

```powershell
python -m compileall backend/app
cd backend
python -m unittest tests.test_historical_snapshot_refresh
python -m unittest tests.test_current_match_payload tests.test_rcon_admin_log_storage tests.test_historical_snapshot_refresh
```

Resultados:

- `python -m compileall backend/app`: OK.
- `cd backend; python -m unittest tests.test_historical_snapshot_refresh`: OK, 15 tests.
- `cd backend; python -m unittest tests.test_current_match_payload tests.test_rcon_admin_log_storage tests.test_historical_snapshot_refresh`: OK, 22 tests.

Auditoria de produccion pendiente tras redeploy:

```powershell
python .\scripts\audit_public_requests.py --base-url https://comunidadhll.devzamode.es --timeout 30 --filter servers --output tmp\task229_servers_recheck_after.json
```

## Outcome

Los endpoints legacy agregados dejan de ejecutar read model RCON o fallback runtime pesado en lectura publica y quedan como wrappers read-only sobre snapshots precomputados. El contrato se mantiene compatible de forma razonable: HTTP 200, `status: ok`, `data.items` y metadata de snapshot/fallback.

No se cambiaron hosts, puertos, `27001`, variables de entorno ni configuracion de servidores. No se tocaron frontend, assets, SVGs, imagenes fisicas, `ai/system-metrics.md` ni `tmp/`.

## Change Budget

- Archivos de codigo modificados: 2.
- Documentacion actualizada: 3 archivos.
- No se creo arquitectura nueva; solo se redirigio el path legacy agregado a read models/snapshots ya existentes.
