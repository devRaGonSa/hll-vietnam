---
id: TASK-230
title: Fix historical server summary single server timeout
status: done
type: backend
team: Backend Senior
supporting_teams: []
roadmap_item: foundation
priority: high
---

# TASK-230 - Fix historical server summary single server timeout

## Goal

Corregir el ultimo `CRITICAL` restante de la auditoria publica global:

- `GET /api/historical/server-summary?server=comunidad-hispana-01`

## Context

Tras `TASK-229`, los endpoints legacy agregados `all-servers` dejaron de hacer timeout. La auditoria completa posterior mostro un unico `CRITICAL`:

- `historical-server-summary-comunidad-hispana-01`
- HTTP 200
- `10120.89 ms`
- `fallback=False`

Los endpoints relacionados respondian correctamente:

- `historical-server-summary-comunidad-hispana-02`: `139.37 ms`, OK, `fallback=False`.
- `snapshot-server-summary-comunidad-hispana-01`: `42.14 ms`, WARNING, `fallback=True`.
- `snapshot-server-summary-comunidad-hispana-02`: `55.97 ms`, WARNING, `fallback=True`.
- `historical-server-summary-all-servers`: ya corregido en `TASK-229`.

## Files Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/backend-senior.md`
- `backend/README.md`
- `backend/requirements.txt`
- `docs/project-overview.md`
- `docs/decisions.md`
- `scripts/audit_public_requests.py`
- `backend/app/routes.py`
- `backend/app/payloads.py`
- `backend/app/rcon_historical_read_model.py`
- `backend/tests/test_historical_snapshot_refresh.py`

## Call Chain Analysis

Cadena de auditoria:

1. `scripts/audit_public_requests.py` genera `historical-server-summary-comunidad-hispana-01` como `GET /api/historical/server-summary?server=comunidad-hispana-01`.
2. `backend/app/routes.py` mapea `/api/historical/server-summary` a `build_historical_server_summary_payload(server_slug=...)`.
3. Tras `TASK-229`, solo `server=all-servers` usaba snapshot fast-path.
4. `server=comunidad-hispana-01` y `server=comunidad-hispana-02` seguian intentando `get_rcon_historical_read_model().list_server_summaries(...)`.
5. Ese read model llama a `list_rcon_historical_server_summaries()`.
6. `_build_server_summary()` enriquece cada resumen con `list_rcon_historical_recent_activity(server_key=..., limit=1)`.
7. Esa lectura intenta primero `list_materialized_rcon_matches(target_key=..., only_ended=True, limit=1)`, que entra en la capa materializada RCON/AdminLog.
8. En produccion, CH01 tardo ~10 s en esa lectura de actividad aunque termino con `fallback=False`; CH02 uso el mismo path pero respondio rapido. La diferencia observable es el coste de la lectura RCON/materialized para CH01, no un fallback CRCON ni un error de configuracion.
9. El endpoint snapshot equivalente ya respondia rapido porque solo lee snapshots precomputados.

## Root Cause

El endpoint legacy por servidor seguia usando el read model RCON runtime para `server-summary`. Aunque la respuesta fuese exitosa y `fallback=False`, el builder hacia una lectura adicional de actividad reciente por servidor para completar `activity.latest_*`. En CH01 esa consulta sobre datos materializados RCON/AdminLog era lenta y elevaba el endpoint a `CRITICAL`.

## Changes

- `backend/app/payloads.py`
  - `build_historical_server_summary_payload()` usa snapshot fast-path para cualquier `server_slug` explicito, no solo `all-servers`.
  - Se extrajo `_build_historical_server_summary_legacy_snapshot_payload()` para conservar `context`, `items`, `summary_basis`, `weekly_ranking_window_days` y `legacy_endpoint_policy`.
  - Si no hay snapshot, devuelve JSON controlado con `items: []` y metadata de snapshot missing, sin RCON live ni fallback runtime pesado.
- `backend/tests/test_historical_snapshot_refresh.py`
  - Cubre que `comunidad-hispana-01` no entra en `get_rcon_historical_read_model()` ni `list_historical_server_summaries()`.
  - Cubre que `comunidad-hispana-02` sigue usando el mismo fast-path.
  - Mantiene cobertura de `all-servers` tras `TASK-229`.
- `docs/FULL_APPLICATION_REQUEST_AUDIT.md`
  - Documenta el estado post-fix de `TASK-230`.
- `docs/PERFORMANCE_PUBLIC_QUERY_AUDIT.md`
  - Actualiza la politica de `/api/historical/server-summary?server=<scope>` como wrapper legacy sobre snapshot read-only.

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
- `cd backend; python -m unittest tests.test_historical_snapshot_refresh`: OK, 17 tests.
- `cd backend; python -m unittest tests.test_current_match_payload tests.test_rcon_admin_log_storage tests.test_historical_snapshot_refresh`: OK, 24 tests.

Auditoria de produccion pendiente tras redeploy:

```powershell
python .\scripts\audit_public_requests.py --base-url https://comunidadhll.devzamode.es --timeout 30 --output tmp\full_audit_after_task230.json
```

## Outcome

El endpoint legacy de resumen historico por servidor queda alineado con el path rapido de snapshots ya usado por `historico.html`. CH01, CH02 y `all-servers` evitan RCON live, scoreboard externo, inicializaciones de storage y fallbacks runtime pesados en lectura publica.

No se cambiaron hosts, puertos, `27001`, variables de entorno ni configuracion de servidores. No se tocaron frontend, assets, SVGs, imagenes fisicas, `ai/system-metrics.md` ni `tmp/`.

## Change Budget

- Archivos de codigo modificados: 2.
- Documentacion actualizada: 3 archivos.
- Sin cambios en frontend ni configuracion.
