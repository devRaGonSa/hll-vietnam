# TASK-082-monthly-mvp-v2-scoring-design-adjustment

## Goal
Diseñar o ajustar de forma precisa la fórmula del MVP mensual V2 incorporando las nuevas métricas derivadas de eventos de jugador ya disponibles.

## Context
La V1 del MVP mensual ya existe y se apoya en métricas persistidas básicas. Con la nueva capa V2 de eventos y agregados, ya se pueden plantear señales más ricas como:
- kills por arma
- teamkills derivados
- duelos y rivalidades
- most_killed / death_by
- posible ponderación por tipo de kill si la señal es suficientemente fiable

Antes de implementar el backend del MVP V2, hace falta cerrar la fórmula concreta y sus pesos.

## Steps
1. Revisar el diseño de scoring V1 y la nueva disponibilidad de métricas V2.
2. Decidir qué métricas avanzadas entran realmente en la V2.
3. Diseñar una fórmula concreta para el MVP mensual V2, incluyendo:
   - pesos
   - elegibilidad
   - penalizaciones
   - tratamiento de muestras pequeñas
   - desempates
4. Decidir si:
   - las kills deben ponderarse por arma/tipo
   - cómo influye teamkill
   - cómo influye duelo/rivalidad
   - qué parte de la V1 se mantiene
5. Mantener la fórmula defendible y explicable, evitando complejidad artificial si la señal aún no es robusta.
6. Dejar clara la compatibilidad o convivencia entre:
   - MVP V1
   - MVP V2
7. No implementar todavía la UI.
8. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- docs/monthly-mvp-ranking-scoring-design.md
- docs/player-event-pipeline-v2-design.md
- docs/monthly-player-ranking-data-audit.md
- backend/README.md
- backend/app/player_event_aggregates.py
- cualquier snapshot/API V2 disponible tras la task previa

## Expected Files to Modify
- docs/monthly-mvp-v2-scoring-design.md
- opcionalmente docs/decisions.md
- opcionalmente ai/architecture-index.md

## Constraints
- No implementar todavía el cálculo backend del MVP V2.
- No tocar producto visible.
- No depender de métricas no confirmadas.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en diseño de scoring V2.

## Validation
- Existe un documento claro con la fórmula V2 propuesta.
- Quedan definidos pesos, elegibilidad, penalizaciones y desempates.
- Queda claro qué señales entran realmente en V2.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 4 archivos modificados o creados.
- Preferir menos de 220 líneas cambiadas.
