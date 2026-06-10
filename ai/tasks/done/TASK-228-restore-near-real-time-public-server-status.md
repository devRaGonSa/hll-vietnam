---
id: TASK-228
title: Restore near-real-time public server status
status: done
type: backend
team: Backend Senior
supporting_teams: []
roadmap_item: foundation
priority: high
---

# TASK-228 - Restore near-real-time public server status

## Goal

Restaurar el comportamiento correcto de la home "Estado actual de servidores" para que `/api/servers` vuelva a servir estado live o casi-live de los servidores cuando la fuente RCON/A2S este disponible:

- mapa actual
- region/servidor
- jugadores
- estado disponible

La ruta no debe depender exclusivamente de snapshots historicos ni devolver `items: []` cuando puede consultar live de forma controlada.

## Context

Tras `TASK-226`, `/api/servers` respondia rapido pero vacio cuando no existian snapshots:

- `source: no-snapshot-available`
- `refresh_attempted: false`
- `refresh_status: cache-only`
- `items: []`

Eso dejaba la home mostrando "Actualizado no disponible" e "Informacion de servidores disponible mas adelante". Ese resultado no es aceptable para una seccion cuyo contrato es estado actual/casi actual.

## Files Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/backend-senior.md`
- `backend/README.md`
- `backend/app/routes.py`
- `backend/app/payloads.py`
- `backend/app/data_sources.py`
- `backend/app/providers/rcon_provider.py`
- `backend/app/collector.py`
- `backend/tests/test_current_match_payload.py`

## Call Chain Analysis

Cadena frontend/backend:

1. La home usa `frontend/assets/js/main.js`.
2. Ese JS consulta `/api/servers` para renderizar las tarjetas de estado.
3. `backend/app/routes.py` mapea `/api/servers` a `build_servers_payload()`.
4. `build_servers_payload()` lee `list_latest_snapshots()` como ultimo estado conocido.
5. Antes de `TASK-226`, si no habia cache o estaba stale, llamaba `_try_collect_real_time_snapshot()`.
6. `_try_collect_real_time_snapshot()` usa `get_live_data_source().collect_snapshots(...)`.
7. Con `HLL_BACKEND_LIVE_DATA_SOURCE=rcon`, la fuente efectiva es RCON-first con fallback A2S controlado.

## Root Cause

`TASK-226` cambio `build_servers_payload()` a modo `cache-only` estricto:

- dejo de llamar `_try_collect_real_time_snapshot()` desde `/api/servers`.
- marco `refresh_attempted: false` siempre.
- devolvia `items: []` cuando no habia snapshot persistido.

Ese cambio arreglo latencia de request, pero rompio el contrato funcional de la home cuando no hay cache caliente.

## Changes

- `backend/app/payloads.py`
  - Restaura la politica near-real-time:
    - si hay snapshot fresco, sirve cache sin refresh.
    - si no hay snapshot o esta stale, intenta refresh live.
    - si live devuelve items, responde con `real-time-rcon-refresh`, `real-time-a2s-fallback` o equivalente.
    - si live falla, devuelve snapshot stale si existe.
    - si live falla y no hay snapshot, responde `items: []` con error controlado y metadata de fallback.
  - `_try_collect_real_time_snapshot()` captura excepciones y evita 500.
  - El refresh publico usa timeout interno corto `PUBLIC_SERVER_STATUS_TIMEOUT_SECONDS = 2.5` sin cambiar variables de entorno ni configuracion RCON.
- `backend/app/data_sources.py`
  - Extiende el contrato live para aceptar `timeout_seconds` opcional.
  - Propaga ese timeout a RCON-first y A2S cuando la llamada publica lo solicita.
- `backend/app/providers/rcon_provider.py`
  - Propaga `timeout_seconds` opcional a `query_live_server_sample()`.
  - Las llamadas que no pasan timeout siguen usando `HLL_BACKEND_RCON_TIMEOUT_SECONDS`.
- `backend/tests/test_current_match_payload.py`
  - Ajusta el test de `/api/servers` de `cache-only` a near-real-time.
  - Cubre refresh live cuando no hay cache.
  - Cubre respuesta controlada si live falla sin cache.
  - Cubre fallback a snapshot stale si live falla con cache existente.
- `docs/FULL_APPLICATION_REQUEST_AUDIT.md`
  - Documenta el estado post-fix de `TASK-228`.
- `docs/PERFORMANCE_PUBLIC_QUERY_AUDIT.md`
  - Actualiza `/api/servers` como near-real-time controlado en vez de cache-only.

## Validation

Validaciones ejecutadas:

```powershell
python -m compileall backend/app
cd backend
python -m unittest tests.test_current_match_payload
python -m unittest tests.test_current_match_payload tests.test_rcon_admin_log_storage tests.test_historical_snapshot_refresh
```

Resultados:

- `python -m compileall backend/app`: OK.
- `cd backend; python -m unittest tests.test_current_match_payload`: OK, 7 tests.
- `cd backend; python -m unittest tests.test_current_match_payload tests.test_rcon_admin_log_storage tests.test_historical_snapshot_refresh`: OK, 20 tests.

Auditoria local:

- No se ejecuto porque `http://127.0.0.1:8000/health` no respondio desde el host.

Comandos de validacion de produccion tras redeploy:

```powershell
$base = "https://comunidadhll.devzamode.es"

Invoke-WebRequest "$base/api/servers" |
  Select-Object -ExpandProperty Content

Invoke-WebRequest "$base/api/servers/latest" |
  Select-Object -ExpandProperty Content

Invoke-WebRequest "$base/api/servers/history" |
  Select-Object -ExpandProperty Content

python .\scripts\audit_public_requests.py --base-url https://comunidadhll.devzamode.es --timeout 30 --filter servers --output tmp\task228_servers_audit_after.json
```

## Outcome

`/api/servers` vuelve a intentar estado live/casi-live de forma controlada cuando no hay cache o el cache esta vencido. Si RCON/A2S responde, la home recibe items reales. Si RCON/A2S no responde en el entorno de pruebas, el endpoint devuelve JSON controlado y no debe bloquear 30 s ni devolver 500 vacio.

## Constraints Confirmed

- No se cambio `27001`.
- No se cambiaron hosts ni puertos RCON.
- No se cambio `127.0.0.1`.
- No se cambiaron variables de entorno de servidores.
- No se cambio configuracion de servidores.
- No se tocaron player search/profile/historical detail.
- No se tocaron current-match/kills ni current-match/players salvo por tests compartidos.
- No se reactivo Elo/MMR.
- No se reintrodujo Comunidad Hispana #03.
- No se toco frontend.
- No se tocaron assets, SVGs ni imagenes fisicas.
- No se toco `frontend/assets/img/weapons/`.
- No se toco `frontend/assets/img/clans/`.
- No se toco `ai/system-metrics.md`.
- No se incluyo `tmp/`.

## Risks

- El refresh live sigue siendo sincronico y consulta targets configurados. El timeout publico corto reduce el riesgo de 30 s, pero con varios targets o un servidor que responde parcialmente puede haber latencia acumulada.
- No se persiste el snapshot live desde el GET publico para evitar DDL/inicializaciones pesadas en la lectura publica. `/api/servers/latest` y `/api/servers/history` pueden seguir vacios hasta que un proceso de captura/persistencia actualice almacenamiento.
- La validacion final de que la home muestra servidores requiere redeploy en el entorno donde RCON/live este disponible.
