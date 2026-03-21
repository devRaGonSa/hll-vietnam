# TASK-042-historical-snapshots-storage-and-model

## Goal
Diseñar e implementar una capa de almacenamiento de snapshots históricos precalculados para el proyecto, preparada para servir rápidamente resumen, rankings y partidas recientes sin recalcular agregados pesados en tiempo real.

## Context
La página histórica ya funciona, pero parte de la información puede requerir agregaciones costosas si se calculan en el momento de cada carga o al cambiar de pestaña. El objetivo es introducir una capa de snapshots precalculados y persistidos que permita responder de forma rápida y estable. Esto debe incluir no solo el resumen del servidor, sino también los tops/rankings semanales.

## Steps
1. Revisar la estructura histórica actual y los endpoints/API que hoy calculan resumen, rankings y partidas recientes.
2. Diseñar un modelo de snapshot persistido que soporte, como mínimo:
   - resumen de servidor
   - top kills semanales
   - top muertes semanales
   - top partidas con más de 100 kills por jugador
   - top puntos de soporte semanales
   - partidas recientes
3. Definir para cada snapshot metadatos claros, por ejemplo:
   - server_key
   - snapshot_type
   - metric
   - window
   - payload_json
   - generated_at
   - source_range_start
   - source_range_end
   - is_stale
4. Implementar el almacenamiento local de snapshots de forma coherente con la persistencia histórica actual.
5. Documentar la estructura y propósito de esta nueva capa.
6. No migrar todavía toda la UI a snapshots en esta task.
7. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- backend/README.md
- backend/app/historical_models.py
- backend/app/historical_storage.py
- backend/app/payloads.py
- backend/app/routes.py
- docs/historical-domain-model.md

## Expected Files to Modify
- backend/README.md
- backend/app/historical_models.py
- backend/app/historical_storage.py
- opcionalmente nuevos módulos, por ejemplo:
  - backend/app/historical_snapshots.py
  - backend/app/historical_snapshot_storage.py
- opcionalmente documentación técnica adicional

## Constraints
- No basar esta capa en A2S.
- No crear todavía nueva UI en esta task.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en almacenamiento y modelo de snapshots.

## Validation
- Existe un modelo de snapshot persistido claro.
- El modelo cubre resumen, rankings y partidas recientes.
- La estructura está lista para ser rellenada periódicamente.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 6 archivos modificados o creados.
- Preferir menos de 220 líneas cambiadas.
