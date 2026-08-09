# TASK-045-simplify-real-server-cards-for-product-ui

## Goal
Simplificar las tarjetas de servidores reales para mostrar solo la informacion mas util para el visitante final, mejorando la claridad y reduciendo ruido visual y tecnico.

## Context
Las tarjetas actuales ya muestran datos reales A2S, pero siguen ensenando informacion que no aporta suficiente valor para la experiencia principal. La tarjeta debe centrarse en lo esencial: nombre, estado, jugadores, mapa, region, ultima captura y CTA de conexion. Cualquier metrica adicional debe ser secundaria o eliminarse si no mejora claramente la lectura.

## Steps
1. Revisar la estructura actual de las tarjetas reales.
2. Reducir la informacion visible principal a:
   - nombre
   - estado
   - jugadores actuales
   - mapa
   - region
   - ultima captura
   - boton Conectar
3. Evaluar si promedio y pico deben quedar como datos secundarios discretos o desaparecer.
4. Eliminar de la tarjeta elementos como:
   - tendencia reciente
   - numero de capturas
   - bloques densos poco utiles
5. Reorganizar la tarjeta para que se lea rapido y con claridad.
6. Mantener una composicion limpia y coherente con el diseno actual.
7. Asegurar buena legibilidad en desktop y movil.

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- frontend/index.html
- frontend/assets/js/main.js
- frontend/assets/css/styles.css
- backend/app/payloads.py

## Expected Files to Modify
- frontend/index.html
- frontend/assets/js/main.js
- frontend/assets/css/styles.css

## Constraints
- No tocar backend salvo alineacion menor si fuera imprescindible.
- No romper la CTA Conectar.
- No anadir librerias nuevas.
- No hacer cambios destructivos.
- Mantener el ajuste centrado en UX de producto final.

## Validation
- Las tarjetas reales muestran solo la informacion mas util y legible.
- Desaparece ruido tecnico innecesario.
- La CTA Conectar sigue visible y clara.
- La UI gana sensacion de producto final.

## Change Budget
- Preferir menos de 3 archivos modificados.
- Preferir menos de 160 lineas cambiadas.

## Outcome
- `frontend/assets/js/main.js` simplifica el render de tarjetas reales a identidad, estado, poblacion, quick facts y CTA, eliminando resumen historico, tendencia y llamadas auxiliares ya innecesarias.
- `frontend/assets/css/styles.css` elimina estilos asociados a bloques tecnicos densos y deja una composicion mas directa para las quick facts.
- No fue necesario tocar backend ni cambiar la CTA `Conectar`.

## Validation Result
- Validado con `node --check frontend/assets/js/main.js`.
- Revisado en codigo: las tarjetas mantienen nombre, estado, jugadores, mapa, region, ultima captura y CTA, y desaparecen tendencia, capturas, promedio y pico.
- Revisado en diff: la task queda limitada a `frontend/assets/js/main.js`, `frontend/assets/css/styles.css` y el archivo de task.

## Decision Notes
- Se opto por eliminar por completo las metricas secundarias en lugar de rebajarlas visualmente, porque seguian cargando la tarjeta y no aportaban suficiente valor a la lectura principal.
