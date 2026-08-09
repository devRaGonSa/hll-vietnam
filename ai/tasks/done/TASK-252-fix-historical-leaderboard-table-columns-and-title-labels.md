# TASK-252 - Fix historical leaderboard table columns and title labels

## Summary

This task fixes two regressions introduced after TASK-250 in the public historical leaderboard:

- the section title could render as `undefined ...`
- the primary metric column header could disappear because `hydrateWeeklyLeaderboard(...)` was called with the wrong argument order in some refresh paths

It also tightens the leaderboard table behavior so each top shows only the columns that match its metric.

## Files Read First

- `frontend/historico.html`
- `frontend/assets/js/historico.js`

## Root Cause

### 1. `undefined` in title

`buildLeaderboardTitle(...)` expects a valid metric config with a `.title`.

After TASK-250, some calls to `hydrateWeeklyLeaderboard(...)` still used the old function signature and omitted the new `ratioHeadingNode` argument. That shifted the remaining arguments:

- `weeklyWindowNoteNode` was received as `ratioHeadingNode`
- `weeklySnapshotMetaNode` was received as `noteNode`
- the metric config was received as `snapshotMetaNode`
- the timeframe string was received as `metricConfig`

That left `metricConfig.title` undefined and produced titles like:

- `undefined Semanal - Todos los servidores`

### 2. Primary metric header missing

The same bad argument order also broke the header sync path:

- the value column header was still updated
- but the ratio-heading logic was running against the wrong node
- depending on the metric, the table could lose the intended visible structure and appear with the main metric column effectively unlabeled in production

## Changes Applied

- Updated every `hydrateWeeklyLeaderboard(...)` call to pass `weeklyRatioHeadingNode` in the correct position.
- Hardened `buildLeaderboardTitle(...)` so it always falls back to a safe metric config and never emits `undefined`.
- Adjusted metric labels to match the required public wording:
  - `kills` -> title `Top kills`, value heading `Kills`
  - `deaths` -> title `Top muertes`, value heading `Muertes`
  - `matches_over_100_kills` -> title `Partidas 100+ kills`, value heading `Partidas 100+ kills`
  - `support` -> title `Soporte`, value heading `Soporte`
- Kept ratio-column behavior metric-aware:
  - kills -> `Kills/partida`
  - deaths -> `Muertes/partida`
  - matches_over_100_kills -> no ratio column
  - support -> `Soporte/partida` only when rows exist; otherwise the ratio column stays hidden

## Final Headers By Top

### Top kills

- `Pos.`
- `Jugador`
- `Kills`
- `Partidas`
- `Kills/partida`

### Top muertes

- `Pos.`
- `Jugador`
- `Muertes`
- `Partidas`
- `Muertes/partida`

### Partidas 100+ kills

- `Pos.`
- `Jugador`
- `Partidas 100+ kills`
- `Partidas`

### Soporte

If rows exist:

- `Pos.`
- `Jugador`
- `Soporte`
- `Partidas`
- `Soporte/partida`

If no rows exist:

- `Pos.`
- `Jugador`
- `Soporte`
- `Partidas`

## Support Status

Current support payload behavior was reviewed only to the extent needed to diagnose the UI:

- the RCON historical leaderboard code documents support as a special case
- when support data is not available from the materialized RCON read model, it returns an empty supported payload instead of falling back to unrelated public-scoreboard totals

Frontend behavior now matches that contract:

- no `undefined`
- no stale `Kills/partida`
- no ratio column for support when there are no rows

## Validation

Executed:

- `node --check frontend/assets/js/historico.js`

Static checks:

- every `hydrateWeeklyLeaderboard(...)` call now passes `weeklyRatioHeadingNode`
- `buildLeaderboardTitle(...)` has a safe fallback path and no longer depends on an unchecked `metricConfig.title`
- header/value mappings were checked for:
  - `kills`
  - `deaths`
  - `matches_over_100_kills`
  - `support`

Expected output matrix:

- kills -> `Pos., Jugador, Kills, Partidas, Kills/partida`
- deaths -> `Pos., Jugador, Muertes, Partidas, Muertes/partida`
- matches_over_100_kills -> `Pos., Jugador, Partidas 100+ kills, Partidas`
- support -> `Pos., Jugador, Soporte, Partidas`, plus `Soporte/partida` only when rows exist

## Post-Deploy Visual Check

1. Open `historico.html`
2. Select `Semanal + Top kills`
   - title must be `Top kills Semanal - ...`
   - `Kills` column visible
   - `Kills/partida` visible
3. Select `Mensual + Top muertes`
   - title must be `Top muertes Mensual - ...`
   - `Muertes` column visible
   - `Muertes/partida` visible
4. Select `Partidas 100+ kills`
   - title must be `Partidas 100+ kills ...`
   - `Partidas 100+ kills` column visible
   - no ratio column
5. Select `Soporte`
   - title must be `Soporte ...`
   - no `undefined`
   - no `Kills/partida`
   - if no rows, empty state remains intact

## Notes

- No backend changes were required.
- No assets, maps, brands, clan images or weapon images were modified.
