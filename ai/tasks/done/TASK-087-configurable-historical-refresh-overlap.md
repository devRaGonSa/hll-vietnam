# TASK-087-configurable-historical-refresh-overlap

## Goal
Hacer configurable la ventana de solape del refresh historico para permitir pasadas manuales de 24h, 48h o mas sobre todos los servidores sin recurrir a un bootstrap grande innecesario.

## Context
La operativa actual del historico tiene dos limites practicos:
- el refresh incremental del historico base relee solo una ventana corta reciente
- el worker de player-events V2 tambien corta demasiado pronto para recuperar huecos recientes de forma controlada

Esto complica recuperar faltantes reales de los ultimos 1-3 dias, por ejemplo cuando faltan datos desde el lunes en uno o varios servidores.

La solucion inmediata no es RCON historico, sino exponer una ventana de solape configurable para:
- `historical_ingestion refresh`
- `player_event_worker refresh`

## Steps
1. Revisar el flujo actual de cutoff y solape en:
   - `backend/app/historical_ingestion.py`
   - `backend/app/historical_storage.py`
   - `backend/app/player_event_worker.py`
   - `backend/app/player_event_storage.py`
   - `backend/app/config.py`
2. Añadir configuracion explicita para el solape temporal del refresh, manteniendo compatibilidad hacia atras:
   - `HLL_HISTORICAL_REFRESH_OVERLAP_HOURS`
   - `HLL_PLAYER_EVENT_REFRESH_OVERLAP_HOURS`
3. Exponer tambien override por CLI en ambos comandos:
   - `python -m app.historical_ingestion refresh --overlap-hours 48`
   - `python -m app.player_event_worker refresh --overlap-hours 48`
4. Mantener el comportamiento por defecto actual o equivalente si el operador no pasa override.
5. Asegurar que el refresh global sin `--server` recorre los tres servidores historicos ya registrados.
6. Documentar en README el runbook operativo para:
   - pasada manual de 48 horas
   - pasada de validacion por un solo servidor
   - recomposicion posterior de snapshots
7. Mantener el trabajo limitado al backend y runbook operativo. No tocar UI.

## Files to Read First
- `backend/README.md`
- `backend/app/historical_ingestion.py`
- `backend/app/historical_storage.py`
- `backend/app/player_event_worker.py`
- `backend/app/player_event_storage.py`
- `backend/app/config.py`

## Expected Files to Modify
- `backend/app/historical_ingestion.py`
- `backend/app/historical_storage.py`
- `backend/app/player_event_worker.py`
- `backend/app/player_event_storage.py`
- `backend/app/config.py`
- `backend/README.md`

## Constraints
- No romper el refresh incremental actual.
- No cambiar el proveedor historico actual por defecto.
- No tocar frontend.
- No introducir dependencias nuevas.
- El override por CLI debe ser opcional.
- La ventana por defecto debe seguir siendo conservadora para no disparar coste innecesario.

## Validation
- Existe soporte de configuracion/env para overlap del historico base.
- Existe soporte de configuracion/env para overlap de player-events.
- Existen flags CLI `--overlap-hours` en ambos comandos.
- Una pasada manual de 48 horas queda documentada para todos los servidores.
- El repositorio queda consistente.

## Change Budget
- Preferir menos de 7 archivos modificados o creados.
- Preferir menos de 260 lineas cambiadas.
