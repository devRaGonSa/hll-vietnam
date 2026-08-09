# TASK-044-historical-snapshots-api

## Goal
Exponer una API de snapshots historicos precalculados para que el frontend pueda consumir resumen, tops y partidas recientes sin disparar agregaciones costosas en tiempo real.

## Context
Con snapshots ya persistidos y generados periodicamente, el siguiente paso es exponer endpoints ligeros para que la UI historica lea directamente datos preparados.

## Steps
1. Revisar la capa de snapshots ya creada y el runner de generacion.
2. Disenar endpoints claros para leer snapshots por servidor, tipo y metrica.
3. Cubrir como minimo:
   - resumen de servidor
   - tops semanales por metrica
   - partidas recientes
4. Asegurar que los endpoints devuelven tambien informacion util de actualizacion:
   - generated_at
   - rango fuente
   - stale/fresh si aplica
5. Mantener compatibilidad razonable con la UI historica ya existente o dejar clara la migracion.
6. Documentar los endpoints en backend.
7. No cambiar todavia toda la UI en esta task.
8. Al completar la implementacion:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- backend/README.md
- backend/app/routes.py
- backend/app/payloads.py
- backend/app/historical_snapshot_storage.py
- backend/app/historical_snapshots.py

## Expected Files to Modify
- backend/app/routes.py
- backend/app/payloads.py
- backend/README.md
- opcionalmente nuevos modulos de payload/query de snapshots

## Constraints
- No usar A2S para esta capa.
- No hacer calculos pesados on-demand si ya existe snapshot valido.
- No crear UI nueva en esta task.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en una API ligera de snapshots.

## Validation
- Existen endpoints de snapshots para resumen, tops y partidas recientes.
- Los payloads incluyen metadatos de actualizacion utiles.
- La capa esta lista para que la UI deje de depender de agregados pesados en tiempo real.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 5 archivos modificados o creados.
- Preferir menos de 220 lineas cambiadas.

## Outcome
- `backend/app/routes.py` expone endpoints ligeros de lectura para `server-summary`, `weekly-leaderboard` y `recent-matches` bajo `/api/historical/snapshots/*`.
- `backend/app/payloads.py` lee directamente `historical_precomputed_snapshots` con `get_historical_snapshot(...)` y devuelve payloads compatibles con frontend sin recalcular agregados historicos pesados.
- La metadata comun de snapshot incluye `generated_at`, `source_range_start`, `source_range_end`, `is_stale`, `freshness` y `found`.
- `backend/README.md` documenta los endpoints de snapshots y la metadata operativa disponible para frontend.

## Validation Result
- Validado con `python -m py_compile backend/app/routes.py backend/app/payloads.py backend/app/historical_snapshot_storage.py backend/app/historical_snapshots.py`.
- Validado con `resolve_get_payload(...)` para:
  - `/api/historical/snapshots/server-summary`
  - `/api/historical/snapshots/weekly-leaderboard`
  - `/api/historical/snapshots/recent-matches`
- Validado con builders de payload en Python: los tres endpoints exponen `freshness` y responden de forma estable incluso cuando todavia no existe snapshot persistido, devolviendo `found: False` y estados vacios compatibles.
- Durante una validacion paralela aparecio un `sqlite3.OperationalError: database is locked` por inicializaciones concurrentes sobre la misma SQLite local; la validacion secuencial posterior paso correctamente sin requerir cambios de implementacion para esta task.
- Revisado en diff: la task queda limitada a `backend/app/routes.py`, `backend/app/payloads.py`, `backend/README.md` y este archivo de task.

## Decision Notes
- Se mantuvieron intactos los endpoints historicos legacy (`/api/historical/server-summary`, `/api/historical/weekly-leaderboard`, `/api/historical/recent-matches`) para no romper consumidores existentes mientras la migracion a snapshots ocurre por separado.
- La capa de snapshots se resolvio como lectura directa de persistencia con recorte por `limit` sobre payload ya precalculado, evitando introducir nuevos calculos on-demand.
