# TASK-071-public-scoreboard-provider-adapter

## Goal
Adaptar la fuente actual public-scoreboard al nuevo contrato de proveedor para que siga siendo la fuente estándar en desarrollo sin romper el comportamiento existente.

## Context
Una vez exista la abstracción de fuente, hay que mover la lógica actual a un proveedor explícito de tipo public-scoreboard. Eso permitirá mantener dev estable mientras se prepara RCON para producción.

## Steps
1. Revisar la lógica actual que usa scoreboard/CRCON público.
2. Encapsularla dentro del proveedor public-scoreboard compatible con la nueva abstracción.
3. Asegurar que desarrollo sigue funcionando con la misma semántica actual.
4. Mantener el mismo resultado en:
   - ingestión histórica
   - snapshots
   - estado actual de servidores
5. Reducir duplicaciones y dejar clara la responsabilidad del proveedor.
6. Actualizar documentación mínima.
7. No implementar todavía lógica RCON en esta task.
8. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- backend/README.md
- backend/app/config.py
- backend/app/historical_ingestion.py
- backend/app/payloads.py
- backend/app/routes.py
- backend/app/source_provider.py
- docs/historical-crcon-source-discovery.md

## Expected Files to Modify
- backend/app/historical_ingestion.py
- backend/app/payloads.py
- backend/app/routes.py
- opcionalmente nuevos módulos, por ejemplo:
  - backend/app/providers/public_scoreboard_provider.py
- backend/README.md

## Constraints
- No romper el comportamiento actual en dev.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en encapsular correctamente la fuente actual.

## Validation
- El proveedor public-scoreboard funciona bajo la nueva abstracción.
- El modo desarrollo sigue comportándose como antes.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 5 archivos modificados o creados.
- Preferir menos de 220 líneas cambiadas.

## Outcome
- Se extrajo la logica del proveedor historico actual a `backend/app/providers/public_scoreboard_provider.py`.
- `backend/app/data_sources.py` quedo reducido a contratos y seleccion de proveedor por entorno.
- El comportamiento de desarrollo se mantuvo estable con `public-scoreboard` como proveedor historico por defecto.
- No se introdujo logica RCON en esta task.

## Validation Notes
- `python -m compileall backend/app` completo sin errores tras el refactor.
- La diff quedo limitada al selector de proveedores, el adapter publico y la documentacion minima.
- `backend/app/source_provider.py` no existia; se reutilizo `backend/app/data_sources.py` como punto de seleccion ya introducido en la task anterior.
