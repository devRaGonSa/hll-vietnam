# TASK-039-real-server-panel-data-density-pass

## Goal
Mejorar la densidad informativa y la claridad de las tarjetas de servidores reales, aprovechando mejor los datos ya disponibles sin recargar visualmente la landing.

## Context
Tras ocultar los placeholders cuando existen snapshots reales y preparar una CTA de conexión en español, el panel real ya tiene buena base. Sin embargo, todavía puede ganar valor mostrando mejor la información disponible y organizando mejor la jerarquía interna de las tarjetas.

## Steps
1. Revisar la composición actual de las tarjetas de servidores reales.
2. Revisar qué datos ya están disponibles o pasarán a estar disponibles tras la task de resúmenes históricos.
3. Mejorar la jerarquía interna de cada tarjeta:
   - nombre
   - estado
   - mapa
   - jugadores
   - región
   - última captura
   - CTA
   - métricas resumidas si existen
4. Hacer que la tarjeta transmita más información útil sin volverse pesada.
5. Mantener coherencia visual con la landing actual.
6. Mejorar legibilidad en desktop y móvil.
7. No rediseñar toda la página ni añadir nuevas secciones grandes.

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- frontend/index.html
- frontend/assets/js/main.js
- frontend/assets/css/styles.css
- backend/app/payloads.py
- backend/app/routes.py

## Expected Files to Modify
- frontend/index.html
- frontend/assets/js/main.js
- frontend/assets/css/styles.css

## Constraints
- No tocar backend salvo si es estrictamente necesario por alineación menor con payloads ya existentes.
- No añadir librerías nuevas.
- No romper el fallback ni la CTA Conectar.
- No hacer cambios destructivos.
- Mantener la mejora centrada en claridad, jerarquía y densidad informativa.

## Validation
- Las tarjetas reales muestran mejor la información útil.
- La jerarquía interna mejora.
- La experiencia visual sigue siendo limpia.
- El panel se entiende mejor en desktop y móvil.

## Change Budget
- Preferir menos de 3 archivos modificados.
- Preferir menos de 180 líneas cambiadas.
## Outcome
- `frontend/assets/js/main.js` reorganiza la jerarquÃ­a interna de las tarjetas reales para destacar nombre, estado, poblaciÃ³n actual, mapa, regiÃ³n, Ãºltima captura, CTA y mÃ©tricas resumidas.
- `frontend/assets/css/styles.css` refuerza la densidad informativa con una columna compacta de estado/poblaciÃ³n y una fila de quick facts legible en desktop y mÃ³vil.
- La CTA `Conectar`, la tendencia reciente y el fallback existente se mantienen operativos.

## Validation Result
- Ejecutado: `node --check frontend/assets/js/main.js`.
- Resultado: sintaxis JavaScript vÃ¡lida tras el ajuste de jerarquÃ­a y densidad visual.
- Revisado en cÃ³digo: la versiÃ³n enriquecida de la tarjeta conserva `steam://connect/<host>:<game_port>` para snapshots reales y mantiene el fallback cuando no hay datos reales utilizables.

## Decision Notes
- La mejora de densidad se concentrÃ³ dentro de la tarjeta existente, sin aÃ±adir nuevas secciones grandes ni cambiar la arquitectura del panel.
