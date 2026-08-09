# TASK-047-remove-nested-width-constraints

## Goal
Eliminar o corregir restricciones internas de anchura que siguen estrechando hero, tráiler y panel de servidores aunque el shell principal se haya ensanchado.

## Context
En la UI actual hay indicios claros de que, además del shell principal, existen wrappers interiores o `max-width` secundarios que mantienen las secciones demasiado estrechas. Esta task debe identificar y eliminar esas restricciones internas para que cada sección ocupe realmente el ancho disponible del carril principal.

## Steps
1. Revisar la estructura HTML y CSS de hero, tráiler y panel de servidores.
2. Identificar wrappers internos con `max-width`, anchuras fijas o márgenes automáticos que estrechen el contenido.
3. Corregir esas restricciones para que:
   - hero
   - tráiler
   - panel de servidores
   usen `width: 100%` dentro del shell principal.
4. Mantener una composición limpia y centrada, sin volver a una columna estrecha.
5. Evitar que un wrapper interno rompa el ancho unificado buscado.
6. No rediseñar secciones; solo liberar el ancho real utilizable.

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- frontend/index.html
- frontend/assets/css/styles.css

## Expected Files to Modify
- frontend/index.html
- frontend/assets/css/styles.css

## Constraints
- No tocar backend.
- No añadir librerías nuevas.
- No hacer cambios destructivos.
- Mantener la estructura visual existente salvo correcciones de anchura.

## Validation
- No quedan wrappers interiores que vuelvan a estrechar las secciones principales.
- Hero, tráiler y servidores ocupan realmente el ancho del shell maestro.
- La sensación de “columna central demasiado angosta” desaparece o se reduce claramente.

## Change Budget
- Preferir menos de 2 archivos modificados.
- Preferir menos de 120 líneas cambiadas.
