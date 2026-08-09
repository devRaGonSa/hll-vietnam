# TASK-250 - Fix historical ranking labels, table uniformity and Steam icon

## Summary

This task fixes public labels that were still misleading in historical leaderboards, aligns the visible column order and wording between Stats and Ranking, and audits the Steam brand icon path used by external profiles.

## Files Read First

- `frontend/historico.html`
- `frontend/assets/js/historico.js`
- `frontend/ranking.html`
- `frontend/assets/js/ranking.js`
- `frontend/assets/js/stats.js`
- `frontend/assets/js/historico-partida.js`

## Historical Leaderboards

The weekly/monthly leaderboard table now adapts its ratio column to the active metric:

- `kills` -> `Kills/partida`
- `deaths` -> `Muertes/partida`
- `support` -> `Soporte/partida`
- `matches_over_100_kills` -> ratio column hidden

This removes the incorrect `Kills/partida` label from:

- Top muertes
- Top soporte
- Partidas 100+ kills

No aggregated real KPM was added in this task.

## Stats / Ranking Uniformity

Visible labels were normalized to Spanish or accepted abbreviations:

- `Deaths` -> `Muertes`
- `Teamkills` -> `TK`
- `matches_considered` -> `Partidas`
- `kd_ratio` -> `KD`
- `kills_per_match` -> `Kills/partida`

Shared player ranking column order now stays consistent:

- `Pos.`
- `Jugador`
- `Partidas`
- `Kills`
- `Muertes`
- `TK`
- `KD`
- `Kills/partida`

`ranking.html` keeps its extra `Valor activo` column before the shared block because that table is metric-driven.

## Steam Icon Audit

The code path in `historico-partida.js` is already correct:

- `./assets/img/brands/steam.png`

The local file also exists:

- `frontend/assets/img/brands/steam.png`

It is currently untracked in git:

- `git status --short --untracked-files=all -- frontend/assets/img/brands`
  - `?? frontend/assets/img/brands/steam.png`

Production currently returns:

- `https://comunidadhll.devzamode.es/assets/img/brands/steam.png` -> `404`

So the remaining issue is deployment scope, not the frontend path.

The defensive `onerror` behavior remains in place.

Because this exact local asset exists and is the only Steam brand asset detected in:

- `frontend/assets/img/brands/`
- `frontend/assets/img/`
- `frontend/assets/`

it is the one asset that should be included with the TASK-250 frontend commit if the goal is to make the icon visible in production.

## Validation

Executed:

- `node --check frontend/assets/js/historico.js`
- `node --check frontend/assets/js/stats.js`
- `node --check frontend/assets/js/ranking.js`

Static validation performed:

- no visible `Deaths` label remains in Stats / Ranking tables or selects
- no visible `Teamkills` label remains in Stats / Ranking tables or selects
- `Kills/partida` no longer appears for Top muertes, Top soporte or Partidas 100+ kills
- Top muertes now uses `Muertes/partida`
- Stats and Ranking keep the same relative order for shared columns

Operational validation performed:

- production Steam icon URL returns `404`
- local `frontend/assets/img/brands/steam.png` exists but is not tracked
- no alternate local Steam asset name or extension was detected

## Notes

- No backend changes were required.
- No map, weapon or clan asset was modified.
- To fully fix the Steam icon in production, the existing local `steam.png` must be included in a later isolated commit.
