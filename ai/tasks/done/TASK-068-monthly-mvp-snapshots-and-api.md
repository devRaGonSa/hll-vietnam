# TASK-068-monthly-mvp-snapshots-and-api

## Goal
Exponer el ranking mensual MVP V1 mediante snapshots JSON y API propia del backend, siguiendo la misma filosofía rápida y estable ya usada por la capa histórica.

## Context
Una vez implementado el cálculo backend del monthly MVP, hace falta integrarlo en la capa de snapshots del proyecto para que:
- no dependa de cálculos pesados on-demand
- pueda servirse rápido a la UI
- sea consistente con el resto de la arquitectura histórica

## Steps
1. Revisar la implementación del cálculo mensual MVP y la arquitectura actual de snapshots JSON.
2. Diseñar la forma de snapshot para el ranking mensual MVP, tanto por servidor como para all-servers.
3. Generar snapshots JSON apropiados, por ejemplo:
   - server monthly mvp
   - all-servers monthly mvp
4. Incluir metadatos claros, como mínimo:
   - generated_at
   - source_range_start
   - source_range_end
   - freshness / is_stale si aplica
   - month_key o periodo real usado
5. Exponer endpoints claros y consistentes para leer esos snapshots.
6. Mantener compatibilidad y coherencia con la API histórica existente.
7. Integrar el monthly MVP en el runner/generación periódica de snapshots si corresponde.
8. No crear todavía la UI final en esta task.
9. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- backend/README.md
- backend/app/routes.py
- backend/app/payloads.py
- backend/app/historical_snapshots.py
- backend/app/historical_snapshot_storage.py
- backend/app/historical_runner.py
- backend/app/config.py
- docs/monthly-mvp-ranking-scoring-design.md

## Expected Files to Modify
- backend/app/routes.py
- backend/app/payloads.py
- backend/app/historical_snapshots.py
- backend/app/historical_snapshot_storage.py
- backend/app/historical_runner.py
- backend/README.md
- opcionalmente nuevos módulos auxiliares si mejoran claridad

## Constraints
- No recalcular el ranking pesado en cada request de usuario.
- No romper snapshots históricos existentes.
- No crear todavía UI nueva en esta task.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en snapshots y API del monthly MVP.

## Validation
- Existen snapshots JSON del monthly MVP para servidor y/o all-servers según diseño.
- Existen endpoints para leer esos snapshots.
- El monthly MVP se integra con la operativa de snapshots del proyecto.
- La respuesta es rápida y coherente con el resto de la API histórica.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 6 archivos modificados o creados.
- Preferir menos de 240 líneas cambiadas.
