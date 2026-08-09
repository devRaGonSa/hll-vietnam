# TASK-036-hide-placeholders-when-real-servers-exist-and-localize-connect-label

## Goal
Ajustar el panel de servidores para ocultar los placeholders o referencias provisionales cuando ya existan snapshots reales A2S utilizables, y cambiar la etiqueta visible del botón de conexión de “Connect” a “Conectar”.

## Context
La landing ya muestra snapshots reales A2S de Comunidad Hispana #01 y #02. En este punto, mantener visibles los placeholders como bloque principal o paralelo degrada la claridad del producto y da una sensación de estado provisional que ya no corresponde al nivel real del sistema. Los placeholders deben quedar como fallback técnico, no como contenido normal cuando haya datos reales disponibles. Además, la CTA visible de conexión debe localizarse al español.

## Steps
1. Revisar el render actual del panel de servidores en frontend.
2. Identificar la lógica que separa:
   - snapshots `real-a2s`
   - snapshots históricos persistidos
   - placeholders o `controlled-fallback`
3. Ajustar la lógica para que:
   - si existen snapshots reales A2S utilizables, solo se muestren esos servidores reales en la vista principal
   - los placeholders queden ocultos en la vista normal
   - el fallback provisional solo se muestre cuando no existan datos reales o el backend no aporte snapshots utilizables
4. Mantener clara la procedencia del dato real sin sobrecargar la UI.
5. Cambiar la etiqueta visible del botón de conexión de:
   - `Connect`
   a:
   - `Conectar`
6. Mantener intacto el uso técnico del enlace `steam://connect/<host>:<game_port>`.
7. Revisar el copy mínimo del bloque para que encaje con una fase más madura del producto.
8. Mantener el ajuste visual contenido, sin rediseñar toda la landing.

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
- No tocar backend salvo referencia documental mínima si fuera imprescindible.
- No romper el fallback cuando no haya datos reales.
- No quitar soporte para placeholders a nivel interno; solo ocultarlos cuando existan snapshots reales utilizables.
- No añadir librerías nuevas.
- No hacer cambios destructivos.
- Mantener el ajuste centrado en claridad de producto y localización de la CTA.

## Validation
- Cuando existen snapshots `real-a2s`, la vista principal del panel muestra solo servidores reales.
- Los placeholders ya no aparecen en la vista normal si hay datos reales disponibles.
- Si no hay datos reales, el fallback sigue funcionando.
- El botón visible muestra “Conectar”.
- La landing gana claridad visual y semántica.

## Change Budget
- Preferir menos de 3 archivos modificados.
- Preferir menos de 140 líneas cambiadas.

## Outcome
- `frontend/assets/js/main.js` filtra la vista principal del panel para mostrar solo snapshots `real-a2s` cuando existen, manteniendo el fallback persistido solo para escenarios sin capturas reales utilizables.
- `frontend/assets/js/main.js` localiza la CTA visible de conexión a `Conectar` sin alterar el esquema técnico `steam://connect/<host>:<game_port>`.
- `frontend/index.html` y `frontend/assets/css/styles.css` ajustan el copy y la presentación base del bloque para que el estado por defecto sea más neutro y menos provisional.

## Validation Result
- Ejecutado: `node --check frontend/assets/js/main.js`.
- Resultado: sintaxis JavaScript válida tras el ajuste de filtrado y localización.
- Revisado en código: la vista enriquecida usa `selectPrimaryServerItems(...)`, por lo que los placeholders quedan ocultos cuando hay snapshots reales y el fallback sigue siendo la ruta visible si no existen capturas reales utilizables.
- Revisado en código: la CTA visible del enlace de conexión muestra `Conectar`.

## Decision Notes
- La ocultación de placeholders se resolvió en la capa de selección de items visibles, sin tocar backend ni eliminar soporte interno de fallback.
