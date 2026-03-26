# TASK-114-add-playtime-to-historical-top-rankings

## Goal
Anadir `tiempo jugado` a las tablas/listas de tops historicos para que el usuario vea, junto a `partidas`, cuanto tiempo acumulado jugo cada jugador en el periodo del ranking.

## Context
Hoy los rankings historicos visibles muestran posicion, jugador, valor de la metrica y partidas. El producto necesita mostrar tambien tiempo jugado del mismo periodo del ranking para interpretar mejor el rendimiento y la actividad.

## Scope
Backend + frontend, de forma localizada.

## Steps
1. Auditar:
   - `backend/app/payloads.py`
   - funciones backend que construyen leaderboards historicos
   - `frontend/assets/js/historico.js`
   - `frontend/historico.html`
2. Identificar si el backend ya expone tiempo jugado para el periodo del ranking.
3. Si no lo expone, anadirlo de forma consistente y localizada.
4. Actualizar la tabla/lista de tops para mostrar:
   - o bien una nueva columna `Tiempo jugado`
   - o una representacion clara junto a `Partidas`
5. Mantener coherencia temporal:
   - el tiempo jugado debe corresponder al mismo periodo del ranking mostrado
6. No romper tabs, filtros, timeframe semanal/mensual ni otras metricas.

## Constraints
- No mezclar tiempo global de perfil con tiempo del periodo del ranking.
- No tocar otras secciones salvo lo necesario.
- Mantener el cambio visual limpio y legible.

## Validation
- Los tops muestran `tiempo jugado` ademas de `partidas`.
- El dato corresponde al mismo periodo del ranking.
- No se rompe la UI historica.

## Expected Files
- backend de leaderboards historicos
- `frontend/assets/js/historico.js`
- `frontend/historico.html`
- `frontend/assets/css/historico.css` solo si hace falta

## Outcome
- `backend/app/historical_storage.py` ahora agrega `SUM(time_seconds)` en los leaderboards semanal y mensual y expone `total_time_seconds` por jugador dentro del mismo periodo del ranking.
- `frontend/historico.html` anade una nueva columna `Tiempo jugado` en la tabla de rankings historicos.
- `frontend/assets/js/historico.js` renderiza ese dato como horas jugadas del periodo usando `total_time_seconds`, sin mezclarlo con datos globales de perfil.
- `frontend/assets/css/historico.css` amplia el ancho minimo de la tabla para mantener legibilidad con la nueva columna.

## Validation Notes
- `python -m py_compile backend\\app\\historical_storage.py backend\\app\\payloads.py`
- Validacion del payload de ranking:
  - `build_historical_leaderboard_payload(limit=1, server_id='comunidad-hispana-01', metric='kills', timeframe='weekly')`
  - comprobado que el item devuelto incluye `total_time_seconds`
- `git diff --name-only`
