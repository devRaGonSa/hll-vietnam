# TASK-040-full-width-page-shell-and-section-width-rebalance

## Goal
Reorganizar el layout general de la landing para aprovechar mucho mejor el ancho de pÃ¡gina disponible, separando el ancho Ãºtil de las distintas secciones y eliminando la sensaciÃ³n de pÃ¡gina excesivamente estrecha.

## Context
La UI actual ya funciona y muestra datos reales, pero la composiciÃ³n general estÃ¡ demasiado constreÃ±ida en ancho. Esto provoca mucho espacio muerto lateral, reduce el impacto visual del diseÃ±o y comprime en exceso el panel de servidores. La landing necesita una estructura de anchuras mÃ¡s flexible y mÃ¡s coherente con un formato panorÃ¡mico de desktop.

## Steps
1. Revisar la estructura general de contenedores de `frontend/index.html`.
2. Revisar el sistema de anchuras, `max-width`, paddings laterales y shells actuales en `frontend/assets/css/styles.css`.
3. Reorganizar la pÃ¡gina para que no todas las secciones dependan del mismo ancho mÃ¡ximo.
4. Definir al menos una separaciÃ³n clara entre:
   - ancho del hero
   - ancho del trÃ¡iler
   - ancho del panel de servidores
5. Aumentar el ancho Ãºtil del bloque de servidores para aprovechar mejor desktop amplio.
6. Mantener el diseÃ±o responsive y sin romper mÃ³vil o tablet.
7. Preservar la identidad visual actual sin rediseÃ±ar completamente la pÃ¡gina.

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
- No tocar backend.
- No aÃ±adir librerÃ­as nuevas.
- No romper el comportamiento actual del frontend.
- No hacer cambios destructivos.
- Mantener la landing coherente con el tono visual actual.

## Validation
- La pÃ¡gina ocupa mejor el ancho disponible en desktop.
- El panel de servidores gana anchura real.
- El hero y el trÃ¡iler mantienen buen equilibrio visual.
- La UI sigue funcionando correctamente en tablet y mÃ³vil.

## Change Budget
- Preferir menos de 3 archivos modificados.
- Preferir menos de 180 lÃ­neas cambiadas.

## Outcome
- `frontend/assets/css/styles.css` separa el ancho del hero, del bloque de trailer y del panel de servidores con shells independientes.
- El `page-shell` deja de imponer un unico ancho maximo a toda la landing y el panel de servidores gana mas ancho util en desktop.
- La mejora se mantuvo en CSS para no introducir cambios estructurales innecesarios en el HTML.

## Validation Result
- Revisado en diff: el ajuste queda limitado a `frontend/assets/css/styles.css` y al propio archivo de task.
- Revisado en codigo: hero, trailer y panel de servidores usan anchuras maximas distintas y el layout movil conserva los resets responsive existentes.
- Limitacion: no se ejecuto una comprobacion visual automatizada del navegador en esta tarea.

## Decision Notes
- La separacion de shells se resolvio con anchuras por seccion en lugar de crear nuevos wrappers HTML, para mantener la landing estable y reducir riesgo sobre el frontend actual.
