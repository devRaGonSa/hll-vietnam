# TASK-076-player-event-pipeline-v2-design

## Goal
Diseñar una arquitectura mínima de pipeline de eventos de jugador que permita, en una futura fase, persistir y agregar datos avanzados necesarios para una V2 del ranking MVP.

## Context
Si métricas como killer/victim, `most_killed`, `death_by`, kills por arma o acciones tácticas no salen listas de RCON puro, el proyecto necesitará una canalización propia de eventos/logs y una persistencia específica para construir esas vistas.

## Steps
1. Revisar la auditoría sobre el origen de métricas avanzadas.
2. Diseñar una arquitectura mínima para una futura canalización de eventos.
3. Definir qué tipos de eventos serían necesarios como base, por ejemplo:
   - kill
   - death
   - killer -> victim
   - weapon used
   - teamkill
   - cualquier otro evento imprescindible confirmado
4. Definir qué tabla o modelo de persistencia haría falta a alto nivel.
5. Definir cómo se agregarían después métricas como:
   - `most_killed`
   - `death_by`
   - kills por arma
   - distinción infantry/tank/artillery si fuera posible
6. Explicar cómo esa capa podría alimentar una futura V2 del MVP mensual.
7. Mantener fuera de alcance la implementación real.
8. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- docs/rcon-data-capability-audit.md
- docs/crcon-advanced-metrics-origin-audit.md
- docs/monthly-mvp-ranking-scoring-design.md
- backend/README.md
- backend/app/historical_models.py
- backend/app/historical_storage.py
- backend/app/rcon_client.py

## Expected Files to Modify
- docs/player-event-pipeline-v2-design.md
- opcionalmente ai/architecture-index.md
- opcionalmente docs/decisions.md

## Constraints
- No implementar todavía la canalización.
- No crear tablas ni rutas reales.
- No tocar producto visible.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en diseño técnico.

## Validation
- Existe un documento claro con la arquitectura mínima propuesta para eventos de jugador.
- Queda claro qué eventos serían necesarios y cómo alimentarían una V2 del MVP.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 4 archivos modificados o creados.
- Preferir menos de 220 líneas cambiadas.
