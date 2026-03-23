# TASK-045-historical-ui-migrate-to-snapshots

## Goal
Migrar la pagina historica para que lea snapshots precalculados de resumen, tops y partidas recientes, mejorando tiempos de carga y evitando esperas innecesarias al abrir la pagina o cambiar de pestana.

## Context
La UI historica ya existe, pero el objetivo ahora es que no dependa de consultas pesadas en tiempo real. Debe leer snapshots ya preparados y actualizados en segundo plano, mostrando datos rapidos y estables.

## Steps
1. Revisar la API de snapshots ya implementada.
2. Cambiar la UI historica para que:
   - resumen
   - tabs de tops
   - partidas recientes
   se carguen desde snapshots y no desde agregados costosos on-demand.
3. Mostrar de forma clara cuando se genero el snapshot.
4. Mantener estados de loading, empty y error, pero reducir la espera perceptible.
5. Asegurar que cambiar entre pestanas de tops sea rapido y estable.
6. Mantener coherencia visual con el resto de la web.
7. No crear paginas nuevas en esta task.
8. Al completar la implementacion:
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

## Expected Files to Modify
- frontend/historico.html
- frontend/assets/js/historico.js
- frontend/assets/css/historico.css
- opcionalmente backend docs minimas si cambia el flujo de consumo

## Constraints
- No romper la UI historica existente.
- No introducir frameworks nuevos.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en rendimiento percibido y consumo de snapshots.

## Validation
- La UI historica carga resumen, tops y partidas recientes desde snapshots.
- Cambiar de pestana entre tops es rapido.
- El usuario ve una referencia clara de actualizacion.
- La pagina reduce la dependencia de calculos on-demand pesados.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 5 archivos modificados o creados.
- Preferir menos de 220 lineas cambiadas.

## Outcome
- `frontend/assets/js/historico.js` deja de depender de agregados historicos on-demand y pasa a leer snapshots precalculados para resumen, ranking semanal y partidas recientes.
- `frontend/assets/js/historico.js` incorpora cache por servidor y metrica para que cambiar de pestana entre tops reutilice payloads ya leidos y reduzca la espera perceptible.
- `frontend/historico.html` y `frontend/assets/css/historico.css` muestran una referencia explicita de `generated_at` y del rango fuente de cada snapshot en las tres secciones principales.
- `backend/app/routes.py` y `backend/app/payloads.py` anaden la capa minima de lectura `/api/historical/snapshots/*` necesaria para servir snapshots precalculados sin recalcular agregados pesados.
- `backend/README.md` documenta los nuevos endpoints de snapshots y la metadata operativa que exponen.

## Validation Result
- Validado con `node --check frontend/assets/js/historico.js`.
- Validado con `python -m py_compile backend/app/routes.py backend/app/payloads.py`.
- Validado con `resolve_get_payload(...)` para:
  - `/api/historical/snapshots/server-summary`
  - `/api/historical/snapshots/weekly-leaderboard`
  - `/api/historical/snapshots/recent-matches`
- Validado con builders Python: los nuevos payloads responden de forma estable incluso cuando todavia no existen snapshots persistidos y devuelven `found: False` con `items: []` o `item: None`.
- Revisado en diff: el alcance queda limitado a `backend/README.md`, `backend/app/routes.py`, `backend/app/payloads.py`, `frontend/historico.html`, `frontend/assets/css/historico.css`, `frontend/assets/js/historico.js` y este archivo de task.

## Decision Notes
- La task estaba bloqueada por una dependencia no resuelta: la UI debia migrar a snapshots, pero la API ligera de lectura descrita en la task previa no estaba presente en `routes.py` ni en `payloads.py` dentro de este worktree. Se implemento solo la capa minima necesaria para completar la migracion sin ampliar el alcance a nueva UI ni a nuevos calculos backend.
- Se mantuvieron los endpoints historicos legacy para no romper compatibilidad mientras la pagina historica migra al contrato basado en snapshots.
