# TASK-090-rcon-historical-provider-minimal-read-model

## Goal
Construir una primera capa de lectura historica minima sobre la persistencia prospectiva RCON, sin intentar aun paridad completa con todos los rankings competitivos del historico actual.

## Context
Esta task depende de la task anterior.

Una vez exista captura prospectiva RCON, hace falta una primera capa de lectura util que permita comprobar cobertura real y exponer algo operativo sin mentir sobre la profundidad disponible.

La prioridad aqui no es clonar toda la salida de `public-scoreboard`, sino exponer:
- cobertura
- actividad reciente
- estado del historico RCON disponible
- una base compatible para evolucion posterior

## Steps
1. Implementar una primera version funcional de `RconHistoricalDataSource` basada en datos persistidos, no en consultas RCON on-demand dentro del request path.
2. Definir un read model minimo util para:
   - resumen/cobertura por servidor
   - actividad o sesiones recientes
   - metadata de disponibilidad y frescura
3. Exponer un camino de seleccion seguro por `HLL_BACKEND_HISTORICAL_DATA_SOURCE=rcon` sin romper el modo `public-scoreboard`.
4. Mantener la degradacion controlada cuando falten metricas:
   - devolver payload coherente
   - documentar que contratos quedan soportados y cuales no todavia
5. Actualizar README y runbook para aclarar:
   - que endpoints funcionan con la lectura RCON minima
   - que endpoints siguen dependiendo de `public-scoreboard`
6. No intentar aun:
   - weekly/monthly leaderboards completos
   - MVP V1/V2 completos
   - equivalencia total con `historico.html`

## Files to Read First
- `docs/rcon-historical-ingestion-design.md`
- `backend/README.md`
- `backend/app/data_sources.py`
- `backend/app/payloads.py`
- `backend/app/routes.py`
- los archivos creados en la task anterior para captura prospectiva RCON

## Expected Files to Modify
- `backend/app/data_sources.py`
- `backend/app/payloads.py`
- `backend/app/routes.py`
- uno o varios archivos nuevos bajo `backend/app/` para read model RCON historico
- `backend/README.md`

## Constraints
- No sustituir aun el historico actual completo.
- No tocar frontend.
- No exponer contratos falsos o semicompletos como si fueran paridad total.
- La lectura HTTP debe seguir siendo fast-path de solo lectura sobre persistencia local.
- Si un endpoint no queda soportado por la capa minima, debe quedar documentado y degradar de forma clara.

## Validation
- `HLL_BACKEND_HISTORICAL_DATA_SOURCE=rcon` deja una lectura historica minima operativa y documentada.
- El backend no rompe el modo `public-scoreboard`.
- La documentacion deja claro el alcance real de esta primera capa de lectura.
- El repositorio queda consistente.

## Change Budget
- Preferir menos de 7 archivos modificados o creados.
- Preferir menos de 320 lineas cambiadas.
