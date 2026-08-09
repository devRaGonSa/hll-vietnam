# TASK-040-randomized-community-clans-section

## Goal
Implementar una sección única de clanes/comunidades en la landing principal, mostrando los clanes indicados con sus logos y enlaces a Discord, en orden aleatorio en cada carga de página.

## Context
La home ya incorpora una sección de clanes/comunidad, pero ahora hay una definición concreta de qué clanes deben aparecer, qué logos deben usarse y qué Discord debe enlazarse en cada caso. La sección debe ser única, clara y mantenible, y el orden de los clanes debe variar aleatoriamente cada vez que se cargue la página.

## Datos a usar
Los clanes/comunidades que deben mostrarse son estos:

1. LCM
   - Discord: `https://discord.gg/9F9S353QZv`
   - Logo: usar la imagen proporcionada para LCM

2. La 129
   - Discord: placeholder por ahora
   - Logo: usar la imagen proporcionada para La 129

3. 250 Hispania
   - Discord: `https://discord.gg/3E62Yb6Aw3`
   - Logo: usar solo el escudo de la imagen proporcionada, quitando la parte de texto `Historia de la 250` y quedándose únicamente con el emblema/escudo

4. H9H
   - Discord: `https://discord.gg/tYnXK7MQjB`
   - Logo: placeholder por ahora

5. BxB
   - Discord: placeholder por ahora
   - Logo: usar la imagen proporcionada para BxB

6. 7dv
   - Discord: `https://discord.gg/3sxNQZwrg6`
   - Logo: usar la imagen proporcionada para 7dv

## Steps
1. Revisar la landing actual y la sección de clanes/comunidad ya existente.
2. Ajustar la sección para que muestre exactamente estos 6 clanes/comunidades y no una lista distinta.
3. Mantener toda la información de los clanes en una estructura de datos clara y mantenible, preferiblemente en JS si eso encaja mejor con el renderizado actual.
4. Implementar la sección para mostrar, como mínimo, por cada clan:
   - logo
   - nombre
   - botón o enlace a Discord
5. Hacer que el orden de aparición de los clanes sea aleatorio en cada carga de página.
6. Asegurar que la aleatorización no rompe la estructura visual ni genera duplicados.
7. Para los clanes con Discord aún no definido (`La 129` y `BxB`), mostrar un estado coherente y no roto, por ejemplo:
   - botón deshabilitado
   - etiqueta `Próximamente`
   - o equivalente visual claro y honesto
8. Para los clanes con logo pendiente (`H9H`), usar un placeholder visual coherente con la estética de la web.
9. Para `250 Hispania`, usar solo el escudo/emblema, sin el texto `Historia de la 250`.
10. Mantener la sección como una única sección de comunidad/clanes en la home, sin duplicarla.
11. Asegurar que la sección funciona correctamente en escritorio y móvil.
12. Mantener la estética coherente con la landing actual.
13. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- frontend/index.html
- frontend/assets/css/styles.css
- frontend/assets/js/main.js
- cualquier archivo actual de datos/renderizado de la sección de clanes si ya existe
- assets actuales relacionados con logos de comunidad

## Expected Files to Modify
- frontend/index.html
- frontend/assets/css/styles.css
- frontend/assets/js/main.js
- opcionalmente un archivo de datos/config si mejora claridad, por ejemplo:
  - frontend/assets/js/community-clans.js
- opcionalmente nuevos assets referenciados correctamente si la implementación los necesita, por ejemplo dentro de:
  - frontend/assets/img/clans/

## Constraints
- No romper la landing actual.
- No crear varias secciones de clanes; debe quedar una sola.
- No introducir frameworks nuevos.
- No depender de widgets externos o iframes de Discord para esta sección.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en la sección de clanes, su contenido real y el orden aleatorio por carga.

## Validation
- La home muestra una única sección de clanes/comunidades.
- Aparecen exactamente estos 6 clanes/comunidades:
  - LCM
  - La 129
  - 250 Hispania
  - H9H
  - BxB
  - 7dv
- El orden cambia aleatoriamente en cada carga de página.
- Los enlaces de Discord correctos funcionan para:
  - LCM
  - 250 Hispania
  - H9H
  - 7dv
- Los clanes sin enlace definitivo no muestran botones rotos.
- `250 Hispania` usa solo el escudo/emblema, sin el texto lateral.
- La sección sigue siendo visualmente coherente y responsive.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 6 archivos modificados o creados.
- Preferir menos de 260 líneas cambiadas.
