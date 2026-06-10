---
id: TASK-227
title: Fix current-match kills and players timeouts
status: done
type: backend
team: Backend Senior
supporting_teams: []
roadmap_item: foundation
priority: high
---

# TASK-227 - Fix current-match kills and players timeouts

## Goal

Corregir especificamente los endpoints publicos secundarios de partida actual que seguian bloqueando tras `TASK-226`:

- `/api/current-match/kills`
- `/api/current-match/players`

El objetivo no es reconectar RCON ni cambiar configuracion, sino evitar que estos endpoints publicos entren en inicializacion o lecturas bloqueantes y asegurar degradacion JSON controlada cuando el read model no este disponible.

## Context

Validacion real tras `TASK-226` contra produccion:

```powershell
python .\scripts\audit_public_requests.py --base-url https://comunidadhll.devzamode.es --timeout 30 --filter current-match --output tmp\task226_current_match_audit_after.json
```

Resultados relevantes:

- `current-match-comunidad-hispana-01`: OK 200, 2314 ms.
- `current-match-kills-comunidad-hispana-01`: CRITICAL, timeout 30026 ms.
- `current-match-players-comunidad-hispana-01`: CRITICAL, timeout 30079 ms.
- `current-match-comunidad-hispana-02`: OK 200, 2265 ms.
- `current-match-kills-comunidad-hispana-02`: CRITICAL, timeout 30050 ms.
- `current-match-players-comunidad-hispana-02`: CRITICAL, 200 pero 26095 ms, `fallback=True`.

Tambien se valido que `/api/servers` ya esta OK en unos 82 ms y que `TASK-225` sigue OK para player search/profile y historical match detail. Esta task no toca esas rutas.

## Files Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/backend-senior.md`
- `backend/README.md`
- `backend/app/routes.py`
- `backend/app/payloads.py`
- `backend/app/rcon_admin_log_storage.py`
- `backend/app/postgres_rcon_storage.py`
- `backend/tests/test_current_match_payload.py`

## Call Chain Analysis

Rutas exactas en `backend/app/routes.py`:

- `/api/current-match/kills` valida `server`, `limit`, `since_event_id` y llama `build_current_match_kill_feed_payload(server_slug=..., limit=..., since_event_id=...)`.
- `/api/current-match/players` valida `server` y llama `build_current_match_player_stats_payload(server_slug=...)`.
- `/api/current-match` general llama `build_current_match_payload(server_slug=...)`.

Cadena del endpoint general:

1. `resolve_get_payload("/api/current-match?...")`
2. `build_current_match_payload()`
3. `_query_current_match_rcon_sample()` intenta una muestra RCON de sesion.
4. Si falla, cae a `build_servers_payload()`.
5. Tras `TASK-226`, `build_servers_payload()` es cache/snapshot-only y no refresca RCON/A2S en el GET publico.

Cadena de kills:

1. `resolve_get_payload("/api/current-match/kills?...")`
2. `build_current_match_kill_feed_payload()`
3. `list_current_match_kill_feed(server_key=origin.slug, ensure_storage=False)`
4. En PostgreSQL, el codigo llamaba `connect_postgres_compat()` sin argumentos.
5. `connect_postgres_compat()` tiene `initialize=True` por defecto.
6. `initialize_postgres_rcon_storage()` ejecutaba bootstrap/DDL antes de abrir la lectura.

Cadena de players:

1. `resolve_get_payload("/api/current-match/players?...")`
2. `build_current_match_player_stats_payload()`
3. `list_current_match_player_stats(server_key=origin.slug, ensure_storage=False)`
4. En PostgreSQL, el codigo llamaba `connect_postgres_compat()` sin argumentos.
5. `connect_postgres_compat()` inicializaba storage por defecto igual que kills.

## Root Cause

`TASK-226` paso `ensure_storage=False` desde los payloads publicos, pero en la rama PostgreSQL de `backend/app/rcon_admin_log_storage.py` ese flag no se propagaba a `connect_postgres_compat()`.

