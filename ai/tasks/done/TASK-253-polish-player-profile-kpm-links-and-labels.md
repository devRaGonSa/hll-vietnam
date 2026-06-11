# TASK-253 - Polish player profile KPM, links and labels

## Summary

This task improves the public player profile in `stats.html` without changing the validated historical match-detail KPM model.

Changes included:

- real weekly/monthly profile KPM when safe
- no visible raw player ID in the personal profile card or profile heading
- translated `current-week` / `current-month` labels
- external profile buttons aligned with `historico-partida`

Teamkills were not changed here. TASK-251 remains the reference audit for that problem.

## Files Read First

- `frontend/stats.html`
- `frontend/assets/js/stats.js`
- `frontend/assets/js/historico-partida.js`
- `backend/app/payloads.py`
- `backend/app/rcon_historical_player_stats.py`
- `docs/HISTORICAL_MATCH_KILLS_PER_MINUTE_ANALYSIS.md`

## Real KPM Decision

The player profile does not use match duration and does not reuse `kills_per_match`.

It now exposes real KPM only when the selected weekly or monthly window can aggregate player facts with:

- `active_time_source = connection_intervals`
- `active_time_source = connection_intervals_carryover`
- `player_active_seconds >= HLL_KPM_MIN_ACTIVE_SECONDS`

Formula:

```text
sum(eligible_kills) / (sum(eligible_player_active_seconds) / 60)
```

If the profile window has:

- no active time -> `kpm_status = missing_active_time`
- only fallback spans without reliable connection intervals -> `kpm_status = missing_connection_intervals`
- real connection rows but below threshold -> `kpm_status = insufficient_active_time`

Only `kpm_status = ready` is rendered in the frontend.

## Backend Notes

`build_stats_player_profile_payload(...)` now exposes:

- `platform`
- `steam_id_64`
- `epic_id`
- `external_profile_links`
- `player_active_seconds`
- `player_active_minutes`
- `kpm`
- `kpm_status`
- `active_time_source`
- `active_time_coverage`

If `player_period_stats` is unavailable for the requested weekly/monthly profile, the endpoint now falls back to runtime aggregation for that single player and window instead of returning an empty read-model-only payload.

This keeps the route useful without touching scheduler or snapshot policies.

## Frontend Notes

Profile polish in `stats.js`:

- removed visible `ID:` from the identity card
- removed raw player ID from the visible profile heading/state
- translated:
  - `current-week` -> `Semana actual`
  - `current-month` -> `Mes actual`
  - fallback labels for previous windows
- added external profile buttons using the same destinations as `historico-partida`
- keeps defensive image `onerror`
- renders KPM only when `kpm_status == ready`

Profile buttons by platform:

- Steam:
  - Steam
  - Hellor
  - HLL Records
  - Helo
- Epic:
  - Hellor
  - HLL Records

## Teamkills Note

No teamkills fix was implemented here.

Reference:

- `TASK-251-investigate-teamkills-ranking-zeroes.md`

Observed state remains:

- `rcon_match_player_stats.teamkills` stays at zero in the audited dataset
- same-team kill events were not present in the audited AdminLog dataset
- lifetime profile snapshots can show TK counters, but they are not a valid direct source for annual ranking without redesign/backfill

## Validation

Executed:

- `node --check frontend/assets/js/stats.js`
- `python -m compileall backend/app`
- `cd backend; python -m unittest tests.test_current_match_payload`
- `cd backend; python -m unittest tests.test_historical_snapshot_refresh`
- `cd backend; python -m unittest tests.test_stats_player_profile_payload`

Static checks:

- no visible `ID:` remains in the personal profile card
- `current-week` / `current-month` no longer remain as visible UI labels
- external profile buttons do not print raw IDs on screen
- KPM is rendered only for `kpm_status == ready`

## Notes

- No scheduler changes.
- No RCON or server configuration changes.
- No asset changes were required.
