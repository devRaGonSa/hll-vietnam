# TASK-016-hero-logo-and-trailer-cinematic-polish

## Goal
Mejorar visualmente el bloque principal de la landing de HLL Vietnam, con foco en hero, logo y trailer, para darle una presencia mas cinematografica, mas inmersiva y mas propia de una comunidad tactica.

## Context
El usuario quiere priorizar el ajuste visual. El hero actual ya funciona, pero debe ganar impacto sin perder simplicidad. El logo debe sentirse mas protagonista, el bloque del trailer debe integrarse mejor en la composicion y el conjunto debe transmitir mejor el tono del proyecto.

## Steps
1. Revisar la composicion actual del hero.
2. Revisar el tratamiento visual del logo:
   - tamano
   - posicion
   - marco
   - sombra
   - integracion con el fondo
3. Revisar el tratamiento visual del trailer:
   - contenedor
   - marco
   - separacion respecto al resto
   - equilibrio con el CTA y el titulo
4. Mejorar la presencia del bloque principal sin anadir secciones nuevas.
5. Reforzar:
   - impacto inicial
   - sensacion de identidad
   - claridad del CTA principal
   - integracion visual entre logo, titulo y video
6. Mantener el diseno sobrio, sin caer en efectos exagerados.
7. Validar que la composicion siga siendo responsive y estable.

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- frontend/index.html
- frontend/assets/css/styles.css
- frontend/assets/js/main.js

## Expected Files to Modify
- frontend/index.html
- frontend/assets/css/styles.css

## Constraints
- No cambiar la ruta del logo.
- No cambiar el enlace de Discord.
- No cambiar el enlace del trailer.
- No anadir nuevas funcionalidades.
- No romper el fallback actual.
- No usar librerias nuevas.
- No hacer cambios destructivos.
- Mantener la landing simple.

## Validation
- El hero tiene mas presencia visual.
- El logo se percibe mejor integrado y mas protagonista.
- El trailer se siente mejor enmarcado dentro del diseno.
- El CTA sigue siendo claro y visible.
- El resultado mantiene coherencia con el tono militar/tactico del proyecto.
- La composicion funciona en desktop y mobile.

## Change Budget
- Preferir menos de 2 archivos modificados.
- Preferir menos de 180 lineas cambiadas.

## Outcome
- Se reorganizo el bloque principal para agrupar mejor estado backend y CTA sin cambiar su funcionamiento.
- Se reforzo el tratamiento visual del logo con un marco mas trabajado, sombras mas controladas y una mejor integracion con el fondo del hero.
- Se ajusto el panel de trailer para que se sienta mas cinematografico y mejor conectado con la identidad visual del hero.

## Validation Notes
- `git diff --name-only -- frontend/index.html frontend/assets/css/styles.css` devuelve solo los archivos esperados por la task.
- Se confirmo que no se cambiaron la ruta del logo, el enlace de Discord ni la URL del trailer.
- La task se mantuvo en cambios de composicion y estilo; no se altero el fallback ni la logica existente.
- No hay pruebas automaticas especificas para esta composicion; la validacion disponible es revision estructural de HTML/CSS y del alcance del diff.
