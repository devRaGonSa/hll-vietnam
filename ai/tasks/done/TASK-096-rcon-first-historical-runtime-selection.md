# TASK-096-rcon-first-historical-runtime-selection

## Goal
Hacer que el histórico backend funcione realmente en modo RCON-first en runtime, con fallback automático, observable y seguro a public-scoreboard/CRCON cuando RCON falle o no soporte una operación concreta.

## Context
Hoy la repo ya tiene:
- live RCON-first con fallback a A2S
- captura prospectiva RCON
- read model histórico RCON parcial
- histórico clásico por public-scoreboard/CRCON
Pero el runtime histórico aún no se comporta como una política RCON-first completa.

## Steps
1. Auditar la selección histórica actual en:
   - `backend/app/data_sources.py`
   - `backend/app/payloads.py`
   - `backend/app/historical_ingestion.py`
   - `backend/app/historical_runner.py`
   - `backend/app/rcon_historical_read_model.py`
2. Introducir arbitraje histórico explícito:
   - intento primario por RCON
   - fallback a public-scoreboard/CRCON si:
     - RCON falla
     - RCON no tiene cobertura
     - RCON no soporta esa operación concreta
3. Asegurar trazabilidad en payloads:
   - `primary_source`
   - `selected_source`
   - `fallback_used`
   - `fallback_reason`
   - `source_attempts`
4. Ajustar el runtime y los defaults para que la política efectiva del stack sea coherente con histórico RCON-first.
5. Mantener compatibilidad con el histórico clásico sin romper snapshots ni workers existentes.
6. Actualizar `backend/README.md` y runbook para que el comportamiento real quede claro.

## Constraints
- No romper live RCON-first ya existente.
- No eliminar public-scoreboard/CRCON.
- No degradar el request path HTTP en latencia o estabilidad de forma evitable.
- No fingir soporte RCON en operaciones que todavía no están cubiertas.

## Validation
- `/health` y/o la metadata funcional relevante reflejan una política histórica RCON-first coherente.
- Los endpoints históricos compatibles intentan RCON primero.
- Cuando RCON no sirve, el fallback a public-scoreboard/CRCON es observable y claro.
- La repo queda consistente.

## Expected Files
- `backend/app/data_sources.py`
- `backend/app/payloads.py`
- `backend/app/historical_ingestion.py`
- `backend/app/historical_runner.py`
- `backend/app/rcon_historical_read_model.py`
- `backend/app/config.py`
- `backend/README.md`
- `docker-compose.yml` si hace falta
