# TASK-248 - Add real KPM to public tables and fix kills per match labels

## Summary

This task extends the already validated real historical KPM to the main player table in `historico-partida.html` and removes misleading public `KPM` labels that were actually rendering `kills_per_match`.

It does not change the real KPM formula already validated in production.

## Files Read First

- `frontend/historico-partida.html`
- `frontend/assets/js/historico-partida.js`
- `frontend/assets/css/historico.css`
- `frontend/historico.html`
- `frontend/assets/js/historico.js`
- `frontend/stats.html`
- `frontend/assets/js/stats.js`
- `frontend/ranking.html`
- `frontend/assets/js/ranking.js`
- `backend/app/rcon_historical_read_model.py`
- `docs/HISTORICAL_MATCH_KILLS_PER_MINUTE_ANALYSIS.md`

## Problem

The repository already exposed real KPM at player level in `/api/historical/matches/detail`, but the public UI still had two problems:

1. `historico-partida` only showed real KPM in the expanded player panel, not in the main table.
2. Several public surfaces were calling `kills_per_match` by the visible label `KPM`, which is incorrect.

## Decision

Keep the validated real KPM model unchanged:

- only `kpm_status = ready` renders a visible value
- no total-match-duration fallback
- no `event_span_fallback` as ready KPM

Apply two UI rules:

- historical match detail main table gets a real `KPM` column
- any visible `kills_per_match` label becomes `Kills/partida`

Do not add public aggregated weekly/monthly/annual real KPM yet. That would need a separate backend and snapshot coverage contract so mixed datasets do not produce misleading results.

## Implementation

### Historical match detail

- Added a sortable `KPM` option in the player table.
- Added a `KPM` column in the main player list.
- The cell stays empty unless `kpm_status == "ready"`.
- The expanded panel keeps its existing real KPM chip.

### Historical weekly/monthly tables

- Renamed the last leaderboard metric from `KPM` to `Kills/partida`.
- Kept the underlying `kills_per_match` meaning unchanged.

### Stats and ranking

- Annual stats table now labels `kills_per_match` as `Kills/partida`.
- Weekly/monthly comparison cards now label the same metric as `Kills/partida semanal` and `Kills/partida mensual`.
- Ranking already used `Kills/partida`, so no semantic rename was needed there.

## Validation

Executed:

- `node --check frontend/assets/js/historico-partida.js`
- `node --check frontend/assets/js/historico.js`
- `node --check frontend/assets/js/stats.js`
- `node --check frontend/assets/js/ranking.js`

Static validation performed:

- confirmed `historico-partida.html` main table now shows `KPM`
- confirmed expanded player panel still shows real KPM
- confirmed rows with `insufficient_active_time` keep the main table cell empty
- confirmed historical weekly/monthly tables no longer show `KPM` for `kills_per_match`
- confirmed annual stats no longer show `KPM` for `kills_per_match`
- confirmed ranking still uses `Kills/partida`

## Notes

- No backend changes were required for this task.
- No scheduler, RCON or server configuration changes were made.
- Public aggregated real KPM for weekly/monthly/annual remains pending a dedicated coverage-safe snapshot design.
