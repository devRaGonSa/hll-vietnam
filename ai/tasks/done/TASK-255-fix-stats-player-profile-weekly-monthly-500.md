# TASK-255 - Fix stats player profile weekly/monthly 500

## Summary

This task fixes the public player-profile weekly/monthly endpoints after a production audit reported:

- `stats-player-profile-weekly` -> `500`
- `stats-player-profile-monthly` -> `500`

The fix prioritizes endpoint availability and fast response over optional KPM enrichment.

## Affected Endpoint

Route:

- `/api/stats/players/{player_id}?timeframe=weekly`
- `/api/stats/players/{player_id}?timeframe=monthly`

Handler chain:

- `backend/app/routes.py`
- `build_stats_player_profile_payload(...)`
- `get_rcon_materialized_player_stats(...)`
- `_get_player_period_stats_read_model(...)`

## Root Cause

The player-period read model path already handled missing read-model rows defensively.

However, after the base read-model rows were loaded, the code opened a second read scope to compute optional active-time/KPM data:

- `player_active_seconds`
- `player_active_minutes`
- `kpm`
- `kpm_status`
- `active_time_source`
- `active_time_coverage`

That second lookup lived outside the original `try/except`.

If production schema or compatibility differences caused the active-time query to fail, the exception propagated and the whole profile endpoint returned `500` even though the base weekly/monthly profile data was already available.

## Fix

- keep weekly/monthly profile reads read-model-first
- keep runtime-heavy fallback disabled
- wrap the optional active-time read-model enrichment in a defensive fallback
- if active-time enrichment fails:
  - return `kpm = null`
  - return `kpm_status = missing_active_time`
  - return `player_active_seconds = null`
  - return `player_active_minutes = null`
  - keep external links and platform identity
  - still return `200`

This preserves public endpoint speed and avoids breaking the UI when KPM coverage is unavailable.

## Validation

Executed:

- `python -m compileall backend/app`
- `cd backend; python -m unittest tests.test_current_match_payload`
- `cd backend; python -m unittest tests.test_historical_snapshot_refresh`
- `cd backend; python -m unittest tests.test_stats_player_profile_payload`

Expected post-fix audit command:

```powershell
python .\scripts\audit_public_requests.py --base-url https://comunidadhll.devzamode.es --timeout 30 --output tmp\task255_full_audit_after.json
```

## Notes

- No TeamKills change.
- No scheduler change.
- No RCON/server configuration change.
- No asset change.
