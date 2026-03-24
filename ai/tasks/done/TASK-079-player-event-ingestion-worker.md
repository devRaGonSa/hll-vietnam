# TASK-079-player-event-ingestion-worker

## Goal
Añadir un worker/proceso incremental para ingerir eventos de jugador V2 de forma segura, reanudable y compatible con la operación actual del proyecto.

## Context
Con una fuente de eventos y un ledger raw, hace falta un proceso de ingestión incremental que capture eventos sin depender del request path del usuario y sin romper el pipeline actual de histórico y snapshots.

## Steps
1. Revisar la nueva capa de fuente de eventos y la persistencia raw.
2. Diseñar un worker incremental específico para eventos de jugador.
3. Añadir soporte para:
   - ejecución manual
   - reintentos básicos
   - checkpoint o mecanismo de reanudación si aplica
   - deduplicación segura
4. Mantenerlo desacoplado del `historical-runner` actual si eso reduce riesgo operacional.
5. Documentar cómo se ejecuta y cuál es su alcance.
6. No implementar todavía snapshots finales ni UI del MVP V2.
7. No romper el stack Docker actual ni el flujo histórico existente.
8. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- docs/player-event-pipeline-v2-design.md
- backend/README.md
- backend/app/historical_runner.py
- backend/app/config.py
- módulos de eventos añadidos en tasks previas

## Expected Files to Modify
- backend/app/config.py
- backend/README.md
- opcionalmente docker-compose.yml si hace falta dejar preparado el worker
- opcionalmente nuevos módulos, por ejemplo:
  - backend/app/player_event_worker.py
  - backend/app/player_event_ingestion.py

## Constraints
- No romper el runner histórico actual.
- No meter todavía lógica de scoring V2.
- No tocar producto visible.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en ingestión incremental de eventos.

## Validation
- Existe un worker o flujo incremental para eventos de jugador.
- Puede ejecutarse de forma segura y reanudable.
- No rompe el resto del sistema.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 6 archivos modificados o creados.
- Preferir menos de 240 líneas cambiadas.
