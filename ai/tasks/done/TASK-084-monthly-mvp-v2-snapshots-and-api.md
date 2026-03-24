# TASK-084-monthly-mvp-v2-snapshots-and-api

## Goal
Exponer el ranking mensual MVP V2 mediante snapshots JSON y API propia del backend, manteniéndolo separado del MVP V1 y preparado para una futura UI.

## Context
Una vez exista el cálculo backend del MVP V2, hace falta integrarlo en la capa de snapshots y API para lectura rápida, sin añadir cálculos pesados al request path.

## Steps
1. Revisar el cálculo backend del MVP V2.
2. Diseñar snapshots adecuados para:
   - MVP V2 por servidor
   - MVP V2 all-servers si aplica
3. Exponer endpoints claros y consistentes para leer estos snapshots.
4. Incluir metadatos útiles:
   - generated_at
   - month_key / periodo
   - found
   - source_range_start / source_range_end si aplica
5. Integrar la generación en la operativa existente de snapshots si corresponde.
6. Mantener la separación explícita entre:
   - MVP V1
   - MVP V2
7. No implementar todavía la UI V2 final en esta task.
8. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- backend/README.md
- backend/app/historical_snapshots.py
- backend/app/historical_snapshot_storage.py
- backend/app/routes.py
- backend/app/payloads.py
- backend/app/historical_runner.py
- backend/app/config.py

## Expected Files to Modify
- backend/app/routes.py
- backend/app/payloads.py
- backend/app/historical_snapshots.py
- backend/app/historical_snapshot_storage.py
- backend/app/historical_runner.py
- backend/README.md
- opcionalmente nuevos módulos auxiliares si mejoran claridad

## Constraints
- No romper snapshots existentes.
- No mezclar MVP V1 y V2.
- No tocar todavía la UI final.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en snapshots/API del MVP V2.

## Validation
- Existen snapshots JSON del MVP V2.
- Existen endpoints backend para leerlos.
- La lectura es rápida.
- MVP V1 y V2 conviven claramente.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 6 archivos modificados o creados.
- Preferir menos de 240 líneas cambiadas.
