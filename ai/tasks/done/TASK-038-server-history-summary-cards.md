# TASK-038-server-history-summary-cards

## Goal
Añadir al backend y al frontend una primera capa de métricas históricas resumidas para los servidores reales, de forma que el panel muestre información más útil que el simple último snapshot.

## Context
La web ya muestra snapshots reales A2S y dispone de histórico persistido. Sin embargo, el valor actual del panel sigue siendo limitado si solo enseña la última captura y una tendencia básica. El siguiente paso lógico es construir resúmenes históricos ligeros a partir de lo ya almacenado, sin convertir aún la landing en un dashboard complejo.

## Steps
1. Revisar los endpoints históricos actuales y el panel de servidores existente.
2. Identificar qué métricas históricas resumidas son viables con los snapshots ya persistidos, por ejemplo:
   - última vez visto online
   - número de capturas recientes
   - promedio reciente de jugadores
   - valor máximo reciente de población
   - tiempo desde la última captura
3. Añadir la capa mínima necesaria en backend para exponer estas métricas de forma clara.
4. Integrar esas métricas en las tarjetas de servidores reales del frontend.
5. Mantener la mejora ligera y coherente con el diseño actual.
6. No introducir cálculos pesados ni analítica compleja.
7. Preservar el comportamiento correcto si aún hay pocos snapshots disponibles.

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- backend/README.md
- backend/app/routes.py
- backend/app/payloads.py
- backend/app/storage.py
- frontend/index.html
- frontend/assets/js/main.js
- frontend/assets/css/styles.css

## Expected Files to Modify
- backend/app/routes.py
- backend/app/payloads.py
- backend/app/storage.py
- frontend/index.html
- frontend/assets/js/main.js
- frontend/assets/css/styles.css

## Constraints
- No rediseñar toda la landing.
- No añadir gráficas complejas.
- No introducir librerías nuevas.
- No romper el fallback actual.
- No hacer cambios destructivos.
- Mantener la mejora centrada en valor histórico resumido.

## Validation
- El backend expone métricas históricas resumidas útiles para servidores reales.
- El frontend las muestra de forma clara y legible.
- La UI sigue funcionando aunque el histórico disponible sea limitado.
- El panel gana valor funcional sin perder claridad.

## Change Budget
- Preferir menos de 6 archivos modificados.
- Preferir menos de 220 líneas cambiadas.
## Outcome
- `backend/app/storage.py` adjunta a cada snapshot mÃ¡s reciente un `history_summary` ligero con capturas recientes, promedio de jugadores, pico, Ãºltima vez visto online y minutos desde la Ãºltima captura.
- `backend/app/payloads.py` expone esas mÃ©tricas en `GET /api/servers/latest` sin abrir un endpoint nuevo.
- `frontend/assets/js/main.js` integra las mÃ©tricas resumidas en las tarjetas reales e histÃ³ricas ya renderizadas por la landing.
- `frontend/assets/css/styles.css` aÃ±ade el bloque visual compacto para mostrar esos resÃºmenes sin convertir la landing en un dashboard pesado.

## Validation Result
- Ejecutado: import directo de `build_server_latest_payload()` desde `backend/`.
- Resultado: el payload devuelve `history_summary` por servidor con valores coherentes incluso cuando hay pocas capturas disponibles.
- Ejecutado: `node --check frontend/assets/js/main.js`.
- Resultado: sintaxis JavaScript vÃ¡lida tras integrar el bloque de mÃ©tricas resumidas.

## Decision Notes
- Las mÃ©tricas histÃ³ricas resumidas se calculan sobre una ventana corta de snapshots recientes y se entregan junto al payload de Ãºltimo estado para mantener el backend simple y evitar analÃ­tica o endpoints adicionales en esta fase.
