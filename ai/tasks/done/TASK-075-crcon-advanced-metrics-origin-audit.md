# TASK-075-crcon-advanced-metrics-origin-audit

## Goal
Auditar el origen técnico real de métricas avanzadas visibles en ecosistemas tipo CRCON / HLL Records, como `most_killed`, `death_by`, killer-victim, kills por arma y otras señales avanzadas, para determinar si provienen de RCON directo, de eventos/logs, o de una persistencia/agregación propia.

## Context
El proyecto ya integra RCON para live state y la auditoría previa concluyó que el RCON actual del proyecto solo cubre estado live directo. Sin embargo, CRCON / HLL Records muestran métricas avanzadas como:
- `most_killed`
- `death_by`
- duelos entre jugadores
- kills por arma
- otros agregados históricos avanzados

Antes de diseñar una V2 del MVP, hace falta entender exactamente de dónde salen esos datos en términos técnicos.

## Steps
1. Revisar la auditoría existente sobre capacidades RCON.
2. Analizar la implementación actual del proyecto y documentar claramente qué NO está saliendo del cliente RCON actual.
3. Investigar conceptualmente qué caminos posibles explican la existencia de métricas avanzadas en CRCON / HLL Records:
   - comandos RCON directos
   - flujo de eventos
   - logs del servidor
   - almacenamiento propio de CRCON
   - API interna o snapshots enriquecidos
4. Revisar si en la repo ya hay pistas, docs o referencias sobre:
   - `most_killed`
   - `death_by`
   - `kills_by_type`
   - `death_by_weapons`
   - killer/victim
5. Documentar una conclusión clara:
   - qué es plausible obtener por RCON puro
   - qué parece requerir captura de eventos o logs
   - qué parece requerir agregación histórica propia
6. Dejar una matriz clara de origen probable por métrica.
7. No implementar todavía la captura ni nuevas tablas.
8. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- docs/rcon-data-capability-audit.md
- docs/monthly-player-ranking-data-audit.md
- backend/README.md
- backend/app/rcon_client.py
- backend/app/providers/rcon_provider.py
- backend/app/data_sources.py
- cualquier doc local relacionada con CRCON, HLL Records o métricas avanzadas si existiera

## Expected Files to Modify
- docs/crcon-advanced-metrics-origin-audit.md
- opcionalmente ai/architecture-index.md
- opcionalmente docs/decisions.md si surge una conclusión técnica clara

## Constraints
- No implementar todavía captura avanzada.
- No tocar producto visible.
- No asumir sin evidencia que una métrica sale de RCON directo.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en discovery técnico.

## Validation
- Existe un documento que separa claramente:
  - RCON directo
  - eventos/logs
  - agregación/persistencia propia
- Queda claro el origen probable de métricas como `most_killed` y `death_by`
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 4 archivos modificados o creados.
- Preferir menos de 220 líneas cambiadas.
