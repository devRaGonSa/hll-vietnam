# TASK-036-historical-page-branding-and-copy-cleanup

## Goal
Pulir la página histórica propia del proyecto en branding y copy, eliminando formulaciones que suenan técnicas o poco naturales, añadiendo el logo de la comunidad y reforzando la coherencia visual con la landing principal.

## Context
La página histórica ya es funcional y útil, pero hay varios ajustes de acabado que mejorarían claramente la percepción del producto:
- eliminar la palabra `táctico` del hero de la página histórica
- añadir el logo de la comunidad también en esta página
- sustituir formulaciones con `importado` por textos más naturales como `registrado` o `registradas`
- mantener la coherencia visual con la landing principal

Estos cambios son de UX/copy/branding y no deben alterar la arquitectura histórica ya construida.

## Steps
1. Revisar la página histórica actual y su hero.
2. Eliminar o reformular el texto del hero para quitar la palabra `táctico`.
3. Añadir el logo de la comunidad en la página histórica usando la ruta de asset local ya establecida por el proyecto.
4. Revisar todos los textos visibles relacionados con cobertura o datos históricos y sustituir las referencias a:
   - `importado`
   - `importada`
   - `importados`
   - `importadas`
   por formulaciones más naturales y adecuadas, preferentemente:
   - `registrado`
   - `registrada`
   - `registrados`
   - `registradas`
   o equivalentes mejores si encajan más naturalmente con la UI.
5. Revisar que los nuevos textos no rompan layout, cards, badges o títulos.
6. Mantener la estética coherente con la landing y con la identidad actual del proyecto.
7. No introducir todavía nuevas métricas ni nuevas pestañas en esta task.
8. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- frontend/historico.html
- frontend/assets/css/historico.css
- frontend/assets/js/historico.js
- frontend/index.html
- frontend/assets/css/styles.css
- ai/repo-context.md

## Expected Files to Modify
- frontend/historico.html
- frontend/assets/css/historico.css
- frontend/assets/js/historico.js
- opcionalmente frontend/assets/img/logo.png si solo hace falta referenciarlo correctamente, no reemplazarlo
- opcionalmente documentación mínima si hubiera un cambio visible que merezca reflejarse

## Constraints
- No cambiar la arquitectura de la página histórica.
- No crear páginas externas o dependientes de la comunidad.
- No romper la UI histórica existente.
- No introducir librerías nuevas.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en branding, copy y acabado.

## Validation
- La palabra `táctico` desaparece del hero histórico.
- El logo de la comunidad aparece correctamente en la página histórica.
- Los textos visibles dejan de sonar técnicos o artificiales por el uso de `importado`.
- La página sigue siendo coherente visualmente con la landing.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 4 archivos modificados.
- Preferir menos de 180 líneas cambiadas.
