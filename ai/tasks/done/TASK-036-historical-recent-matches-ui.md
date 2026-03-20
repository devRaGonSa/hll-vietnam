# TASK-036-historical-recent-matches-ui

## Goal
Añadir a la UI histórica propia del proyecto una vista o bloque de partidas recientes por servidor, consumiendo exclusivamente la API interna del backend.

## Context
La primera UI histórica del proyecto debe crecer de forma progresiva. Tras el ranking semanal, el siguiente bloque lógico es una vista de partidas recientes que complemente el histórico y aporte más contexto al usuario.

## Steps
1. Revisar la UI histórica ya implementada o diseñada en la task previa.
2. Revisar el endpoint de partidas recientes y su payload.
3. Añadir una sección o vista clara para mostrar partidas recientes por servidor.
4. Mostrar, como mínimo:
   - fecha/hora
   - mapa
   - servidor
   - metadatos relevantes si están disponibles
5. Mantener la navegación y el selector de servidor claros.
6. Añadir estados de loading, empty y error para esta vista.
7. Mantener coherencia visual con el resto del frontend histórico.
8. No usar páginas de la comunidad ni incrustaciones externas.
9. Al completar la implementación:
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
- docs/historical-domain-model.md

## Expected Files to Modify
- frontend/historico.html
- frontend/assets/js/historico.js
- frontend/assets/css/historico.css
- opcionalmente frontend/index.html si se mejora el acceso a la zona histórica

## Constraints
- No usar UI externa de la comunidad.
- No introducir frameworks nuevos.
- No romper la landing actual.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en ampliar la UI histórica propia.

## Validation
- La UI histórica muestra partidas recientes por servidor.
- La UI consume exclusivamente la API interna.
- Existen estados de carga, vacío y error.
- La interfaz sigue siendo coherente con el resto del proyecto.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 5 archivos modificados o creados.
- Preferir menos de 240 líneas cambiadas.
## Outcome
- La UI histÃ³rica propia ahora muestra un bloque de partidas recientes por servidor.
- El bloque usa exclusivamente `GET /api/historical/recent-matches`.
- El selector de servidor se comparte con el ranking semanal para mantener consistencia.
- Se cubrieron estados de carga, vacÃ­o y error para esta vista.

## Validation Notes
- `node --check frontend/assets/js/historico.js`
- revisiÃ³n manual de la estructura HTML/CSS para desktop y mobile
