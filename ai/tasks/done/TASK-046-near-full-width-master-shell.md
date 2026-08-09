# TASK-046-near-full-width-master-shell

## Goal
Sustituir la columna central demasiado estrecha por un shell maestro mucho más ancho, de forma que la landing use casi todo el ancho útil de desktop y reduzca drásticamente el espacio vacío lateral.

## Context
La UI ya unificó las secciones bajo un mismo sistema de anchura, pero ese sistema sigue siendo demasiado estrecho. El resultado es una página encajada en el centro con mucho espacio muerto a izquierda y derecha. El objetivo de esta task es ampliar el carril principal de la landing hasta un ancho cercano al total útil de la ventana, manteniendo márgenes razonables.

## Steps
1. Revisar el shell principal actual y cualquier `max-width` asociado.
2. Sustituir el ancho maestro actual por uno claramente más amplio en desktop.
3. Usar una referencia tipo:
   - `width: min(1600px, calc(100vw - 64px))`
   o equivalente coherente con el diseño actual.
4. Mantener márgenes laterales razonables sin dejar la web pegada a los bordes.
5. Asegurar que el comportamiento responsive en tablet y móvil siga siendo correcto.
6. No rediseñar contenidos; solo ampliar el carril principal de la landing.

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- frontend/index.html
- frontend/assets/css/styles.css

## Expected Files to Modify
- frontend/assets/css/styles.css
- frontend/index.html si fuera necesario alinear wrappers

## Constraints
- No tocar backend.
- No añadir librerías nuevas.
- No hacer cambios destructivos.
- Mantener la identidad visual actual.
- Mantener el trabajo centrado en el shell principal.

## Validation
- La página usa mucho mejor el ancho disponible en desktop.
- Disminuye claramente el espacio vacío lateral.
- Hero, tráiler y servidores siguen alineados en un mismo carril visual.
- Tablet y móvil no se rompen.

## Change Budget
- Preferir menos de 2 archivos modificados.
- Preferir menos de 120 líneas cambiadas.
