# TASK-070-data-source-abstraction-for-historical-and-live

## Goal
Introducir una capa de abstracción de fuente de datos para que el backend pueda trabajar con distintas fuentes según entorno sin cambiar el contrato de producto ni la UI.

## Context
El proyecto hoy funciona con una fuente pública basada en scoreboard/CRCON público. Se quiere mantener ese modo para desarrollo, pero preparar producción para funcionar con RCON como fuente principal. Antes de implementar el proveedor RCON, hace falta definir una abstracción clara que desacople el backend de una única fuente.

## Steps
1. Revisar la arquitectura actual de ingestión histórica, snapshots y panel live.
2. Identificar los puntos donde hoy se asume una fuente concreta.
3. Diseñar una interfaz o capa de proveedor de datos para cubrir como mínimo:
   - histórico / ingestión
   - estado actual live de servidores
4. Definir un contrato claro para proveedores de datos, por ejemplo:
   - public-scoreboard provider
   - rcon provider
5. Mantener intactos los contratos de salida del backend hacia la UI.
6. Preparar la selección del proveedor por configuración/entorno.
7. Documentar la arquitectura resultante.
8. No cambiar todavía el producto visible más de lo imprescindible.
9. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- backend/README.md
- backend/app/config.py
- backend/app/historical_ingestion.py
- backend/app/historical_runner.py
- backend/app/payloads.py
- backend/app/routes.py
- backend/app/main.py

## Expected Files to Modify
- backend/app/config.py
- backend/app/historical_ingestion.py
- backend/app/payloads.py
- opcionalmente nuevos módulos, por ejemplo:
  - backend/app/data_sources.py
  - backend/app/source_provider.py
- backend/README.md
- opcionalmente ai/architecture-index.md

## Constraints
- No romper el modo actual de desarrollo.
- No acoplar la UI a una fuente concreta.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en la abstracción de fuente de datos.

## Validation
- Existe una abstracción clara de proveedor de datos.
- El backend puede seleccionar fuente por configuración.
- El flujo actual no se rompe.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 6 archivos modificados o creados.
- Preferir menos de 240 líneas cambiadas.

## Outcome
- Se introdujo `backend/app/data_sources.py` como capa de seleccion y contrato para proveedores live e historicos.
- `historical_ingestion.py` dejo de depender directamente de requests CRCON embebidas y ahora resuelve su proveedor por configuracion.
- `payloads.py` dejo de invocar el colector A2S de forma acoplada y ahora consume un proveedor live seleccionado por entorno.
- Se mantuvieron intactos los contratos HTTP del backend hacia la UI.
- Quedaron preparadas las rutas de seleccion para `public-scoreboard`, `a2s` y el placeholder futuro `rcon`.

## Validation Notes
- `python -m compileall backend/app` completo sin errores.
- `git diff --name-only` quedo limitado al alcance backend y documentacion de la task.
- El modo por defecto sigue apuntando a `a2s` para live y `public-scoreboard` para historico, por lo que el flujo de desarrollo no cambia.
