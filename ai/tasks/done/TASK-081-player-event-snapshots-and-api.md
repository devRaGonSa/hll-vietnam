# TASK-081-player-event-snapshots-and-api

## Goal
Exponer por snapshots JSON y API propia del backend las nuevas métricas derivadas V2 de eventos de jugador, manteniendo la filosofía de lectura rápida y desacoplada del request path pesado.

## Context
La base V2 ya existe:
- source adapter
- raw ledger
- incremental worker
- derived aggregates

Ahora hace falta convertir esas métricas derivadas en una capa consumible por producto y por futuras fórmulas de MVP V2 sin depender de consultas pesadas on-demand.

Las primeras métricas que deben quedar listas para lectura rápida son:
- most_killed
- death_by
- duel summaries
- weapon kills
- teamkills derivados

## Steps
1. Revisar los agregados V2 ya implementados.
2. Diseñar snapshots JSON adecuados para estas métricas avanzadas por:
   - servidor
   - all-servers cuando aplique
   - periodo mensual si corresponde
3. Exponer endpoints claros y consistentes para leer esas métricas.
4. Mantener la misma filosofía que el histórico actual:
   - lectura rápida
   - sin cálculos pesados en el request path
5. Incluir metadatos claros en los snapshots cuando aplique:
   - generated_at
   - period/month_key
   - source_range_start
   - source_range_end
   - found / is_stale si aplica
6. Integrar la generación de estos snapshots con la operativa existente o con una vía equivalente razonable.
7. No implementar todavía la UI V2 final.
8. No romper el MVP V1 ni los snapshots actuales.
9. Al completar la implementación:
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
- backend/app/player_event_aggregates.py
- backend/app/player_event_storage.py
- docs/player-event-pipeline-v2-design.md

## Expected Files to Modify
- backend/app/routes.py
- backend/app/payloads.py
- backend/app/historical_snapshots.py
- backend/app/historical_snapshot_storage.py
- backend/README.md
- opcionalmente nuevos módulos auxiliares si mejoran claridad

## Constraints
- No recalcular estas métricas pesadas en cada request.
- No romper la API histórica existente.
- No tocar todavía la UI final del MVP V2.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en snapshots/API V2.

## Validation
- Existen snapshots JSON de métricas V2.
- Existen endpoints backend para leerlas.
- La lectura es rápida y coherente con la arquitectura actual.
- No se rompe el MVP V1 ni el histórico actual.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 6 archivos modificados o creados.
- Preferir menos de 240 líneas cambiadas.
