# TASK-254 - Fix historical ratio values and stats profile performance regression

## Summary

This task fixes two regressions detected before pushing TASK-252 and TASK-253:

1. Historical leaderboard ratio columns could show `0,00` when the direct ratio field was `null`.
2. The public player profile in `stats.html` could become slow when the weekly/monthly read model was empty and the endpoint fell back to runtime aggregation.

## Historical Ratios

Root cause:

- `formatHistoricalPerMatch(...)` converted `null` direct values with `Number(null)`, which becomes `0`.
- For `Top muertes` and `Soporte`, that caused the formatter to stop early and render `0,00` instead of dividing the real total by matches.

Fix:

- treat `null`, `undefined` and empty string as missing direct values
- only use a direct ratio value when it is truly present
- otherwise compute:
  - kills / partidas
  - muertes / partidas
  - soporte / partidas
- if `matches <= 0` or the total is missing, render an empty string instead of a fake `0,00`

Expected examples:

- kills `170`, matches `4` -> `42,50`
- deaths `225`, matches `14` -> `16,07`

## Stats Profile Performance

Root cause:

- TASK-253 added a runtime fallback for weekly/monthly personal profile reads when `player_period_stats` was empty.
- That fallback queried live materialized match/player tables and ranking windows on the request path.
- For public profile reads this is too expensive and can degrade page responsiveness.

Fix:

- disable the runtime fallback for weekly/monthly profile reads
- keep the endpoint read-model-first only for public weekly/monthly profile windows
- when the read model is missing:
  - return a lightweight profile payload
  - keep external profile links and platform identity
  - keep `kpm = null`
  - keep `kpm_status = missing_active_time`

This preserves:

- translated labels
- hidden personal ID in the visible profile card
- external profile buttons
- no fake KPM

## Teamkills

No TeamKills change was implemented here.

Reference:

- `TASK-251-investigate-teamkills-ranking-zeroes.md`

## Validation

Executed:

- `node --check frontend/assets/js/historico.js`
- `node --check frontend/assets/js/stats.js`
- `python -m compileall backend/app`
- `cd backend; python -m unittest tests.test_current_match_payload`
- `cd backend; python -m unittest tests.test_historical_snapshot_refresh`
- `cd backend; python -m unittest tests.test_stats_player_profile_payload`

Static/manual checks:

- no `undefined` titles remain in historical leaderboard labels
- `Kills/partida` only stays on `Top kills`
- `Muertes/partida` stays on `Top muertes`
- `matches_over_100_kills` keeps no ratio column
- Steam profile buttons still resolve to Steam + Hellor + HLL Records + Helo
- Epic profile buttons still resolve to Hellor + HLL Records

## Notes

- No backend scheduler change.
- No RCON/server configuration change.
- No asset change.
