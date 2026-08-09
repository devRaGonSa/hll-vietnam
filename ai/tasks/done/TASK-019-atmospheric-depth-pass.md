# TASK-019-atmospheric-depth-pass

## Goal
Aumentar la profundidad visual y la atmósfera general de la landing de HLL Vietnam mediante un refinamiento controlado de fondo, overlays, iluminación y separación de planos, sin recargar la interfaz ni romper su sobriedad.

## Context
La paleta actual funciona y la base visual está bien encaminada, pero el fondo y el marco general aún se perciben algo planos. Hace falta una pasada de atmósfera para reforzar el tono Vietnam/táctico, mejorar la profundidad percibida y dar más cohesión al conjunto, especialmente alrededor del hero y de las secciones principales.

## Steps
1. Revisar el tratamiento actual del fondo y los overlays.
2. Evaluar cómo se perciben:
   - profundidad
   - viñeteado
   - textura ambiental
   - degradados
   - separación entre hero y secciones
3. Refinar el sistema de fondo para aportar más atmósfera sin saturar.
4. Aplicar mejoras controladas en:
   - overlays
   - sombras de entorno
   - iluminación indirecta
   - separación de bloques
   - sensación cinematográfica
5. Mantener una estética oscura, militar y limpia.
6. Evitar efectos exagerados, brillos excesivos o ruido visual.
7. Validar que el resultado no perjudica legibilidad ni rendimiento aparente.
8. Mantener intacto el comportamiento funcional de la landing.

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- frontend/index.html
- frontend/assets/css/styles.css

## Expected Files to Modify
- frontend/assets/css/styles.css
- opcionalmente `frontend/index.html` si hiciera falta una envolvente mínima o ajuste estructural pequeño para soportar mejor la profundidad visual

## Constraints
- No cambiar contenido funcional.
- No añadir imágenes nuevas ni dependencias nuevas salvo que sea estrictamente innecesario.
- No rediseñar completamente la página.
- No tocar backend.
- No hacer cambios destructivos.
- Mantener el tono sobrio y cinematográfico.

## Validation
- La página transmite mayor profundidad visual.
- El fondo se siente menos plano.
- Hero y secciones se perciben mejor separados y más cohesionados.
- La atmósfera Vietnam/táctica queda reforzada.
- La legibilidad y claridad general se mantienen o mejoran.

## Change Budget
- Preferir menos de 2 archivos modificados.
- Preferir menos de 160 líneas cambiadas.
