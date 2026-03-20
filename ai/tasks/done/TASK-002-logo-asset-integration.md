# TASK-002-logo-asset-integration

## Goal
Integrar correctamente el logo real del proyecto HLL Vietnam en la landing actual, asegurando que el frontend use un asset local estable y coherente con la identidad visual del proyecto.

## Context
La landing inicial ya existe y actualmente está preparada para mostrar un logo local en `frontend/assets/img/logo.png`. Antes de hacer mejoras visuales adicionales, hay que consolidar la integración del logo real para que el proyecto tenga una base visual correcta, mantenible y consistente.

## Steps
1. Revisar la estructura actual del frontend.
2. Confirmar que existe la ruta esperada para el logo:
   - `frontend/assets/img/logo.png`
3. Si el logo real aún no está en esa ruta, dejar la integración preparada de forma segura sin romper la página.
4. Revisar `frontend/index.html` para asegurar que:
   - usa la ruta local correcta del logo
   - el `alt` del logo es descriptivo y coherente
   - no hay rutas temporales, absolutas o inconsistentes
5. Revisar `frontend/assets/css/styles.css` para asegurar que:
   - el bloque visual del logo tiene un tamaño adecuado
   - mantiene buena presentación en escritorio y móvil
   - no deforma la imagen
6. Corregir cualquier inconsistencia menor relacionada con la carga o presentación del logo.
7. Mantener la landing simple: logo, tráiler y botón de Discord.

## Files to Read First
- frontend/index.html
- frontend/assets/css/styles.css
- docs/project-overview.md
- ai/repo-context.md
- AGENTS.md

## Expected Files to Modify
- frontend/index.html
- frontend/assets/css/styles.css
- opcionalmente `frontend/assets/img/logo.png` si el flujo de la task contempla dejar el asset correctamente ubicado

## Constraints
- No rediseñar toda la landing.
- No añadir nuevas secciones.
- No introducir frameworks ni dependencias nuevas.
- No tocar backend.
- No hacer cambios destructivos.
- Mantener la estética militar sobria ya definida.

## Validation
- La landing referencia el logo local mediante una ruta estable.
- El logo se muestra correctamente sin deformaciones.
- El HTML sigue funcionando al abrirse directamente en navegador.
- La presentación del logo es correcta tanto en móvil como en escritorio.
- No se rompe el tráiler ni el botón de Discord.

## Change Budget
- Preferir menos de 4 archivos modificados.
- Preferir menos de 120 líneas cambiadas.

## Outcome
- Confirmada la existencia del asset local `frontend/assets/img/logo.png`; no fue necesario reemplazarlo ni moverlo.
- `frontend/index.html` mantiene una ruta local estable (`./assets/img/logo.png`) y ahora usa un `alt` más descriptivo junto con dimensiones explícitas para reducir saltos de layout.
- `frontend/assets/css/styles.css` ya no fuerza un contenedor cuadrado para el logo: la imagen conserva su proporción con `max-width` y `max-height`, con ajustes específicos para escritorio y móvil.
- Validación completada mediante revisión del marcado, verificación de la ruta local del logo y revisión de `git diff --name-only`.
- No hay tests de integración configurados para este alcance; la comprobación aplicable fue manual sobre HTML/CSS y compatibilidad con apertura directa en navegador.
