# TASK-103-rcon-first-historical-aggregates-and-fallback-boundary

## Goal
Mover los agregados históricos de producto a una frontera RCON-first real, dejando scoreboard solo para las piezas que todavía no puedan calcularse desde el modelo histórico competitivo RCON-backed.

## Context
Una vez exista el modelo primario histórico competitivo RCON-backed, hace falta conectar realmente los endpoints y payloads de producto para que usen esa capa como primaria.

## Steps
1. Auditar:
   - `backend/app/payloads.py`
   - `backend/app/routes.py`
   - `backend/app/historical_snapshots.py`
   - `backend/app/historical_snapshot_storage.py`
   - `backend/app/elo_mmr_engine.py`
2. Reorientar como RCON-first real, al menos donde la nueva capa ya lo permita:
   - historical server summary
   - recent matches
   - Elo/MMR mensual
   - y cualquier agregado competitivo mínimo ya soportado
3. Mantener fallback a public-scoreboard solo cuando:
   - la capability sea partial/unavailable
   - la cobertura RCON no alcance
   - el cálculo falle
4. Hacer visible la frontera exacta de fallback:
   - qué endpoints ya son realmente RCON-first
   - cuáles siguen cayendo a scoreboard
   - por qué
5. Ajustar snapshots/materializaciones si hace falta para no depender del request path directo.
6. Alinear README/runbook con esta nueva frontera funcional.

## Constraints
- No afirmar que MVP V1/V2 completos ya sean 100% RCON-backed si no lo son.
- No romper endpoints existentes.
- No ocultar el fallback real.
- Mantener latencia razonable.

## Validation
- Los endpoints históricos soportados ya usan RCON-backed como primario real.
- El fallback a scoreboard queda reducido y explícito.
- Elo/MMR mensual consume primariamente el modelo RCON-backed donde ya sea posible.
- La repo queda consistente.

## Expected Files
- `backend/app/payloads.py`
- `backend/app/routes.py`
- `backend/app/historical_snapshots.py`
- `backend/app/historical_snapshot_storage.py`
- `backend/app/elo_mmr_engine.py`
- `backend/README.md`
- otros archivos backend si hace falta
