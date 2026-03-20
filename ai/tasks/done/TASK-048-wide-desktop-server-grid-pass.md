# TASK-048-wide-desktop-server-grid-pass

## Goal
Aprovechar el nuevo ancho de desktop para que el panel de servidores use una rejilla más amplia y cómoda, evitando que las tarjetas sigan viéndose pequeñas o demasiado encerradas.

## Context
Una vez ampliado el shell principal y eliminadas restricciones internas, el panel de servidores debe beneficiarse directamente de ese ancho. Si la rejilla sigue siendo demasiado conservadora, la página seguirá dando sensación de estrechez aunque el contenedor ya sea ancho.

## Steps
1. Revisar la rejilla actual del panel de servidores.
2. Ajustar el grid para que aproveche mejor desktop ancho.
3. Usar una estrategia robusta tipo:
   - `repeat(auto-fit, minmax(360px, 1fr))`
   o equivalente mejor adaptada al diseño actual.
4. Revisar gaps, paddings y anchuras mínimas para evitar tarjetas pequeñas o apretadas.
5. Mantener buen comportamiento en tablet y móvil.
6. No rediseñar la tarjeta; centrarse en cómo la rejilla usa el ancho disponible.

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- frontend/assets/css/styles.css
- frontend/assets/js/main.js
- frontend/index.html

## Expected Files to Modify
- frontend/assets/css/styles.css
- frontend/index.html si hiciera falta alinear clases o wrappers

## Constraints
- No tocar backend.
- No añadir librerías nuevas.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en grid y aprovechamiento del ancho.

## Validation
- El panel de servidores se ve más amplio y mejor repartido en desktop.
- Las tarjetas dejan de sentirse pequeñas o encajadas.
- La UI mantiene buena lectura en tablet y móvil.

## Change Budget
- Preferir menos de 2 archivos modificados.
- Preferir menos de 120 líneas cambiadas.