Resultado: en produccion con `HLL_BACKEND_DATABASE_URL`, kills/players seguian ejecutando `initialize_postgres_rcon_storage()` durante el GET publico. Esa inicializacion/DDL en el request path explica la diferencia frente a `/api/current-match` general: el endpoint general no pasa por AdminLog ni por `connect_postgres_compat()` para construir kills/players; usa muestra RCON de sesion y fallback a snapshot de servidores.

No se encontro necesidad de cambiar hosts RCON, puertos, `27001`, `127.0.0.1`, variables de entorno ni configuracion de servidores.

## Changes

- `backend/app/rcon_admin_log_storage.py`
  - `list_current_match_kill_feed()` ahora llama `connect_postgres_compat(initialize=ensure_storage)`.
  - `list_current_match_player_stats()` ahora llama `connect_postgres_compat(initialize=ensure_storage)`.
  - Con `ensure_storage=False`, las lecturas publicas de AdminLog no inicializan PostgreSQL.
- `backend/tests/test_current_match_payload.py`
  - Anade tests de regresion para kills y players verificando que la ruta PostgreSQL read-only llama `connect_postgres_compat(initialize=False)`.
- `docs/FULL_APPLICATION_REQUEST_AUDIT.md`
  - Documenta el estado post-fix de `TASK-227`.
- `docs/PERFORMANCE_PUBLIC_QUERY_AUDIT.md`
  - Actualiza la nota de arquitectura de lectura publica para reflejar la correccion real de PostgreSQL read-only.

## Validation

Validaciones ejecutadas:

```powershell
python -m compileall backend/app
cd backend
python -m unittest tests.test_current_match_payload
cd backend
python -m unittest tests.test_current_match_payload tests.test_rcon_admin_log_storage tests.test_historical_snapshot_refresh
```

Resultados:

- `python -m compileall backend/app`: OK.
- `cd backend; python -m unittest tests.test_current_match_payload`: OK, 5 tests.
- `cd backend; python -m unittest tests.test_current_match_payload tests.test_rcon_admin_log_storage tests.test_historical_snapshot_refresh`: OK, 18 tests.

Auditoria HTTP local:

- No se ejecuto auditoria local porque `http://127.0.0.1:8000/health` no respondio desde el host.

Comando exacto para validar produccion tras redeploy:

```powershell
python .\scripts\audit_public_requests.py --base-url https://comunidadhll.devzamode.es --timeout 30 --filter current-match --output tmp\task227_current_match_audit_after.json
```

## Outcome

La ruta publica secundaria de AdminLog queda realmente read-only en PostgreSQL cuando los payloads llaman con `ensure_storage=False`. Si el read model no existe o falla, los payloads ya capturan la excepcion y devuelven `status: ok`, `items: []`, `fallback_used: true` y `fallback_reason` controlado, sin 500 vacio.

## Constraints Confirmed

- No se cambio `27001`.
- No se cambiaron hosts ni puertos RCON.
- No se cambio `127.0.0.1`.
- No se cambiaron variables de entorno de servidores.
- No se cambio configuracion de servidores.
- No se toco `/api/servers`.
- No se tocaron player search/profile/historical detail.
- No se reactivo Elo/MMR.
- No se reintrodujo Comunidad Hispana #03.
- No se toco frontend.
- No se tocaron assets, SVGs ni imagenes fisicas.
- No se toco `frontend/assets/img/weapons/`.
- No se toco `frontend/assets/img/clans/`.
- No se toco `ai/system-metrics.md`.
- No se incluyo `tmp/`.

## Risks

- Si PostgreSQL esta caido o la apertura de conexion queda bloqueada por red/DNS, el endpoint aun depende del timeout de conexion de PostgreSQL. Esta task elimina el bootstrap/DDL publico identificado, no introduce cambios de configuracion ni pooling.
- `/api/current-match` general sigue con muestra RCON directa por diseno actual; no fue parte de esta task porque la auditoria post-226 lo midio OK en unos 2.3 s.
- La confirmacion final de latencia requiere redeploy y auditoria de produccion.
