# TASK-105-historical-storage-read-only-hardening

## Goal
Eliminar los bloqueos `database is locked` en las rutas de lectura del histórico separando correctamente:
- inicialización/migración/seed con side effects
- lecturas read-only normales del histórico

## Context
Las pruebas reales han demostrado que una lectura de `build_historical_server_summary_payload(...)` puede fallar con:
`sqlite3.OperationalError: database is locked`
incluso con `historical-runner` y `rcon-historical-worker` parados.

La causa observada es que `historical_storage` sigue:
- usando conexión writer en `_connect()`
- llamando a `initialize_historical_storage()` desde rutas de lectura
- ejecutando seed/init/normalización antes de leer

Eso hace que una ruta conceptualmente read-only siga comportándose como writer.

## Scope
Backend solamente. Sin cambios en frontend.

## Steps
1. Auditar:
   - `backend/app/historical_storage.py`
   - `backend/app/sqlite_utils.py`
   - cualquier capa relacionada que abra SQLite para histórico
2. Separar claramente:
   - path de inicialización/migración/seed
   - path read-only de consultas históricas
3. Introducir una conexión read-only o no-writer para las consultas históricas cuando sea viable.
4. Evitar que funciones como:
   - `list_historical_server_summaries`
   - `list_recent_historical_matches`
   - `get_historical_player_profile`
   - leaderboards y consultas relacionadas
   ejecuten side effects de init/seed en runtime normal de lectura.
5. Mantener compatibilidad con las rutas writer ya existentes.
6. Actualizar README/runbook para dejar claro el comportamiento read-only vs writer.

## Constraints
- No romper migraciones/init cuando realmente hagan falta.
- No romper writers históricos existentes.
- No volver a introducir `database is locked` por rutas de lectura.
- No tocar frontend.

## Validation
- Las lecturas históricas dejan de usar un path writer con side effects.
- La lectura de summary/recent/profile/leaderboards funciona con menor riesgo de lock.
- La repo queda consistente.

## Expected Files
- `backend/app/historical_storage.py`
- `backend/app/sqlite_utils.py`
- `backend/README.md`
- otros archivos backend solo si son estrictamente necesarios

## Outcome
- Separado el path writer de inicializacion/migracion/seed del path read-only de consultas historicas.
- Las lecturas de `historical_storage.py` ya no llaman a `initialize_historical_storage()` en runtime normal.
- Cuando el SQLite historico no existe todavia, las lecturas devuelven defaults vacios/estables sin crear archivo.
- Cuando el SQLite existe, las lecturas usan `connect_sqlite_readonly(..., mode=ro)` con `busy_timeout`.
- Se mantuvo compatibilidad con las rutas writer existentes.

## Validation Notes
- `python -m py_compile backend\\app\\historical_storage.py backend\\app\\sqlite_utils.py`
- Script Python de validacion local contra `backend/data/task-105-validation/historical-test.sqlite3`:
  - verifico que `summary`, `recent`, `profile`, `leaderboards` y helpers read-only no crean el SQLite si no existe
  - verifico que `initialize_historical_storage()` sigue creando el SQLite y deja las lecturas operativas
- `git diff --name-only`
