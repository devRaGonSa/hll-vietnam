# TASK-020-component-surface-polish

## Goal
Pulir visualmente superficies y componentes de la landing de HLL Vietnam para mejorar calidad percibida, consistencia y acabado en tarjetas, chips, badges, contenedores y detalles de UI.

## Context
La landing ya tiene una estructura visual bastante competente, pero aún puede ganar acabado en microdetalles de interfaz. El panel de servidores, las tarjetas, los chips de estado y los contenedores principales necesitan una pasada de consistencia visual para que el conjunto se sienta más refinado y más uniforme.

## Steps
1. Revisar los componentes visuales actuales de la landing.
2. Evaluar consistencia en:
   - radios
   - bordes
   - sombras
   - chips
   - badges de estado
   - tarjetas
   - barras de ocupación
   - encabezados de panel
3. Refinar esos elementos para que compartan un lenguaje visual más sólido y coherente.
4. Mejorar calidad percibida sin añadir complejidad innecesaria.
5. Asegurar que el panel de servidores y los componentes de apoyo se lean mejor tanto en estado estático como hidratado por JS.
6. Mantener clara la jerarquía entre componentes primarios y secundarios.
7. Validar responsive y consistencia entre escritorio y móvil.
8. No tocar el contrato del backend ni el contenido funcional de los payloads.

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- frontend/index.html
- frontend/assets/css/styles.css
- frontend/assets/js/main.js
- backend/app/payloads.py

## Expected Files to Modify
- frontend/index.html
- frontend/assets/css/styles.css
- frontend/assets/js/main.js

## Constraints
- No cambiar endpoints.
- No cambiar payloads backend.
- No añadir librerías nuevas.
- No romper el fallback estático.
- No rediseñar completamente la landing.
- No hacer cambios destructivos.
- Mantener el ajuste centrado en UI y acabado visual.

## Validation
- Las superficies y componentes se ven más coherentes y mejor acabados.
- Chips, badges y tarjetas tienen una presentación más limpia y consistente.
- El panel de servidores gana claridad y calidad visual.
- La landing mantiene su funcionamiento actual.
- La mejora se aprecia en desktop y mobile.

## Change Budget
- Preferir menos de 3 archivos modificados.
- Preferir menos de 190 líneas cambiadas.
