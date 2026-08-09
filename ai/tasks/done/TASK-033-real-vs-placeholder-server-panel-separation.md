# TASK-033-real-vs-placeholder-server-panel-separation

## Goal
Mejorar la claridad visual y funcional del panel de servidores separando o priorizando de forma más evidente los snapshots reales A2S frente a los placeholders controlados.

## Context
El panel de servidores ya consume datos del backend y actualmente mezcla snapshots reales persistidos con tarjetas de fallback controlado. El sistema funciona, pero ahora conviene dejar visualmente más claro qué servidores son reales y cuáles siguen siendo referencias provisionales.

## Steps
1. Revisar el panel actual de servidores y su lógica de renderizado.
2. Identificar cómo distingue actualmente el frontend entre:
   - `real-a2s`
   - `controlled-fallback`
   - histórico persistido
3. Mejorar la composición del panel para que los snapshots reales queden más destacados o separados de los placeholders.
4. Mantener el cambio contenido y coherente con el diseño actual.
5. Asegurar que la información de procedencia siga siendo clara.
6. No eliminar el fallback si todavía es útil para el proyecto.
7. No rediseñar la landing completa.

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
- No tocar backend salvo si una referencia documental mínima fuera imprescindible.
- No eliminar soporte para fallback.
- No introducir librerías nuevas.
- No hacer cambios destructivos.
- Mantener la mejora centrada en claridad de datos y jerarquía visual.

## Validation
- El panel distingue mejor entre servidores reales y placeholders.
- Los snapshots reales ganan prioridad o separación visual clara.
- El fallback sigue funcionando.
- La landing mantiene coherencia visual.

## Change Budget
- Preferir menos de 3 archivos modificados.
- Preferir menos de 160 líneas cambiadas.
## Outcome
- `frontend/assets/js/main.js` separa el render historico en dos bloques: `Snapshots reales A2S` y `Referencia provisional e historico auxiliar`, priorizando arriba los snapshots reales.
- `frontend/assets/js/main.js` etiqueta cada tarjeta persistida como `Snapshot real A2S` o `Referencia persistida` segun `snapshot_origin`, manteniendo el fallback sin eliminarlo.
- `frontend/assets/css/styles.css` refuerza la separacion visual con encabezados de seccion y variantes de tarjeta diferenciadas para reales y placeholders.

## Validation Result
- Ejecutado: `node --check frontend/assets/js/main.js`.
- Resultado: sintaxis JavaScript valida tras introducir el render por secciones.
- Revisado en codigo: el panel renderiza una seccion prioritaria `Snapshots reales A2S` y una seccion separada para referencia/fallback, sin romper la grilla existente.

## Decision Notes
- La separacion se implementa dentro del mismo panel para mantener el alcance pequeno y evitar un redisenio estructural de la landing.
