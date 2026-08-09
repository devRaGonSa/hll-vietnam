# TASK-003-landing-minimal-polish

## Goal
Mejorar visualmente la landing actual de HLL Vietnam con un pulido minimo y controlado, reforzando la identidad militar y la claridad visual sin cambiar el alcance funcional de la pagina.

## Context
La landing ya tiene los tres elementos principales del alcance actual: logo local, boton de Discord y trailer embebido. Tras integrar correctamente el asset del logo, el siguiente paso es mejorar la presentacion general para que la pagina tenga una apariencia mas solida, mas limpia y mas coherente con la tematica del proyecto, sin anadir nuevas secciones ni complejidad innecesaria.

## Steps
1. Revisar la estructura actual de `frontend/index.html`.
2. Revisar los estilos actuales en `frontend/assets/css/styles.css`.
3. Mejorar la jerarquia visual del bloque principal:
   - logo
   - titulo principal
   - subtitulo, si existe
   - boton de Discord
   - bloque del trailer
4. Ajustar espaciados, tamanos, anchuras y alineaciones para mejorar legibilidad.
5. Reforzar la identidad visual militar sobria:
   - paleta oscura
   - acentos controlados
   - mejor contraste
   - sensacion tactica/cinematica sin recargar
6. Mejorar el contenedor del video para que se vea mas integrado en la composicion general.
7. Verificar que la landing siga funcionando correctamente en escritorio y movil.
8. Mantener el alcance estricto actual, sin anadir nuevas funcionalidades ni secciones.

## Files to Read First
- frontend/index.html
- frontend/assets/css/styles.css
- docs/project-overview.md
- ai/repo-context.md
- AGENTS.md

## Expected Files to Modify
- frontend/index.html
- frontend/assets/css/styles.css

## Constraints
- No anadir nuevas secciones de contenido.
- No tocar backend.
- No introducir frameworks ni librerias nuevas.
- No modificar la ruta del logo.
- No cambiar el enlace de Discord.
- No cambiar el trailer.
- No hacer cambios destructivos.
- Mantener el HTML funcional abriendose directamente en navegador.

## Validation
- La landing se ve mas solida y ordenada visualmente.
- Se mantiene el enfoque minimo: logo, identidad, Discord y trailer.
- El logo sigue cargando desde `./assets/img/logo.png`.
- El boton de Discord sigue visible y destacado.
- El trailer sigue funcionando correctamente.
- La presentacion sigue siendo responsive.
- No se anaden elementos fuera del alcance actual.

## Change Budget
- Preferir menos de 3 archivos modificados.
- Preferir menos de 180 lineas cambiadas.

## Outcome
- `frontend/index.html` mantiene el contenido original de la landing y solo anade hooks de estilo para reforzar la jerarquia visual del bloque principal.
- `frontend/assets/css/styles.css` mejora composicion, contraste, espaciados y tratamiento del bloque de video con una direccion mas sobria y tactica, sin introducir nuevas secciones ni funcionalidades.
- Se mantuvieron sin cambios la ruta del logo (`./assets/img/logo.png`), el enlace de Discord y el `iframe` del trailer.
- Validacion completada mediante revision del HTML/CSS resultante y `git diff --name-only`, confirmando que el alcance quedo limitado a los archivos esperados.
- No hay tests de integracion configurados para este alcance; la validacion aplicable fue manual sobre compatibilidad de HTML/CSS para apertura directa en navegador y comportamiento responsive esperado.
