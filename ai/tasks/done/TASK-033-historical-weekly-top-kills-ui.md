# TASK-033-historical-weekly-top-kills-ui

## Goal
Crear la primera UI histórica propia del proyecto para mostrar el ranking de jugadores con más kills de la última semana por servidor, consumiendo la API histórica interna del backend y sin depender de páginas externas de la comunidad.

## Context
El proyecto ya dispone de:
- live status de servidores vía A2S
- capa histórica propia persistida
- validación de calidad histórica completada
- endpoint histórico `GET /api/historical/weekly-top-kills`

Con la calidad del histórico ya validada, el siguiente paso es exponer una primera vista propia y útil para el usuario final. Esta UI debe ser del propio proyecto, no una duplicación o incrustación de la web de la comunidad.

## Steps
1. Revisar el endpoint actual `GET /api/historical/weekly-top-kills` y su payload real.
2. Diseñar una primera UI histórica propia, simple y clara, para mostrar rankings semanales.
3. Implementar esta UI en una página propia del proyecto, por ejemplo:
   - `frontend/historico.html`
   o una ruta equivalente coherente con la estructura actual del frontend.
4. Añadir un selector o control claro para alternar entre los 2 servidores reales de la comunidad.
5. Consumir la API histórica propia del backend, sin depender de URLs públicas de la comunidad.
6. Mostrar, como mínimo:
   - posición
   - nombre de jugador
   - kills semanales
   - servidor seleccionado
   - rango temporal usado si el payload lo expone o puede presentarse de forma clara
7. Añadir estados de:
   - carga
   - vacío
   - error
   - sin datos históricos suficientes
8. Mantener la estética coherente con la landing actual.
9. No mezclar esta vista con estado live A2S salvo referencia mínima si fuera útil.
10. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- docs/historical-domain-model.md
- docs/historical-data-quality-notes.md
- backend/README.md
- backend/app/routes.py
- backend/app/payloads.py
- frontend/index.html
- frontend/assets/css/styles.css
- frontend/assets/js/main.js

## Expected Files to Modify
- uno o más archivos nuevos de frontend para esta vista, por ejemplo:
  - frontend/historico.html
  - frontend/assets/js/historico.js
  - frontend/assets/css/historico.css
- opcionalmente frontend/index.html si se añade un enlace de acceso razonable a la nueva vista
- opcionalmente documentación mínima si hay que reflejar la nueva pantalla propia

## Constraints
- No usar páginas de la comunidad como UI del producto.
- No incrustar ni duplicar HTML externo.
- No romper la landing actual.
- No introducir frameworks nuevos.
- No hacer cambios destructivos.
- Mantener la solución centrada en una primera UI histórica útil y clara.

## Validation
- Existe una primera página histórica propia del proyecto.
- La página consume `GET /api/historical/weekly-top-kills`.
- El usuario puede alternar entre los 2 servidores.
- La UI muestra posiciones, jugadores y kills de forma clara.
- Existen estados de loading, empty y error.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 6 archivos modificados o creados.
- Preferir menos de 260 líneas cambiadas.
## Outcome
- Se creÃ³ `frontend/historico.html` como primera UI histÃ³rica propia del proyecto.
- La vista consume `GET /api/historical/weekly-top-kills` desde `frontend/assets/js/historico.js`.
- Se aÃ±adieron estados de carga, vacÃ­o, error y mensaje de datos histÃ³ricos insuficientes.
- El selector permite alternar entre `comunidad-hispana-01` y `comunidad-hispana-02`.

## Validation Notes
- `python -m compileall app`
- comprobaciÃ³n local de payload con `build_weekly_top_kills_payload(limit=3, server_id='comunidad-hispana-01')`
- `node --check frontend/assets/js/historico.js`
