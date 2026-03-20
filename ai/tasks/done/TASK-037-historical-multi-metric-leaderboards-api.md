# TASK-037-historical-multi-metric-leaderboards-api

## Goal
Extender la capa histórica del backend para soportar varios rankings semanales por servidor, no solo top kills, de modo que la UI pueda mostrar pestañas con diferentes métricas relevantes.

## Context
La página histórica ya muestra un ranking semanal de kills, pero se quiere evolucionar hacia una sección con varias pestañas o vistas de ranking para el mismo rango temporal. Las métricas solicitadas inicialmente son:
- Top kills
- Top muertes
- Top número de partidas con más de 100 kills (a nivel de jugador)
- Top puntos de soporte

Para que la UI pueda hacerlo de forma limpia, primero hace falta una API histórica más flexible y consistente.

## Steps
1. Revisar la implementación actual del endpoint de `weekly-top-kills`.
2. Revisar el modelo histórico persistido y confirmar qué métricas están disponibles de forma fiable, especialmente:
   - kills
   - deaths
   - support score / puntos de soporte
   - kills por partida por jugador
3. Diseñar una estrategia de API para rankings históricos multitétrica. Puede ser:
   - un endpoint genérico por métrica
   - varios endpoints específicos
   - o una solución equivalente siempre que sea clara y mantenible
4. Implementar soporte para estas métricas en la misma ventana temporal semanal:
   - top kills
   - top deaths
   - top count of matches with kills >= 100 por jugador
   - top support points
5. Asegurar que las queries:
   - respetan el servidor seleccionado
   - respetan el rango temporal semanal
   - no mezclan datos entre servidores
   - no devuelven duplicados por mala consolidación de identidad
6. Si alguna métrica requerida no estuviera siendo persistida todavía de forma válida, completar lo estrictamente necesario en la capa histórica para soportarla.
7. Documentar la nueva API en backend.
8. No crear todavía pestañas o cambios visuales en frontend en esta task.
9. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- backend/README.md
- backend/app/routes.py
- backend/app/payloads.py
- backend/app/historical_storage.py
- backend/app/historical_models.py
- backend/app/historical_ingestion.py
- docs/historical-domain-model.md
- docs/historical-data-quality-notes.md

## Expected Files to Modify
- backend/app/routes.py
- backend/app/payloads.py
- backend/app/historical_storage.py
- backend/app/historical_models.py
- opcionalmente backend/app/historical_ingestion.py si hace falta completar la persistencia de alguna métrica necesaria
- backend/README.md
- opcionalmente nuevos módulos de query histórica si mejoran claridad

## Constraints
- No basar estas métricas en A2S.
- No crear UI en esta task.
- No depender de páginas externas de la comunidad.
- No romper el endpoint histórico actual salvo para mejorarlo o generalizarlo.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en API histórica y consistencia de métricas.

## Validation
- Existen rankings históricos semanales para:
  - kills
  - muertes
  - partidas con más de 100 kills por jugador
  - puntos de soporte
- Los rankings funcionan por servidor.
- Los rankings respetan la ventana semanal definida por el proyecto.
- La documentación backend queda alineada.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 7 archivos modificados o creados.
- Preferir menos de 260 líneas cambiadas.
