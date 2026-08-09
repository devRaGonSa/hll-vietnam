# TASK-074-rcon-data-capability-audit

## Goal
Auditar con precisión qué datos reales pueden obtenerse hoy mediante RCON en el proyecto, qué datos requieren captura de eventos o logs, y qué métricas serían viables para una futura V2 del ranking MVP.

## Context
La integración live con RCON ya está funcionando en producción-like mode para el panel actual de servidores. Antes de evolucionar el sistema MVP mensual con métricas avanzadas, necesitamos saber con exactitud qué superficie de datos expone RCON realmente.

Es importante no confundir:
- RCON puro
- CRCON / scoreboard público
- agregados históricos tipo HLL Records

Algunas métricas deseadas para una futura V2 podrían incluir:
- kills por tipo de arma
- distinción de artillery / tank / infantry
- killer -> victim
- most_killed
- death_by
- teamkills por evento
- garrisons / OPs destruidos
- otras señales tácticas

Pero todavía no sabemos cuáles salen realmente de RCON directo y cuáles requerirían una canalización propia de eventos o persistencia adicional.

## Steps
1. Revisar la implementación actual del proveedor RCON:
   - backend/app/rcon_client.py
   - backend/app/providers/rcon_provider.py
   - backend/app/data_sources.py
2. Auditar qué comandos/capacidades reales expone hoy el cliente RCON implementado.
3. Verificar qué datos live pueden obtenerse ya de forma directa:
   - estado de servidor
   - jugadores
   - scoreboard actual
   - mapa
   - equipos
   - cualquier otro campo ya expuesto
4. Investigar si la superficie RCON actual o el protocolo disponible permiten acceder a:
   - kills por arma
   - killer/victim
   - death_by
   - most_killed
   - teamkills
   - artillery/tank distinctions
   - garrisons / OPs destruidos
   - otras métricas tácticas útiles
5. Separar claramente para cada métrica:
   - disponible por RCON directo hoy
   - disponible solo si se captura un flujo de eventos/logs
   - no confirmada
   - no disponible
6. Documentar qué métricas podrían alimentar una V2 del ranking MVP y bajo qué condiciones.
7. Aclarar qué parte requeriría:
   - ampliar el cliente RCON
   - capturar eventos
   - persistir nuevo histórico
   - agregar métricas propias
8. No implementar todavía nuevas tablas, nuevas rutas, nuevas métricas visibles ni cambios de scoring.
9. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- backend/README.md
- backend/app/rcon_client.py
- backend/app/providers/rcon_provider.py
- backend/app/data_sources.py
- backend/app/payloads.py
- docs/monthly-player-ranking-data-audit.md
- docs/monthly-mvp-ranking-scoring-design.md

## Expected Files to Modify
- docs/rcon-data-capability-audit.md
- opcionalmente ai/architecture-index.md si conviene enlazar la auditoría
- opcionalmente docs/decisions.md si surge una decisión técnica clara sobre el alcance de RCON para V2

## Constraints
- No implementar todavía la V2 del MVP.
- No tocar producto visible.
- No confundir CRCON/source pública con RCON puro.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en discovery técnico y viabilidad de métricas.

## Validation
- Existe un documento claro que explica qué datos reales se pueden obtener hoy por RCON.
- Queda claro qué métricas requerirían eventos/logs o persistencia adicional.
- Queda claro qué subset de métricas sería viable para una futura V2 del MVP.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 4 archivos modificados o creados.
- Preferir menos de 220 líneas cambiadas.

## Outcome
- Se documentó `docs/rcon-data-capability-audit.md` con el alcance real de RCON en la repo, separando RCON directo, CRCON público y métricas que requerirían pipeline de eventos/logs.
- La auditoría deja confirmado que la integración RCON operativa hoy solo cubre estado live basado en `ServerConnect`, `Login` y `GetServerInformation`.
- Quedó explícito que el proveedor histórico `rcon` sigue siendo un placeholder no operativo y que las métricas avanzadas para un MVP V2 no salen hoy de RCON directo en esta repo.
- `ai/architecture-index.md` enlaza ahora la nueva auditoría para mantener visible ese límite arquitectónico.

## Validation Notes
- Revisión de código completada sobre `backend/app/rcon_client.py`, `backend/app/providers/rcon_provider.py`, `backend/app/data_sources.py` y `backend/app/payloads.py`.
- La auditoría se mantuvo dentro del alcance documental: no se añadieron tablas, rutas ni cambios visibles de producto.
- La evidencia del repositorio sigue separando correctamente live por RCON frente a histórico por CRCON / scoreboard público.
