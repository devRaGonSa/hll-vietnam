# TASK-069-monthly-mvp-ui-top3

## Goal
Añadir a la página histórica una sección clara y visual para mostrar el Top 3 MVP mensual V1, consumiendo los snapshots/API ya preparados y manteniendo coherencia con la navegación existente.

## Context
El monthly MVP V1 ya está definido a nivel de diseño y, tras las tasks previas, debe quedar disponible en snapshots y API. El siguiente paso es exponerlo en la UI de forma clara, sin convertir la pantalla en algo recargado ni confuso.

## Steps
1. Revisar la UI histórica actual y el nuevo endpoint/snapshot del monthly MVP.
2. Diseñar una sección visual clara para el Top 3 MVP mensual.
3. Mantener compatibilidad con el selector actual de ámbito:
   - servidor individual
   - all-servers
4. Mostrar, como mínimo:
   - posición 1, 2 y 3
   - nombre de jugador
   - puntuación MVP
   - metadatos mínimos útiles según el diseño aprobado
5. Mostrar el periodo mensual real usado de forma natural.
6. Mantener estados de:
   - loading
   - empty
   - error
7. Integrar la nueva sección sin romper la navegación actual semanal/mensual de leaderboards por métrica.
8. Mantener el rendimiento percibido y la coherencia visual con la página actual.
9. No crear páginas nuevas.
10. Al completar la implementación:
    - dejar el repositorio consistente
    - hacer commit
    - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- frontend/historico.html
- frontend/assets/js/historico.js
- frontend/assets/css/historico.css
- backend/app/routes.py
- backend/app/payloads.py
- backend/README.md
- docs/monthly-mvp-ranking-scoring-design.md

## Expected Files to Modify
- frontend/historico.html
- frontend/assets/js/historico.js
- frontend/assets/css/historico.css
- opcionalmente backend docs mínimas si hay que reflejar el nuevo bloque visible

## Constraints
- No romper la UI histórica actual.
- No introducir frameworks nuevos.
- No crear páginas nuevas.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en una sección Top 3 mensual clara y útil.

## Validation
- La UI histórica muestra el Top 3 MVP mensual.
- Funciona para servidor individual y all-servers.
- El periodo mensual mostrado es claro.
- Los estados de loading/empty/error son coherentes.
- La pantalla sigue siendo usable y visualmente consistente.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 5 archivos modificados.
- Preferir menos de 220 líneas cambiadas.
