# TASK-077-player-kill-event-source-adapter

## Goal
Implementar una primera capa/adaptador de fuente de eventos centrada en eventos de kill/death para preparar la V2 del sistema de métricas de jugador.

## Context
Las auditorías previas concluyen que el cliente RCON live actual no basta por sí solo para obtener directamente todos los agregados avanzados visibles en ecosistemas tipo CRCON/HLL Records. Para construir métricas como:
- killer -> victim
- most_killed
- death_by
- kills por arma
- teamkills por evento

hace falta una fuente de eventos o una adaptación técnica que permita modelar esos datos en bruto antes de agregarlos.

La V2 debe empezar por una primera capa mínima centrada en eventos de kill/death, sin abarcar todavía todo el resto de acciones tácticas.

## Steps
1. Revisar las auditorías y documentos de diseño V2:
   - docs/rcon-data-capability-audit.md
   - docs/crcon-advanced-metrics-origin-audit.md
   - docs/player-event-pipeline-v2-design.md
2. Identificar la fuente o punto técnico más viable dentro del proyecto actual para empezar a capturar eventos de kill/death.
3. Diseñar e implementar un adaptador/fuente mínima para eventos de jugador que, como mínimo, pueda producir un formato común con campos base como:
   - server
   - match
   - timestamp
   - killer
   - victim
   - weapon si existe
   - teamkill si existe
4. Mantener esta capa desacoplada de la persistencia final.
5. Documentar claramente:
   - qué datos se capturan realmente en esta fase
   - qué datos siguen fuera de alcance
6. No implementar todavía snapshots/UI del MVP V2.
7. No romper live RCON ni el histórico actual.
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
- docs/player-event-pipeline-v2-design.md
- backend/README.md
- backend/app/rcon_client.py
- backend/app/providers/rcon_provider.py
- backend/app/data_sources.py

## Expected Files to Modify
- backend/README.md
- opcionalmente nuevos módulos, por ejemplo:
  - backend/app/player_event_source.py
  - backend/app/providers/player_event_source_provider.py
  - backend/app/event_sources/*.py
- opcionalmente ai/architecture-index.md si conviene enlazar la nueva pieza

## Constraints
- No implementar todavía agregados finales ni UI.
- No romper el proveedor RCON live actual.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en una fuente mínima de eventos kill/death.

## Validation
- Existe una capa/adaptador clara para eventos de kill/death.
- Produce un formato mínimo reutilizable por la persistencia posterior.
- Queda documentado qué cubre y qué no cubre todavía.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 6 archivos modificados o creados.
- Preferir menos de 240 líneas cambiadas.
