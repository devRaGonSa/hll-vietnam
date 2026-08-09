# TASK-055-fix-all-servers-historical-aggregate

## Goal
Corregir el agregado histórico `all-servers` / `Totales / Todos` para que resumen, tops semanales y partidas recientes reflejen realmente la suma o agregación de los servidores con histórico disponible, en vez de devolver snapshots vacíos.

## Context
La situación actual del histórico es esta:
- `comunidad-hispana-01` muestra datos correctos
- `comunidad-hispana-02` muestra datos correctos
- `Totales / Todos` aparece vacío
- `comunidad-hispana-03` todavía no debe considerarse error, porque no se ha ejecutado bootstrap para ese servidor

Esto indica un fallo específico en la generación o persistencia del agregado lógico `all-servers`, no un problema general de la capa histórica.

## Steps
1. Revisar la implementación actual del agregado lógico `all-servers` en:
   - snapshots
   - payloads
   - rutas
   - generación/prewarm
2. Verificar cómo se construyen actualmente:
   - resumen global
   - weekly leaderboards globales
   - recent matches globales
3. Corregir la lógica para que `all-servers` agregue correctamente los servidores con histórico disponible.
4. Asegurar que el agregado:
   - incluya `comunidad-hispana-01`
   - incluya `comunidad-hispana-02`
   - no dependa de que `comunidad-hispana-03` ya tenga histórico
   - no colapse a vacío si uno de los servidores no tiene datos aún
5. Verificar que los snapshots globales se generen con datos reales y no se sobrescriban con vacíos.
6. Regenerar los snapshots necesarios de `all-servers`.
7. Validar que en la UI:
   - `Totales / Todos` deje de mostrar 0 partidas / 0 jugadores
   - los tops globales ya tengan datos
   - recent matches globales ya tengan contenido si existe histórico en #01 y #02
8. Documentar brevemente la semántica final del agregado global.
9. No tratar todavía `#03` como parte obligatoria del agregado si no hay bootstrap para ese servidor.
10. Al completar la implementación:
    - dejar el repositorio consistente
    - hacer commit
    - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- backend/README.md
- backend/app/historical_storage.py
- backend/app/historical_snapshots.py
- backend/app/historical_snapshot_storage.py
- backend/app/payloads.py
- backend/app/routes.py
- frontend/assets/js/historico.js
- frontend/historico.html

## Expected Files to Modify
- backend/app/historical_storage.py
- backend/app/historical_snapshots.py
- backend/app/historical_snapshot_storage.py
- backend/app/payloads.py
- backend/app/routes.py
- backend/README.md
- opcionalmente frontend/assets/js/historico.js si hace falta ajustar cómo se interpreta el agregado global

## Constraints
- No romper #01 ni #02.
- No exigir histórico de #03 para que `all-servers` funcione.
- No crear páginas nuevas.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en arreglar el agregado global.

## Validation
- `Totales / Todos` deja de estar vacío.
- El resumen global tiene partidas, jugadores y mapas si #01 y #02 tienen histórico.
- Los tops globales funcionan.
- Las partidas recientes globales funcionan.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 6 archivos modificados o creados.
- Preferir menos de 240 líneas cambiadas.
