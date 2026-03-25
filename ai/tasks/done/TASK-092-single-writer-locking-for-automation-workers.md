# TASK-092-single-writer-locking-for-automation-workers

## Goal
Imponer una coordinacion de single-writer entre todos los procesos del backend que escriben sobre el mismo SQLite compartido, evitando colisiones entre automatizaciones y ejecuciones manuales y sustituyendo errores opacos de `database is locked` por una coordinacion controlada y mensajes claros.

## Context
Actualmente pueden coincidir sobre el mismo volumen `/app/data`:
- `historical-runner`
- `player_event_worker`
- `rcon-historical-worker`
- ejecuciones manuales via `docker compose exec backend ...`

Aunque WAL y busy_timeout ayudan, no garantizan una operativa limpia si varios writers largos arrancan a la vez. Hace falta una politica de exclusion mutua a nivel de proceso/job, no solo a nivel SQLite.

## Scope
Backend y orquestacion minima/documentacion. Sin cambios en frontend.

## Desired Design
Implementar un unico lock compartido para todos los writers que tocan el mismo SQLite.

Ese lock debe:
- vivir bajo el storage compartido en `/app/data` o una ruta derivada del `storage_path`
- ser comun para:
  - `app.historical_runner`
  - `app.historical_ingestion`
  - `app.player_event_worker`
  - `app.rcon_historical_worker`
- adquirirse al principio de cada run writer-oriented
- liberarse siempre aunque haya excepcion
- incluir metadata visible del holder:
  - proceso/comando
  - started_at
  - host/container si es viable
- tener espera configurable con timeout y poll interval
- fallar con error claro cuando no pueda adquirir el lock dentro del timeout
- evitar dependencias nuevas si es posible

## Steps
1. Crear una utilidad comun de writer lock compartido para el backend.
2. Aplicarla a:
   - `historical_ingestion` manual
   - `historical_runner`
   - `player_event_worker`
   - `rcon_historical_worker`
3. Asegurarte de que el lock cubre la ejecucion writer-oriented completa, no solo una sentencia aislada.
4. Exponer configuracion/env para:
   - lock timeout
   - poll interval
5. Añadir mensajes de error/estado legibles cuando el lock este ocupado.
6. Mantener las rutas HTTP read-only fuera de este lock.
7. Actualizar `docker-compose.yml` solo si es necesario para dejar la operativa alineada.
8. Actualizar `backend/README.md` con runbook claro:
   - que writers comparten lock
   - como hacer una pasada manual
   - que pasa si el lock esta ocupado
   - como convivir con automatizaciones sin parar contenedores salvo necesidad excepcional

## Constraints
- No tocar frontend.
- No convertir esto en un rediseño total del scheduler.
- No romper los workers ya existentes.
- No bloquear las rutas HTTP de lectura.
- No ampliar el alcance funcional del read model RCON.
- Debe quedar claro que la solucion principal es single-writer coordination, no solo subir retries.

## Validation
- Existe un lock compartido real para los writers.
- `historical_runner`, `historical_ingestion`, `player_event_worker` y `rcon_historical_worker` lo usan.
- Si dos writers coinciden, no se produce un fallo opaco de SQLite; hay espera controlada o error claro de lock ocupado.
- `python -m compileall app` pasa.
- Las CLIs principales siguen respondiendo con `--help`.
- La repo queda consistente.

## Expected Files
- uno o varios utilitarios nuevos bajo `backend/app/`
- `backend/app/historical_runner.py`
- `backend/app/historical_ingestion.py`
- `backend/app/player_event_worker.py`
- `backend/app/rcon_historical_worker.py`
- `docker-compose.yml` si hace falta
- `backend/README.md`
