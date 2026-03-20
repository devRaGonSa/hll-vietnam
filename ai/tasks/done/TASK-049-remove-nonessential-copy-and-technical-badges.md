# TASK-049-remove-nonessential-copy-and-technical-badges

## Goal
Eliminar de la landing los textos descriptivos y etiquetas tecnicas que no aportan valor al usuario final, dejando una interfaz mas limpia, directa y orientada a producto final.

## Context
La UI ya esta en una fase suficientemente madura como para prescindir de copy de presentacion y de labels internos o tecnicos. Actualmente siguen apareciendo textos de relleno o de tono demasiado explicativo, asi como etiquetas como "Snapshot real A2S", que no deberian estar visibles en la vista principal publica.

## Steps
1. Revisar el hero, bloque de trailer y bloque de servidores.
2. Eliminar o simplificar textos descriptivos no esenciales, incluyendo ejemplos como:
   - descripciones explicativas del trailer
   - copy redundante del bloque de servidores
   - textos internos de validacion o sistema
3. Eliminar de las tarjetas reales etiquetas tecnicas como:
   - "Snapshot real A2S"
4. Revisar tambien chips o badges secundarios que aporten poco valor al usuario final.
5. Mantener solo el texto minimo necesario para entender cada seccion.
6. Preservar claridad y estetica sin dejar la pagina vacia ni fria.
7. No tocar backend en esta task.

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- frontend/index.html
- frontend/assets/js/main.js
- frontend/assets/css/styles.css

## Expected Files to Modify
- frontend/index.html
- frontend/assets/js/main.js
- frontend/assets/css/styles.css

## Constraints
- No tocar backend.
- No eliminar informacion util de servidor como mapa, jugadores, region, estado, ultima actualizacion y CTA.
- No anadir librerias nuevas.
- No hacer cambios destructivos.
- Mantener el ajuste centrado en copy/UI.

## Validation
- Desaparecen textos descriptivos innecesarios.
- Desaparecen etiquetas tecnicas como "Snapshot real A2S".
- La pagina se percibe mas limpia y mas finalista.
- La informacion util del servidor sigue intacta.

## Change Budget
- Preferir menos de 3 archivos modificados.
- Preferir menos de 120 lineas cambiadas.

## Outcome
- `frontend/index.html` elimina copy descriptivo del hero y del bloque de trailer, simplifica el encabezado de servidores y quita etiquetas secundarias en las tarjetas estaticas.
- `frontend/assets/js/main.js` sustituye textos tecnicos por textos de producto mas directos y elimina labels internos visibles en tarjetas y estados del bloque de servidores.
- `frontend/assets/css/styles.css` elimina el estilo del texto descriptivo del hero ya retirado del markup.

## Validation Result
- Validado con `node --check frontend/assets/js/main.js`.
- Verificado con `rg` que ya no quedan labels visibles como `Snapshot real A2S`, `Fallback estatico`, `Servidor de referencia` o equivalentes en `frontend/`.
- Revisado en diff: la task queda limitada a `frontend/index.html`, `frontend/assets/js/main.js`, `frontend/assets/css/styles.css` y este archivo de task. El cambio no toca backend.

## Decision Notes
- Se mantuvo una nota breve en el bloque de servidores para no dejar la seccion fria, pero se reescribio a una forma claramente orientada a usuario final y sin lenguaje interno del sistema.
