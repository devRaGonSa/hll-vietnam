# TASK-043-unified-page-shell-and-section-width-system

## Goal
Unificar el sistema de anchuras de la pagina para que hero, trailer y panel de servidores compartan el mismo ancho util y se perciban como parte de una misma experiencia visual, eliminando la sensacion actual de secciones con tamanos distintos.

## Context
La UI actual ya funciona y muestra datos reales, pero las secciones principales no comparten una anchura consistente. Esto hace que la pagina se sienta fragmentada y reduce la sensacion de producto final. El objetivo de esta task es definir un unico sistema de shell/layout para las secciones principales y aplicarlo de forma consistente.

## Steps
1. Revisar la estructura actual de shells, contenedores y max-width del frontend.
2. Identificar diferencias de ancho entre:
   - hero
   - bloque del trailer
   - bloque de servidores
3. Definir un unico ancho maestro para las secciones principales en desktop.
4. Hacer que hero, trailer y panel de servidores usen el mismo carril visual principal.
5. Ajustar margenes laterales, paddings y separacion vertical para evitar sensacion de fragmentacion.
6. Mantener el comportamiento responsive correcto en tablet y movil.
7. No redisenar el contenido, solo el sistema de layout y anchuras.

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
- No anadir librerias nuevas.
- No hacer cambios destructivos.
- Mantener la identidad visual actual.
- Mantener el trabajo centrado en shell/layout.

## Validation
- Hero, trailer y panel de servidores comparten el mismo ancho util en desktop.
- La pagina se percibe mas unificada.
- No quedan secciones visualmente demasiado estrechas respecto a otras.
- El responsive sigue funcionando.

## Change Budget
- Preferir menos de 3 archivos modificados.
- Preferir menos de 180 lineas cambiadas.

## Outcome
- `frontend/index.html` introduce un `panel__shell` comun en trailer y servidores para que ambas secciones compartan el mismo carril interior.
- `frontend/assets/css/styles.css` reemplaza los anchos independientes de hero, trailer y servidores por un sistema unificado con `--page-shell-width` y `--panel-content-width`.
- El ajuste se mantuvo centrado en layout, paddings y separacion vertical, sin redisenar el contenido.

## Validation Result
- Revisado en diff: la task queda limitada a `frontend/index.html`, `frontend/assets/css/styles.css` y el archivo de task, dentro del scope esperado.
- Revisado en codigo: hero, trailer y panel de servidores pasan a compartir un mismo ancho maestro en desktop y un mismo carril interior para el contenido principal.
- El responsive existente se conserva con los breakpoints moviles previos y con padding especifico para paneles en `max-width: 640px`.

## Decision Notes
- Se unifico el sistema de shell a nivel de seccion y de carril interior en lugar de tocar el contenido de cada bloque, para cumplir el objetivo visual sin abrir un rediseno mayor.
