# TASK-043-historical-snapshots-generation-runner

## Goal
Implementar un generador/runner de snapshots históricos que calcule y refresque periódicamente resumen, tops y partidas recientes para cada servidor de la comunidad.

## Context
Una vez existe almacenamiento de snapshots, hace falta una capa operativa que genere esos snapshots a partir del histórico persistido. El objetivo es que la página histórica no dependa de cálculos pesados en tiempo real, sino de datos precalculados actualizados periódicamente.

## Steps
1. Revisar los agregados históricos actuales y la nueva capa de snapshots.
2. Implementar un runner o flujo de generación que produzca snapshots para cada servidor.
3. Generar, como mínimo:
   - resumen de servidor
   - top kills 7d
   - top muertes 7d
   - top partidas con más de 100 kills por jugador 7d
   - top puntos de soporte 7d
   - partidas recientes
4. Añadir metadatos de generación y estado.
5. Definir una frecuencia razonable de refresco, por ejemplo 10 o 15 minutos.
6. Documentar cómo ejecutar el runner manualmente y cómo operarlo de forma periódica.
7. No migrar todavía toda la UI en esta task.
8. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- backend/README.md
- backend/app/config.py
- backend/app/historical_storage.py
- backend/app/historical_snapshots.py
- backend/app/historical_snapshot_storage.py
- backend/app/historical_runner.py

## Expected Files to Modify
- backend/README.md
- backend/app/config.py
- backend/app/historical_runner.py
- backend/app/historical_snapshots.py
- backend/app/historical_snapshot_storage.py
- opcionalmente nuevos módulos auxiliares de generación

## Constraints
- No romper el live status.
- No crear UI nueva en esta task.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en generación periódica de snapshots.

## Validation
- Existe un runner que genera snapshots de resumen, tops y partidas recientes.
- Los snapshots se pueden refrescar periódicamente.
- La documentación explica cómo ejecutarlo.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 6 archivos modificados o creados.
- Preferir menos de 240 líneas cambiadas.
