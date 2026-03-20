# TASK-039-community-clans-section-on-landing

## Goal
Añadir una nueva sección en la página principal para mostrar clanes/comunidades aliadas o relacionadas, con sus logos y un enlace hacia sus respectivos Discords.

## Context
Además de los servidores y del histórico, se quiere que la home tenga una sección específica de clanes donde puedan verse logos representativos y un link hacia cada Discord. Esta sección debe integrarse en la landing sin romper su simplicidad ni convertirse en un directorio desordenado.

## Steps
1. Revisar la landing actual y decidir una ubicación razonable para la nueva sección de clanes.
2. Diseñar una sección clara y visualmente coherente con el resto de la home.
3. Preparar una estructura de datos simple y mantenible para los clanes mostrados, por ejemplo:
   - nombre
   - logo
   - enlace Discord
   - descripción breve opcional
4. Implementar la sección mostrando al menos:
   - logo de cada clan
   - nombre
   - botón o link claro hacia su Discord
5. Mantener la solución suficientemente flexible para añadir o quitar clanes más adelante sin reescribir la sección completa.
6. Asegurar que la sección funciona bien en escritorio y móvil.
7. No incrustar widgets completos de Discord salvo que ya estén expresamente aprobados; en esta task basta con enlaces claros al servidor Discord.
8. Mantener la landing limpia y visualmente consistente.
9. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- frontend/index.html
- frontend/assets/css/styles.css
- frontend/assets/js/main.js
- ai/repo-context.md

## Expected Files to Modify
- frontend/index.html
- frontend/assets/css/styles.css
- frontend/assets/js/main.js
- opcionalmente un archivo de datos/config simple en frontend si mejora claridad, por ejemplo:
  - frontend/assets/js/community-clans.js
- opcionalmente assets de logos si se dejan preparados o referenciados correctamente

## Constraints
- No romper la landing actual.
- No recargar la home con demasiada información.
- No depender de páginas externas como iframes para esta sección.
- No introducir frameworks nuevos.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en una sección limpia, visual y fácil de mantener.

## Validation
- Existe una nueva sección de clanes en la página principal.
- Cada clan mostrado tiene logo y enlace claro a su Discord.
- La sección es coherente con el estilo de la landing.
- La estructura permite mantener y ampliar la lista de clanes razonablemente.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 5 archivos modificados o creados.
- Preferir menos de 240 líneas cambiadas.
