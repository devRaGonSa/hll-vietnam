# TASK-091-sqlite-writer-hardening

## Goal
Unificar y endurecer la politica de conexion SQLite para todas las rutas de escritura del backend que comparten la misma base de datos, reduciendo contencion evitable y haciendo el comportamiento consistente entre historico base, player-events y captura prospectiva RCON.

## Context
La repo ya tiene varias rutas de escritura sobre el mismo SQLite:
- historico base CRCON
- player-event ledger V2
- captura prospectiva RCON
- snapshots y runners asociados

Parte del storage ya usa timeout/WAL/busy_timeout, pero no toda la capa de persistencia lo hace de forma uniforme. Antes de cualquier politica de locking entre procesos, hace falta que todas las conexiones writer-capable usen una configuracion SQLite coherente.

## Scope
Backend solamente. Sin cambios en frontend.

## Steps
1. Auditar todas las funciones `_connect()` o equivalentes que abren SQLite en:
   - `backend/app/historical_storage.py`
   - `backend/app/player_event_storage.py`
   - `backend/app/rcon_historical_storage.py`
   - cualquier otro storage writer-capable relacionado
2. Crear una utilidad compartida y pequena para abrir conexiones SQLite con politica comun de escritura.
3. La politica comun debe incluir como minimo:
   - `timeout` explicito
   - `PRAGMA foreign_keys = ON`
   - `PRAGMA journal_mode = WAL`
   - `PRAGMA busy_timeout`
   - `row_factory = sqlite3.Row`
4. Reusar esa utilidad en todas las capas de persistencia con escritura que comparten el mismo DB.
5. Mantener compatibilidad con la ruta actual del storage y sin cambiar contratos HTTP.
6. Actualizar README/runbook backend con una nota breve sobre la politica SQLite usada por writers.

## Constraints
- No tocar frontend.
- No cambiar la semantica funcional de los endpoints.
- No cambiar el proveedor historico por defecto.
- No meter dependencias nuevas salvo necesidad extrema.
- Mantener la utilidad pequeña y facil de leer.

## Validation
- Todas las capas writer-capable relevantes comparten la misma politica SQLite.
- `python -m compileall app` pasa.
- Las CLIs principales siguen arrancando con `--help`.
- La repo queda consistente.

## Expected Files
- `backend/app/historical_storage.py`
- `backend/app/player_event_storage.py`
- `backend/app/rcon_historical_storage.py`
- un util compartido nuevo bajo `backend/app/` si hace falta
- `backend/README.md`
