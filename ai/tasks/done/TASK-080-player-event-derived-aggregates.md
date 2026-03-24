# TASK-080-player-event-derived-aggregates

## Goal
Construir los primeros agregados derivados V2 a partir del ledger raw de eventos de jugador, centrados en duelos y armas, para preparar una futura V2 del MVP.

## Context
Con eventos raw ya capturados, el siguiente paso es derivar métricas útiles y reutilizables. Las primeras más valiosas para la V2 del MVP son:
- most_killed
- death_by
- killer/victim
- kills por arma
- teamkills por jugador

## Steps
1. Revisar la estructura del ledger raw y el diseño V2.
2. Diseñar e implementar agregados básicos por:
   - partida
   - mes
   - servidor
   - all-servers cuando aplique
3. Incluir al menos:
   - most_killed
   - death_by
   - net duel summaries
   - kills por arma
   - teamkills derivados por jugador
4. Mantener los agregados separados de la UI y del MVP V1.
5. Documentar qué métricas derivadas quedan ya disponibles para una futura V2 del score.
6. No implementar todavía la fórmula final del MVP V2 ni su UI.
7. No hacer cambios destructivos.
8. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- docs/player-event-pipeline-v2-design.md
- docs/crcon-advanced-metrics-origin-audit.md
- backend/README.md
- módulos de eventos raw ya implementados
- backend/app/historical_storage.py
- docs/monthly-mvp-ranking-scoring-design.md

## Expected Files to Modify
- backend/README.md
- opcionalmente nuevos módulos, por ejemplo:
  - backend/app/player_event_aggregates.py
  - backend/app/player_event_queries.py
- opcionalmente docs/decisions.md si hace falta fijar alguna decisión de agregación

## Constraints
- No tocar todavía la UI del MVP V2.
- No romper el MVP V1.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en agregados base de duelos y armas.

## Validation
- Existen agregados derivados básicos reutilizables para V2.
- Queda clara su disponibilidad por servidor/mes/all-servers cuando aplique.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 6 archivos modificados o creados.
- Preferir menos de 240 líneas cambiadas.
