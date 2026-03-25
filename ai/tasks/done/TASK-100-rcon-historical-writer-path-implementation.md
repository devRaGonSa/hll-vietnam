# TASK-100-rcon-historical-writer-path-implementation

## Goal
Implementar un writer path histórico real por RCON para que la ingesta histórica intente RCON primero y use scoreboard/public-scoreboard solo como fallback.

## Context
La repo ya tiene:
- live RCON-first
- captura prospectiva RCON
- read model histórico RCON parcial
- ingesta histórica clásica por scoreboard
Pero todavía no existe un writer path histórico real por RCON integrado en `historical_ingestion`.

## Steps
1. Auditar:
   - `backend/app/data_sources.py`
   - `backend/app/historical_ingestion.py`
   - `backend/app/rcon_historical_worker.py`
   - `backend/app/rcon_historical_storage.py`
   - `backend/app/rcon_historical_read_model.py`
   - cualquier capa necesaria de modelos/storage
2. Definir qué significa “writer path histórico RCON” con la telemetría real actual:
   - qué puede alimentar
   - qué estructura persistida necesita
   - cómo se integra con el ingestion flow existente
3. Implementar una vía writer-oriented RCON que permita a `historical_ingestion` intentar primero RCON.
4. Si RCON falla o no cubre la operación concreta, hacer fallback controlado a scoreboard/public-scoreboard.
5. Mantener trazabilidad explícita:
   - primary_source
   - selected_source
   - fallback_used
   - fallback_reason
   - source_attempts
6. No romper la compatibilidad con snapshots ni con rebuilds posteriores.
7. Actualizar README/runbook explicando el nuevo writer path real.

## Constraints
- No fingir cobertura histórica RCON que no exista.
- No eliminar scoreboard como fallback.
- No romper live RCON-first.
- No romper el locking compartido.

## Validation
- `historical_ingestion` intenta RCON primero.
- Cuando RCON falla o no soporta la operación, hace fallback explícito a scoreboard.
- La salida del comando deja claro qué fuente se usó realmente.
- El repositorio queda consistente.

## Expected Files
- `backend/app/data_sources.py`
- `backend/app/historical_ingestion.py`
- archivos backend necesarios para writer path RCON
- `backend/README.md`
