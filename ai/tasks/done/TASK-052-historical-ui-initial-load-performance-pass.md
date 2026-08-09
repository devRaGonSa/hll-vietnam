# TASK-052-historical-ui-initial-load-performance-pass

## Goal
Reducir drásticamente el tiempo percibido de carga inicial de `historico.html`, evitando peticiones innecesarias al entrar, eliminando precargas agresivas y permitiendo que resumen, ranking y partidas recientes se hidraten de forma progresiva e independiente.

## Context
La página histórica ya consume snapshots rápidos, pero el comportamiento actual sigue generando una experiencia lenta:
- se lanzan varias peticiones de snapshots al entrar
- se precargan varias métricas de leaderboard demasiado pronto
- hay prefetch por interacción ligera o por estrategia demasiado agresiva
- la UI tarda en mostrar contenido útil porque espera más de la cuenta antes de hidratar bloques visibles

El objetivo de esta task es que la carga inicial sea más ligera y que el usuario vea contenido útil antes, aunque el resto de bloques sigan llegando progresivamente.

## Steps
1. Revisar `frontend/assets/js/historico.js` y la estrategia actual de carga inicial.
2. Identificar y reducir las peticiones lanzadas al entrar en la página para el servidor activo.
3. Hacer que en la carga inicial solo se pidan los datos estrictamente necesarios para pintar la primera vista útil, como mínimo:
   - resumen del servidor activo
   - leaderboard de la pestaña activa
   - partidas recientes del servidor activo
4. Evitar que en la carga inicial se precarguen automáticamente todas las métricas del leaderboard si no son visibles todavía.
5. Eliminar o reducir estrategias agresivas de prefetch por `hover`, `focus` o cambios ligeros de interacción si están disparando peticiones innecesarias.
6. Cambiar la hidratación para que los bloques visibles se pinten de forma progresiva e independiente, sin esperar a que todo el conjunto termine si un bloque ya está listo.
7. Mantener estados de loading por bloque, pero evitar que toda la página parezca “bloqueada” por el snapshot más lento.
8. Revisar y ajustar el caché frontend para que ayude a la velocidad sin mantener estados vacíos obsoletos demasiado tiempo.
9. No cambiar la semántica funcional de los datos históricos, solo mejorar la estrategia de carga y renderizado.
10. Al completar la implementación:
    - dejar el repositorio consistente
    - hacer commit
    - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- frontend/historico.html
- frontend/assets/js/historico.js
- frontend/assets/css/historico.css
- backend/app/routes.py
- backend/app/payloads.py
- backend/README.md

## Expected Files to Modify
- frontend/assets/js/historico.js
- frontend/historico.html
- frontend/assets/css/historico.css
- opcionalmente documentación mínima si el comportamiento visible cambia de forma relevante

## Constraints
- No crear páginas nuevas.
- No romper la UI histórica existente.
- No introducir frameworks nuevos.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en rendimiento percibido y estrategia de carga.

## Validation
- La carga inicial hace menos peticiones que antes.
- La página empieza a mostrar contenido útil antes.
- Resumen, leaderboard activo y partidas recientes se hidratan de forma progresiva.
- No se precargan de forma agresiva métricas no visibles en el primer paint.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 4 archivos modificados.
- Preferir menos de 220 líneas cambiadas.

## Outcome
- La carga inicial de `historico.html` ya no dispara precarga agresiva de todos los snapshots ni peticiones por `hover` o `focus` sobre el selector de servidor.
- La UI reutiliza snapshots cacheados de resumen, ranking activo y partidas recientes cuando existen, reduciendo la espera percibida en entradas posteriores y cambios de servidor.
- Resumen, leaderboard activo y partidas recientes se hidratan ahora de forma independiente; el bloque que llega antes se pinta antes, sin esperar al snapshot más lento.
- Validación local:
- `node --check frontend/assets/js/historico.js`
- revisión de `git diff --name-only` para confirmar alcance limitado a `frontend/assets/js/historico.js` y el archivo de task
