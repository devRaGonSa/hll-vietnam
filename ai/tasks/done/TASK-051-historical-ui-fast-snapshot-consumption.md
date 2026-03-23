# TASK-051-historical-ui-fast-snapshot-consumption

## Goal
Ajustar la UI histórica para consumir de forma rápida y estable los snapshots precalculados de resumen, rankings y partidas recientes, incluyendo soporte para el tercer servidor y para tops globales.

## Context
Una vez exista una capa de snapshots en archivos JSON y estén resueltos los servidores #02 y #03, la UI histórica debe consumir esa capa sin esperas innecesarias, permitiendo cambiar de servidor o pestaña sin sensaciones de bloqueo. Además, debe soportar un selector ampliado con:
- Comunidad Hispana #01
- Comunidad Hispana #02
- Comunidad Hispana #03
- Totales / Todos

## Steps
1. Revisar la UI histórica actual y su consumo de snapshots.
2. Ajustar el selector de servidor para incluir:
   - `comunidad-hispana-01`
   - `comunidad-hispana-02`
   - `comunidad-hispana-03`
   - `all-servers`
3. Asegurar que resumen, tops y partidas recientes se cargan desde snapshots rápidos ya preparados.
4. Evitar caches frontales que congelen indefinidamente respuestas `found: false`.
5. Mantener estados de loading, empty y error, pero con una experiencia más ágil.
6. Reflejar correctamente:
   - servidor seleccionado
   - rango real usado
   - fallback semanal si aplica
7. No depender de URLs externas de la comunidad.
8. Mantener coherencia visual con la página histórica ya existente.
9. Al completar la implementación:
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
- opcionalmente backend docs mínimas si cambia el contrato visible de consumo

## Constraints
- No crear páginas nuevas.
- No romper la UI histórica existente.
- No introducir frameworks nuevos.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en velocidad percibida, selector ampliado y consumo de snapshots.

## Validation
- La UI histórica soporta #01, #02, #03 y tops globales.
- Cambiar de servidor o métrica es rápido.
- No se quedan cacheadas indefinidamente respuestas vacías antiguas.
- La página consume snapshots precalculados y no agregados pesados en tiempo real.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 5 archivos modificados o creados.
- Preferir menos de 220 líneas cambiadas.

## Outcome
- El selector histórico se amplió a `comunidad-hispana-01`, `comunidad-hispana-02`, `comunidad-hispana-03` y `all-servers`.
- La UI sigue consumiendo los endpoints propios de snapshots precalculados, pero ahora hace prefetch de resumen, partidas recientes y rankings del alcance activo para acelerar los cambios de selector y pestaña.
- La caché frontend ya no conserva indefinidamente respuestas con `found: false`; las respuestas negativas vencen rápido y se reintentan automáticamente.
- La cabecera y las notas de sección reflejan mejor el alcance activo, incluyendo el caso agregado `Totales / Todos`.
- Validación local:
- `node --check frontend/assets/js/historico.js`
- comprobación de strings y selectores en `frontend/historico.html` y `frontend/assets/js/historico.js` para `comunidad-hispana-03`, `all-servers` y `recent-matches-note`
