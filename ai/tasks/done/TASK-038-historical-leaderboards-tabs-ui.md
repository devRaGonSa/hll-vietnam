# TASK-038-historical-leaderboards-tabs-ui

## Goal
Transformar la sección de ranking semanal de la página histórica en un bloque con pestañas, permitiendo alternar entre varios leaderboards semanales del servidor seleccionado.

## Context
La UI histórica actual muestra un único ranking semanal de kills. El objetivo ahora es convertir esa zona en una sección con pestañas para poder consultar varias métricas sin recargar la página y manteniendo una experiencia clara. Las pestañas requeridas inicialmente son:
- Top kills
- Top muertes
- Top número de partidas con más de 100 kills
- Top puntos de soporte

La UI debe seguir siendo propia del proyecto y consumir únicamente la API histórica interna.

## Steps
1. Revisar la página histórica actual y el bloque de ranking semanal.
2. Revisar la nueva API histórica multitétrica disponible tras la task previa.
3. Diseñar un sistema de pestañas claro y coherente con el estilo de la web.
4. Implementar las pestañas para:
   - Top kills
   - Top muertes
   - Top número de partidas con más de 100 kills
   - Top puntos de soporte
5. Hacer que las pestañas reutilicen el servidor actualmente seleccionado.
6. Mantener estados de:
   - loading
   - vacío
   - error
7. Ajustar títulos, subtítulos y labels de la sección para que sean claros y no sobrecarguen visualmente.
8. No usar páginas externas ni incrustaciones del scoreboard de la comunidad.
9. Mantener la coherencia visual con el resto de la página histórica y con la landing principal.
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
- frontend/historico.html
- frontend/assets/js/historico.js
- frontend/assets/css/historico.css
- opcionalmente documentación mínima si hay un cambio visible relevante en la navegación histórica

## Constraints
- No crear nuevas páginas basadas en URLs externas.
- No romper la UI histórica actual fuera del bloque de ranking.
- No introducir frameworks nuevos.
- No hacer cambios destructivos.
- Mantener la solución centrada en pestañas, claridad y consumo de nuestra API.

## Validation
- La sección de ranking semanal se convierte en un bloque con pestañas funcionales.
- Las pestañas muestran:
  - Top kills
  - Top muertes
  - Top partidas con más de 100 kills
  - Top puntos de soporte
- La UI consume únicamente la API interna del proyecto.
- El selector de servidor sigue funcionando con estas pestañas.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 5 archivos modificados.
- Preferir menos de 220 líneas cambiadas.
