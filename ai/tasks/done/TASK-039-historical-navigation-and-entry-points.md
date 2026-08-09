# TASK-039-historical-navigation-and-entry-points

## Goal
Añadir puntos de entrada y navegación razonables hacia la zona histórica propia del proyecto sin romper la simplicidad actual de la landing.

## Context
Si el proyecto empieza a tener una UI histórica propia, hace falta que el usuario pueda llegar a ella con una navegación clara. Esta task debe resolver ese acceso sin convertir la landing en una aplicación compleja ni depender de enlaces a páginas externas de la comunidad.

## Steps
1. Revisar la landing actual y la UI histórica creada.
2. Diseñar uno o más puntos de entrada razonables hacia la zona histórica propia.
3. Añadir enlaces o CTAs discretos y coherentes para acceder al histórico.
4. Mantener la simplicidad de la landing.
5. No sustituir los botones `Histórico` actuales del panel de servidores si siguen teniendo sentido como acceso al scoreboard externo; solo añadir navegación propia del proyecto donde aporte valor.
6. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- frontend/index.html
- frontend/assets/css/styles.css
- frontend/assets/js/main.js
- frontend/historico.html
- frontend/assets/css/historico.css
- frontend/assets/js/historico.js

## Expected Files to Modify
- frontend/index.html
- frontend/assets/css/styles.css
- opcionalmente frontend/assets/js/main.js
- opcionalmente la propia UI histórica si requiere ajustes de navegación

## Constraints
- No recargar la landing con demasiada navegación.
- No romper la landing actual.
- No depender de URLs de la comunidad como navegación principal del producto.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en accesos claros y ligeros.

## Validation
- Existe una forma clara de acceder a la zona histórica propia.
- La landing mantiene su simplicidad.
- No se rompe el flujo actual de usuario.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 4 archivos modificados.
- Preferir menos de 160 líneas cambiadas.
## Outcome
- Se aÃ±adieron CTAs discretos hacia `frontend/historico.html` en la hero y en el panel de servidores.
- Se aÃ±adiÃ³ un enlace de vuelta desde la vista histÃ³rica a la landing.
- Se preservaron los botones actuales `Historico` hacia scoreboards externos en las cards de servidores.

## Validation Notes
- revisiÃ³n de `frontend/index.html` y `frontend/assets/css/styles.css` para mantener simplicidad y coherencia visual
- `node --check frontend/assets/js/historico.js`
