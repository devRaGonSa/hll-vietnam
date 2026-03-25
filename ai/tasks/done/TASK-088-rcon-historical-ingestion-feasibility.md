# TASK-088-rcon-historical-ingestion-feasibility

## Goal
Aterrizar con precision si la repo puede soportar una ingesta historica por RCON y, en caso afirmativo, definir una arquitectura minima, incremental y defendible sin asumir capacidades que hoy no estan probadas.

## Context
La repo ya tiene:
- proveedor live por RCON
- seleccion de `historical_data_source`
- placeholder `RconHistoricalDataSource`

Pero todavia no existe una implementacion historica real por RCON. Antes de abrir trabajo de implementacion, hace falta una auditoria tecnica que determine:
- que datos puede dar realmente el cliente RCON actual
- si permiten reconstruccion historica, solo captura prospectiva o solo telemetria parcial
- que huecos deben mantenerse temporalmente en `public-scoreboard`
- que contrato minimo puede exponerse sin vender capacidades inexistentes

## Steps
1. Revisar la capa actual de seleccion de proveedores y el adapter RCON existente.
2. Auditar el cliente RCON y documentar exactamente:
   - comandos soportados hoy
   - forma del payload disponible hoy
   - frecuencia de captura razonable
   - si hay o no base para historico real de partidas cerradas
3. Redactar una decision tecnica clara con una de estas salidas:
   - no viable con el cliente actual
   - viable solo para captura prospectiva
   - viable para una capa historica parcial
4. Diseñar la arquitectura minima recomendada:
   - almacenamiento
   - workers
   - checkpoints
   - compatibilidad con `public-scoreboard`
   - politica de degradacion si faltan metricas
5. Dejar una propuesta de fases realista:
   - fase 1: captura prospectiva
   - fase 2: lectura operativa minima
   - fase 3: metricas competitivas si la senal lo permite
6. Actualizar README para reflejar el estado real y evitar ambiguedad sobre “historico por RCON”.

## Files to Read First
- `backend/README.md`
- `backend/app/data_sources.py`
- `backend/app/providers/rcon_provider.py`
- `backend/app/rcon_client.py`
- `backend/app/historical_ingestion.py`
- `backend/app/historical_storage.py`
- `backend/app/player_event_worker.py`
- `backend/app/player_event_storage.py`

## Expected Files to Modify
- `docs/rcon-historical-ingestion-design.md`
- `backend/README.md`

## Constraints
- No implementar aun la ingesta historica por RCON.
- No cambiar runtime behavior del backend.
- No tocar frontend.
- No asumir que RCON resuelve backfill retroactivo si eso no esta demostrado.
- Mantener el documento muy concreto y util para una implementacion posterior.

## Validation
- Existe un documento de diseno con conclusion clara.
- El README deja claro que parte esta implementada y cual no.
- No se introducen cambios de comportamiento en produccion o desarrollo.
- El repositorio queda consistente.

## Change Budget
- Preferir menos de 3 archivos modificados o creados.
- Preferir menos de 220 lineas cambiadas.
