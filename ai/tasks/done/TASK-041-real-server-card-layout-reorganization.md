# TASK-041-real-server-card-layout-reorganization

## Goal
Reorganizar internamente las tarjetas de servidores reales para que aprovechen mejor el espacio horizontal, reduzcan compresiÃ³n vertical y mejoren la legibilidad de los datos.

## Context
Las tarjetas actuales contienen informaciÃ³n Ãºtil, pero en una composiciÃ³n demasiado estrecha y alta. Eso hace que varias mÃ©tricas queden apelotonadas, con mala jerarquÃ­a y sensaciÃ³n de desborde. Esta task debe rediseÃ±ar la distribuciÃ³n interna de la tarjeta, no la arquitectura funcional del panel.

## Steps
1. Revisar la estructura HTML y JS que renderiza las tarjetas de servidores reales.
2. Reorganizar la composiciÃ³n interna para que la tarjeta tenga una lectura mÃ¡s horizontal y clara.
3. Priorizar visualmente:
   - nombre del servidor
   - estado
   - botÃ³n Conectar
   - jugadores
   - mapa
   - regiÃ³n
   - Ãºltima captura
   - mÃ©tricas resumidas
4. Reducir altura innecesaria y mejorar la distribuciÃ³n interna de bloques.
5. Mantener la CTA de conexiÃ³n visible y bien integrada.
6. Mejorar el comportamiento de nombres largos y textos densos.
7. No romper el fallback ni la lÃ³gica actual del panel.

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
- No tocar backend salvo alineaciÃ³n mÃ­nima si fuera imprescindible.
- No aÃ±adir librerÃ­as nuevas.
- No romper la CTA Conectar.
- No hacer cambios destructivos.
- Mantener la mejora centrada en layout y legibilidad.

## Validation
- Las tarjetas reales son mÃ¡s legibles y aprovechan mejor el ancho.
- La jerarquÃ­a interna mejora claramente.
- El texto largo deja de sentirse comprimido o desbordado.
- La UI mantiene coherencia visual con el resto de la landing.

## Change Budget
- Preferir menos de 3 archivos modificados.
- Preferir menos de 180 lÃ­neas cambiadas.

## Outcome
- `frontend/assets/js/main.js` reorganiza la tarjeta real en dos zonas: cabecera prioritaria con estado, poblacion y CTA, y cuerpo con quick facts, resumen historico y tendencia.
- `frontend/assets/css/styles.css` adapta la tarjeta a una lectura mas horizontal en desktop y endurece el wrapping de nombres y valores largos.
- No fue necesario tocar `frontend/index.html` ni alinear payloads del backend.

## Validation Result
- Ejecutado: `node --check frontend/assets/js/main.js`.
- Resultado: sintaxis JavaScript valida tras la reorganizacion del render.
- Revisado en codigo: la CTA `Conectar` sigue ligada a `steam://connect/<host>:<game_port>` y solo aparece para snapshots reales A2S.
- Limitacion: no se ejecuto una comprobacion visual automatizada del navegador en esta tarea.

## Decision Notes
- La reduccion de altura se resolvio moviendo resumen y tendencia a una composicion interna mas horizontal, sin cambiar la logica de secciones del panel ni el fallback existente.
