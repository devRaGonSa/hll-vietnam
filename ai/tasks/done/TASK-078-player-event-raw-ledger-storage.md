# TASK-078-player-event-raw-ledger-storage

## Goal
Crear la persistencia raw mínima para eventos de jugador V2, permitiendo almacenar de forma fiable eventos de kill/death con claves estables, deduplicación y base para agregados posteriores.

## Context
Una vez exista una fuente/adaptador de eventos, hace falta una capa de persistencia en bruto. Esta capa debe ser lo bastante simple para operar ya, pero lo bastante sólida para soportar luego agregados como:
- most_killed
- death_by
- kills por arma
- teamkills por jugador
- killer/victim mensual

## Steps
1. Revisar el diseño V2 del pipeline de eventos.
2. Diseñar una tabla o conjunto mínimo de tablas para el ledger raw de eventos de jugador.
3. Incluir como base, si la fuente lo permite:
   - server key
   - match reference
   - event timestamp
   - killer identity
   - victim identity
   - weapon
   - teamkill flag
   - event source reference o clave de deduplicación
4. Implementar inicialización segura del storage de eventos.
5. Implementar inserción idempotente o deduplicada.
6. Mantener separada esta capa del histórico actual `historical_*`.
7. Documentar la estructura y su propósito.
8. No implementar todavía agregados finales ni UI.
9. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- docs/player-event-pipeline-v2-design.md
- backend/README.md
- backend/app/historical_models.py
- backend/app/historical_storage.py
- cualquier módulo nuevo de la task anterior relacionado con eventos

## Expected Files to Modify
- backend/README.md
- opcionalmente nuevos módulos, por ejemplo:
  - backend/app/player_event_storage.py
  - backend/app/player_event_models.py
- opcionalmente docs/decisions.md si conviene fijar una decisión de persistencia

## Constraints
- No romper el histórico actual.
- No mezclar esta persistencia con snapshots ni UI.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en el ledger raw de eventos.

## Validation
- Existe una persistencia raw mínima para eventos de jugador.
- Soporta deduplicación o idempotencia razonable.
- Queda separada del histórico actual.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 6 archivos modificados o creados.
- Preferir menos de 240 líneas cambiadas.
