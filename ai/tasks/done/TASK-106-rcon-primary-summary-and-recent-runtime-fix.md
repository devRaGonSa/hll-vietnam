# TASK-106-rcon-primary-summary-and-recent-runtime-fix

## Goal
Corregir la frontera runtime para que `historical server summary` y `recent historical matches` usen realmente la capa RCON-backed como fuente primaria cuando haya cobertura suficiente, dejando `public-scoreboard` solo como fallback explicito.

## Context
Las pruebas reales iniciales del sistema habian mostrado que:
- `build_historical_server_summary_payload(...)`
- `build_recent_historical_matches_payload(...)`

seguian devolviendo en runtime:
- `selected_source = "public-scoreboard"`
- `fallback_used = true`

cuando el objetivo de producto era que, si existe cobertura RCON suficiente, esas rutas fueran realmente RCON-first efectivas y no solo nominales.

## Scope
Backend solamente. Sin cambios en frontend.

## Steps
1. Auditar:
   - `backend/app/payloads.py`
   - `backend/app/rcon_historical_read_model.py`
   - `backend/app/rcon_historical_storage.py`
   - `backend/app/historical_snapshots.py`
   - `backend/app/data_sources.py`
2. Identificar por que `summary` y `recent-matches` seguian seleccionando `public-scoreboard` en las pruebas reales.
3. Corregir la seleccion runtime para que:
   - si hay cobertura/capability RCON suficiente -> `selected_source = "rcon"`
   - si no la hay -> fallback explicito a `public-scoreboard`
4. Mantener trazabilidad clara:
   - `primary_source`
   - `selected_source`
   - `fallback_used`
   - `fallback_reason`
   - `source_attempts`
5. Alinear snapshots o materializaciones si hace falta para que no obliguen a caer innecesariamente al historico clasico.
6. Actualizar README/runbook explicando la frontera exacta de summary/recent.

## Constraints
- No fingir cobertura RCON si no existe.
- No romper endpoints existentes.
- No eliminar `public-scoreboard` como red de seguridad.
- No tocar frontend.

## Validation
- `historical server summary` usa RCON como primario real cuando hay cobertura.
- `recent historical matches` usa RCON como primario real cuando hay cobertura.
- Cuando no haya cobertura, el fallback a `public-scoreboard` sigue siendo explicito y observable.
- La repo queda consistente.

## Expected Files
- `backend/app/payloads.py`
- `backend/app/rcon_historical_read_model.py`
- `backend/app/rcon_historical_storage.py`
- `backend/app/historical_snapshots.py`
- `backend/app/data_sources.py`
- `backend/README.md`
- otros archivos backend solo si son estrictamente necesarios

## Outcome
- Ya existe evidencia runtime real suficiente para considerar cumplido el objetivo funcional de la task.
- Para `server_slug = "comunidad-hispana-01"`:
  - `build_historical_server_summary_payload(...)` devuelve:
    - `selected_source = "rcon"`
    - `fallback_used = false`
    - `summary_basis = "rcon-competitive-windows"`
  - `build_recent_historical_matches_payload(..., limit=2)` devuelve:
    - `selected_source = "rcon"`
    - `fallback_used = false`
- Esto demuestra que la frontera runtime RCON-first ya funciona con cobertura real para al menos un servidor y que `summary` y `recent-matches` ya no quedan solo en una intencion nominal.
- El fallback a `public-scoreboard` sigue intacto y sigue siendo la degradacion correcta cuando:
  - no hay cobertura RCON suficiente
  - un target falla
  - la capability concreta no puede servirse de forma fiable desde RCON
- `comunidad-hispana-03` sigue teniendo una incidencia separada de `auth/login`, pero eso no invalida el cierre funcional de esta task porque la frontera runtime pedida aqui ya quedo validada con datos reales en al menos un servidor con cobertura.

## Validation Notes
- Cierre administrativo basado en evidencia runtime ya validada y aportada fuera de esta actualizacion.
- No se rehacen pruebas ni se introducen cambios funcionales adicionales para este cierre.
