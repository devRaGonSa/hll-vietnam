# TASK-065-monthly-player-ranking-data-audit

## Goal
Auditar con precisión los datos disponibles actualmente en el proyecto y en la fuente histórica CRCON/scoreboard para determinar qué métricas pueden alimentar un futuro ranking mensual de mejores jugadores y con qué nivel de fiabilidad.

## Context
Se quiere diseñar un futuro ranking de “Top 3 mejores jugadores del mes”, idealmente teniendo en cuenta variables como:
- kills
- KPM
- KDA
- apoyo
- garrisons/OPs quitados si estuvieran disponibles
- enfrentamientos directos si fueran extraíbles
- impacto en partida

Pero antes de diseñar el ranking o asignar pesos, es imprescindible saber exactamente:
1. qué datos ya están persistidos en la base local del proyecto
2. qué datos existen en la fuente CRCON/scoreboard pero aún no guardamos
3. qué datos no están realmente disponibles o no son fiables
4. qué combinación de métricas sería viable para una primera versión realista del ranking

## Steps
1. Revisar el modelo histórico actual del proyecto, incluyendo:
   - tablas SQLite
   - modelos históricos
   - payloads
   - snapshots existentes
2. Inventariar qué métricas están ya disponibles y persistidas hoy por:
   - jugador
   - partida
   - jugador por partida
3. Confirmar con precisión qué campos existen ya en el histórico bruto y qué calidad tienen para un ranking serio.
4. Revisar la fuente histórica CRCON/scoreboard que usa el proyecto para verificar si, además de lo ya persistido, existen datos accesibles sobre:
   - garrisons destruidos
   - OPs destruidos
   - enfrentamientos directos / duelos
   - otras métricas útiles de impacto táctico
5. Documentar para cada métrica potencial:
   - si ya existe en la base
   - si existe en la fuente pero no se persiste aún
   - si no existe realmente o no puede extraerse de forma fiable
   - si sería recomendable usarla en una futura V1 del ranking
6. Dejar una matriz clara de disponibilidad y fiabilidad, por ejemplo:
   - métrica
   - disponible hoy
   - persistida hoy
   - calidad/fiabilidad
   - coste de implementación adicional
   - recomendable para V1 sí/no
7. Incluir una recomendación final sobre qué conjunto de métricas sería razonable para:
   - una V1 del ranking mensual
   - una posible V2 más ambiciosa
8. No diseñar todavía la fórmula final del ranking salvo una recomendación muy preliminar si ayuda a contextualizar.
9. No implementar todavía nuevas tablas, nuevas ingestas ni nuevas vistas de UI.
10. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- backend/README.md
- backend/app/historical_models.py
- backend/app/historical_storage.py
- backend/app/historical_ingestion.py
- backend/app/historical_snapshots.py
- backend/app/payloads.py
- docs/historical-domain-model.md
- docs/historical-data-quality-notes.md
- docs/historical-crcon-source-discovery.md
- docs/historical-coverage-report.md
- cualquier evidencia de endpoints o JSON reales de la fuente CRCON/scoreboard que ya use el proyecto

## Expected Files to Modify
- un documento nuevo, por ejemplo:
  - docs/monthly-player-ranking-data-audit.md
- opcionalmente ai/architecture-index.md si conviene enlazar esta auditoría
- opcionalmente docs/decisions.md si surge una decisión técnica clara sobre el alcance de métricas para V1/V2

## Constraints
- No implementar todavía el ranking mensual.
- No modificar producto visible.
- No crear nuevas rutas, vistas ni snapshots de ranking MVP.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en discovery, inventario y recomendación técnica.

## Validation
- Existe un documento claro que explica exactamente con qué datos podemos contar hoy.
- Queda claro qué métricas ya están persistidas y cuáles no.
- Queda claro qué métricas existen en la fuente CRCON/scoreboard pero requerirían trabajo adicional.
- Existe una recomendación técnica razonable para una V1 y una V2 del ranking mensual de jugadores.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 4 archivos modificados o creados.
- Preferir menos de 220 líneas cambiadas.
