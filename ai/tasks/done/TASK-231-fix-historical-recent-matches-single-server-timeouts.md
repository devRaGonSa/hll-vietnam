---
id: TASK-231
title: Fix historical recent matches single server timeouts
status: done
type: backend
team: Backend Senior
supporting_teams: []
roadmap_item: foundation
priority: high
---

# TASK-231 - Fix historical recent matches single server timeouts

## Goal

Corregir los dos `CRITICAL` restantes de la auditoria publica global:

- `GET /api/historical/recent-matches?server=comunidad-hispana-01&limit=20`
- `GET /api/historical/recent-matches?server=comunidad-hispana-02&limit=20`

## Context

Tras `TASK-230`, la auditoria completa mostro:

- `launched`: 195
- `OK`: 78
- `WARNING`: 115
- `CRITICAL`: 2

Los dos `CRITICAL` restantes eran:

- `historical-recent-matches-comunidad-hispana-01`: timeout `30032.24 ms`.
- `historical-recent-matches-comunidad-hispana-02`: timeout `30027.15 ms`.

Los snapshots equivalentes y el legacy agregado ya respondian rapido:

- `snapshot-recent-matches-comunidad-hispana-01`: `77.50 ms`.
- `snapshot-recent-matches-comunidad-hispana-02`: `51.11 ms`.
- `historical-recent-matches-all-servers`: `50.66 ms`.
- `snapshot-recent-matches-all-servers`: `63.33 ms`.

## Files Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/backend-senior.md`
- `scripts/audit_public_requests.py`
- `backend/app/routes.py`
- `backend/app/payloads.py`
- `backend/app/rcon_historical_read_model.py`
- `backend/app/rcon_admin_log_materialization.py`
- `backend/tests/test_historical_snapshot_refresh.py`

## Call Chain Analysis

Cadena de auditoria:

1. `scripts/audit_public_requests.py` genera:
   - `historical-recent-matches-comunidad-hispana-01` como `GET /api/historical/recent-matches?server=comunidad-hispana-01&limit=20`.
   - `historical-recent-matches-comunidad-hispana-02` como `GET /api/historical/recent-matches?server=comunidad-hispana-02&limit=20`.
2. `backend/app/routes.py` mapea `/api/historical/recent-matches` a `build_recent_historical_matches_payload(limit=..., server_slug=...)`.
3. Tras `TASK-229`, solo `server=all-servers` usaba snapshot fast-path.
4. CH01 y CH02 seguian entrando en `get_rcon_historical_read_model().list_recent_activity(...)`.
5. El read model llama a `list_rcon_historical_recent_activity()`, que intenta primero `list_materialized_rcon_matches(target_key=..., only_ended=True, limit=...)`.
6. Si RCON no cubria o necesitaba completar items, el builder podia entrar tambien en `list_recent_historical_matches()` como fallback legacy CRCON/PostgreSQL display.
7. Los snapshots equivalentes ya respondian rapido porque leen snapshots precomputados y respetan el `limit`.

## Root Cause

El fast-path de `TASK-229` para recent-matches estaba limitado a `server=all-servers`. Los scopes por servidor seguian usando el camino runtime RCON/materialized y podian caer al fallback legacy de scoreboard, ambos fuera del contrato de lectura publica rapida. En produccion, CH01 y CH02 agotaban los 30 s en ese path.

## Changes

- `backend/app/payloads.py`
  - `build_recent_historical_matches_payload()` usa snapshot fast-path para cualquier `server_slug` explicito, no solo `all-servers`.
  - Se extrajo `_build_recent_historical_matches_legacy_snapshot_payload()` para conservar `context`, `limit`, `server_slug`, `items`, `historical_data_source`, `coverage_basis` y `legacy_endpoint_policy`.
  - Si no hay snapshot, devuelve JSON controlado con `items: []` y metadata de snapshot missing, sin RCON live, sin scoreboard externo y sin fallback runtime pesado.
- `backend/tests/test_historical_snapshot_refresh.py`
  - Cubre que `comunidad-hispana-01` no llama a `get_rcon_historical_read_model()` ni a `list_recent_historical_matches()`.
  - Cubre que `comunidad-hispana-02` usa el mismo fast-path.
  - Mantiene cobertura de `all-servers`.
  - Mantiene cobertura del fast-path de `server-summary` de `TASK-230`.
- `docs/FULL_APPLICATION_REQUEST_AUDIT.md`
  - Documenta el estado post-fix de `TASK-231`.
- `docs/PERFORMANCE_PUBLIC_QUERY_AUDIT.md`
  - Actualiza la politica de `/api/historical/recent-matches?server=<scope>` como wrapper legacy sobre snapshot read-only.

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
- `cd backend; python -m unittest tests.test_historical_snapshot_refresh`: OK, 19 tests.
- `cd backend; python -m unittest tests.test_current_match_payload tests.test_rcon_admin_log_storage tests.test_historical_snapshot_refresh`: OK, 26 tests.

Auditoria de produccion pendiente tras redeploy:

```powershell
python .\scripts\audit_public_requests.py --base-url https://comunidadhll.devzamode.es --timeout 30 --output tmp\full_audit_after_task231.json
```

## Outcome

Los endpoints legacy recent-matches por servidor quedan alineados con los snapshots rapidos que ya consume `historico.html`. CH01, CH02 y `all-servers` evitan RCON live, scoreboard externo, inicializaciones de storage y fallbacks runtime pesados en lectura publica.

No se cambiaron hosts, puertos, `27001`, variables de entorno ni configuracion de servidores. No se tocaron frontend, assets, SVGs, imagenes fisicas, `ai/system-metrics.md` ni `tmp/`.

## Change Budget

- Archivos de codigo modificados: 2.
- Documentacion actualizada: 3 archivos.
- Sin cambios en frontend ni configuracion.
