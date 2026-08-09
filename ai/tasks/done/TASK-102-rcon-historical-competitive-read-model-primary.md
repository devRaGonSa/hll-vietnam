# TASK-102-rcon-historical-competitive-read-model-primary

## Goal
Construir una capa histórica competitiva primaria basada en persistencia RCON, o en una materialización derivada de ella, suficiente para soportar el producto histórico sin depender de public-scoreboard como writer principal.

## Context
Hoy la repo ya tiene:
- captura histórica prospectiva RCON
- read model histórico RCON mínimo
- histórico clásico por public-scoreboard
- player-events V2
- Elo/MMR mensual
Pero el writer path histórico competitivo sigue dependiendo del archivo clásico importado por scoreboard.

## Steps
1. Auditar:
   - `backend/app/rcon_historical_storage.py`
   - `backend/app/rcon_historical_read_model.py`
   - `backend/app/historical_storage.py`
   - `backend/app/player_event_storage.py`
   - `backend/app/elo_mmr_storage.py`
   - `backend/app/payloads.py`
2. Definir un modelo primario histórico competitivo RCON-backed:
   - directo sobre persistencia RCON, o
   - mediante tablas/materializaciones derivadas generadas desde RCON
3. Ese modelo debe cubrir como prioridad:
   - recent activity / recent matches
   - historical server summary
   - métricas mínimas competitivas reutilizables por MVP/Elo
4. Si hacen falta tablas/materialized snapshots nuevas, crearlas.
5. Dejar capabilities explícitas por dominio:
   - exact
   - approximate
   - partial
   - unavailable
6. Documentar claramente qué parte del histórico ya puede dejar de depender del import clásico.
7. Mantener scoreboard como fallback solo para lo que todavía no esté cubierto.

## Constraints
- No romper la persistencia RCON ya existente.
- No eliminar el histórico clásico todavía.
- No inventar granularidad que la captura RCON no tenga.
- No degradar el request path HTTP innecesariamente.

## Validation
- Existe una capa histórica competitiva primaria RCON-backed real.
- Al menos summary/recent activity dejan de depender del pipeline clásico como principal.
- Las capabilities quedan visibles y honestas.
- La repo queda consistente.

## Expected Files
- archivos backend nuevos o modificados bajo `backend/app/` para read model/materialización histórica RCON
- `docs/elo-mmr-monthly-ranking-design.md` si hace falta
- `backend/README.md`
