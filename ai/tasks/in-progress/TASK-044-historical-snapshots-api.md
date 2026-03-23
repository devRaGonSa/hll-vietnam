# TASK-044-historical-snapshots-api

## Goal
Exponer una API de snapshots históricos precalculados para que el frontend pueda consumir resumen, tops y partidas recientes sin disparar agregaciones costosas en tiempo real.

## Context
Con snapshots ya persistidos y generados periódicamente, el siguiente paso es exponer endpoints ligeros para que la UI histórica lea directamente datos preparados.

## Steps
1. Revisar la capa de snapshots ya creada y el runner de generación.
2. Diseñar endpoints claros para leer snapshots por servidor, tipo y métrica.
3. Cubrir como mínimo:
   - resumen de servidor
   - tops semanales por métrica
   - partidas recientes
4. Asegurar que los endpoints devuelven también información útil de actualización:
   - generated_at
   - rango fuente
   - stale/fresh si aplica
5. Mantener compatibilidad razonable con la UI histórica ya existente o dejar clara la migración.
6. Documentar los endpoints en backend.
7. No cambiar todavía toda la UI en esta task.
8. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- backend/README.md
- backend/app/routes.py
- backend/app/payloads.py
- backend/app/historical_snapshot_storage.py
- backend/app/historical_snapshots.py

## Expected Files to Modify
- backend/app/routes.py
- backend/app/payloads.py
- backend/README.md
- opcionalmente nuevos módulos de payload/query de snapshots

## Constraints
- No usar A2S para esta capa.
- No hacer cálculos pesados on-demand si ya existe snapshot válido.
- No crear UI nueva en esta task.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en una API ligera de snapshots.

## Validation
- Existen endpoints de snapshots para resumen, tops y partidas recientes.
- Los payloads incluyen metadatos de actualización útiles.
- La capa está lista para que la UI deje de depender de agregados pesados en tiempo real.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 5 archivos modificados o creados.
- Preferir menos de 220 líneas cambiadas.
