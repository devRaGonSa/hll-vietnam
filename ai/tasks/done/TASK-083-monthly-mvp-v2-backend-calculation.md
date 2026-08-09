# TASK-083-monthly-mvp-v2-backend-calculation

## Goal
Implementar en backend el cálculo mensual del MVP V2 a partir de la fórmula aprobada y de las métricas derivadas V2 ya disponibles por snapshots/agregados.

## Context
La base V2 ya existe y, tras cerrar el diseño de scoring, hace falta materializar el ranking mensual MVP V2 en backend. Esta versión debe poder convivir con la V1 mientras se valida en producto.

## Steps
1. Revisar:
   - scoring V2 aprobado
   - agregados V2 disponibles
   - snapshots/API de métricas avanzadas
2. Implementar el cálculo del ranking mensual MVP V2 por:
   - servidor
   - all-servers cuando aplique
3. Aplicar correctamente:
   - pesos
   - elegibilidad
   - penalizaciones
   - desempates
4. Mantenerlo separado del MVP V1.
5. Preparar el resultado para poder exponerlo después por snapshot/API y, más tarde, por UI.
6. Documentar la nueva capacidad backend.
7. No implementar todavía la UI final.
8. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- docs/monthly-mvp-v2-scoring-design.md
- backend/README.md
- backend/app/player_event_aggregates.py
- backend/app/historical_storage.py
- backend/app/payloads.py
- backend/app/routes.py
- backend/app/historical_snapshots.py

## Expected Files to Modify
- backend/README.md
- backend/app/payloads.py
- backend/app/routes.py
- backend/app/historical_storage.py
- opcionalmente nuevos módulos, por ejemplo:
  - backend/app/monthly_mvp_v2.py
  - backend/app/monthly_mvp_v2_scoring.py

## Constraints
- No romper el MVP V1.
- No tocar todavía la UI final.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en el cálculo backend del MVP V2.

## Validation
- Existe un cálculo backend funcional del monthly MVP V2.
- Soporta servidor y/o all-servers según diseño.
- Convive con la V1.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 6 archivos modificados o creados.
- Preferir menos de 240 líneas cambiadas.
