# TASK-018-hero-layout-rebalance

## Goal
Reequilibrar la composición visual del hero de la landing de HLL Vietnam para darle más impacto, reducir sensación de vacío vertical y mejorar la relación entre logo, titular, subtítulo y CTA principal.

## Context
La landing ya tiene una base visual sólida, pero el hero actual presenta varios puntos de mejora: demasiado espacio vertical, un titular muy dominante partido en varias líneas, un logo con menos protagonismo del deseado y una composición general menos potente que el resto de la página. Esta task debe centrarse únicamente en recomponer el bloque principal para que se perciba como una cabecera premium, más compacta y más cinematográfica, sin cambiar el alcance funcional actual.

## Steps
1. Revisar la composición actual del hero en la landing.
2. Evaluar el equilibrio visual entre:
   - logo
   - eyebrow o etiqueta superior
   - título principal
   - subtítulo o texto descriptivo
   - chip de estado backend si aplica
   - CTA principal
3. Reducir la sensación de vacío vertical y mejorar el ritmo del bloque.
4. Ajustar el protagonismo del logo para que se sienta más integrado y relevante.
5. Ajustar el titular para que mantenga fuerza, pero no rompa la composición ni monopolice toda la jerarquía visual.
6. Reordenar o afinar espaciados, anchuras máximas y alineaciones para que el conjunto se perciba más compacto y más intencional.
7. Mantener el hero claro, centrado en comunidad, branding y CTA.
8. Validar que la composición siga funcionando bien en móvil y escritorio.
9. No alterar enlaces, rutas ni comportamiento funcional existente.

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
- No cambiar la ruta del logo.
- No cambiar el enlace del Discord.
- No cambiar el enlace del tráiler.
- No añadir nuevas secciones.
- No introducir librerías nuevas.
- No romper el fallback actual.
- No hacer cambios destructivos.
- Mantener la landing simple y coherente con el tono HLL Vietnam.

## Validation
- El hero se siente más compacto y más fuerte visualmente.
- El logo tiene mejor presencia relativa.
- El titular sigue siendo potente pero está mejor equilibrado.
- El CTA sigue siendo claro y visible.
- La cabecera transmite más sensación de portada principal.
- La composición sigue siendo responsive y estable.

## Change Budget
- Preferir menos de 2 archivos modificados.
- Preferir menos de 170 líneas cambiadas.
