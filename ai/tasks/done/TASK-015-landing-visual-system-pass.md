# TASK-015-landing-visual-system-pass

## Goal
Realizar una pasada de sistema visual sobre la landing de HLL Vietnam para reforzar identidad, consistencia, contraste y jerarquia general, manteniendo el alcance actual del producto y sin cambiar la arquitectura funcional.

## Context
La landing ya cuenta con logo, trailer, CTA de Discord, estado de backend y panel provisional de servidores actuales de Hell Let Loose. La base funcional existe, pero ahora hace falta una pasada centrada unicamente en calidad visual para que la web tenga una presentacion mas solida, coherente y atractiva dentro del tono militar/tactico del proyecto.

## Steps
1. Revisar la composicion visual global de la landing actual.
2. Revisar la paleta actual, contraste, espaciados, tipografias, contenedores y ritmo vertical.
3. Refinar el sistema visual general sin redisenar por completo la pagina.
4. Mejorar:
   - jerarquia tipografica
   - espaciado entre bloques
   - consistencia entre tarjetas y paneles
   - contraste entre fondo, texto y elementos destacados
   - sensacion visual militar sobria y cinematografica
5. Mantener una estetica oscura, tactica y limpia, evitando recargar la pagina.
6. Asegurar que todos los bloques principales compartan un lenguaje visual coherente.
7. Validar que el resultado siga funcionando bien en escritorio y movil.
8. No cambiar el alcance funcional del producto.

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- docs/project-overview.md
- frontend/index.html
- frontend/assets/css/styles.css
- frontend/assets/js/main.js

## Expected Files to Modify
- frontend/index.html
- frontend/assets/css/styles.css

## Constraints
- No anadir nuevas funcionalidades.
- No cambiar endpoints ni logica backend.
- No introducir librerias nuevas.
- No cambiar el flujo funcional de la landing.
- No reescribir toda la estructura HTML salvo ajustes razonables para mejorar composicion.
- No hacer cambios destructivos.
- Mantener el diseno dentro del tono HLL Vietnam.

## Validation
- La landing tiene una apariencia mas coherente y profesional.
- La jerarquia visual es mas clara.
- El contraste y la legibilidad mejoran.
- La identidad militar/tactica queda reforzada.
- No se rompe ninguna funcionalidad existente.
- La landing sigue viendose correctamente en movil y escritorio.

## Change Budget
- Preferir menos de 3 archivos modificados.
- Preferir menos de 220 lineas cambiadas.

## Outcome
- Se reforzo el sistema visual general de la landing sin cambiar su alcance funcional.
- Se ajusto la jerarquia visual entre hero, panel de trailer y panel de servidores para que compartan mejor lenguaje visual.
- Se mejoraron contraste, ritmo vertical, bordes, sombras y consistencia de contenedores dentro del tono militar sobrio del proyecto.

## Validation Notes
- `git diff --name-only -- frontend/index.html frontend/assets/css/styles.css` devuelve solo los archivos esperados por la task.
- Se reviso el CSS para mantener compatibilidad responsive en escritorio y movil mediante los breakpoints existentes.
- No se cambiaron endpoints, logica backend ni comportamiento funcional de la landing.
- No hay pruebas automaticas configuradas para este ajuste visual; la validacion disponible en esta task es revision de alcance y consistencia del marcado y CSS.
