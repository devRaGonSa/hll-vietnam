# TASK-247 - Implement real player active time and historical KPM

## Summary

This task implements the first real KPM base for historical match detail using reconstructed connection intervals from the RCON AdminLog materialization flow.

It does not use total match duration as a substitute for player time.

## Files Read First

- `backend/app/rcon_admin_log_materialization.py`
- `backend/app/rcon_admin_log_storage.py`
- `backend/app/rcon_historical_read_model.py`
- `backend/app/payloads.py`
- `backend/app/postgres_rcon_storage.py`
- `backend/app/config.py`
- `backend/tests/test_rcon_materialization_pipeline.py`
- `backend/tests/test_current_match_payload.py`
- `backend/tests/test_rcon_admin_log_storage.py`
- `frontend/assets/js/historico-partida.js`
- `frontend/historico-partida.html`
- `docs/REAL_KPM_PLAYER_ACTIVE_SECONDS_DESIGN.md`
- `docs/HISTORICAL_MATCH_KILLS_PER_MINUTE_ANALYSIS.md`

## Problem

Historical match detail could not show a real player KPM because the backend had no player-level active time persisted in the RCON materialized match facts.

Using total match duration would have reintroduced a false KPM.

## Decision

Use the existing RCON AdminLog materialization path as the source of truth.

For each player inside one materialized match:

- keep `first_seen_server_time`
- keep `last_seen_server_time`
- reconstruct connected intervals inside the match window
- persist `player_active_seconds` from those intervals when they are reliable
- mark `active_time_source` according to the interval quality

Reliable interval sources:

- `connection_intervals`
- `connection_intervals_carryover`

Fallback only, not valid for real KPM:

- `event_span_fallback`
- `unavailable`

Then expose KPM in the historical match detail payload only when active time is present and reaches a minimum threshold.

## Persistence

Added to `rcon_match_player_stats`:

- `player_active_seconds`
- `active_time_source`

This is applied for both SQLite and PostgreSQL schema initialization/migration.

Legacy rows remain compatible. They keep `player_active_seconds = null` until they are rematerialized or replaced by newer matches.

## KPM Rules

- Formula:
  - `kills / (player_active_seconds / 60)`
- Minimum threshold:
  - `HLL_KPM_MIN_ACTIVE_SECONDS`
  - default `60`
- If `player_active_seconds` is missing:
  - `kpm = null`
  - `kpm_status = missing_active_time`
- If active time comes only from fallback event span:
  - `kpm = null`
  - `kpm_status = missing_connection_intervals`
- If `player_active_seconds < 60`:
  - `kpm = null`
  - `kpm_status = insufficient_active_time`
- If active time is valid:
  - `kpm` is rounded to 2 decimals
  - `kpm_status = ready`
  - only when `active_time_source` is `connection_intervals` or `connection_intervals_carryover`

## Interval Rules

- connect inside match:
  - open interval at `connected.server_time`
- disconnect inside match:
  - close interval at `disconnected.server_time`
- connected before match start and no pre-start disconnect after that:
  - carry interval from `match_start`
- still connected at match end:
  - close interval at `match_end`
- reconnections:
  - sum all intervals
- inconsistent or incomplete connection evidence:
  - do not mark KPM as ready
  - keep `event_span_fallback` only as auxiliary observed time

## Squad Time

Not implemented.

This task reviewed the possibility of discounting time without squad/unit/role, but the current historical source is not reliable enough to compute `squad_active_seconds` safely. That remains future work.

## Frontend

`historico-partida.js` now shows a `KPM` stat chip in the expanded player panel only when `kpm_status == "ready"`.

Old matches without active time do not show a fake `0.00`.

## Validation

Executed:

- `python -m compileall backend/app`
- `cd backend; python -m unittest tests.test_current_match_payload`
- `cd backend; python -m unittest tests.test_rcon_admin_log_storage`
- `cd backend; python -m unittest tests.test_historical_snapshot_refresh`
- `cd backend; python -m unittest tests.test_rcon_materialization_pipeline.RconMaterializationPipelineTests.test_materialization_migrates_existing_player_stats_schema_with_active_time_columns`
- `cd backend; python -m unittest tests.test_rcon_materialization_pipeline.RconMaterializationPipelineTests.test_match_detail_keeps_kpm_missing_for_legacy_rows_without_active_time`
- `cd backend; python -m unittest tests.test_rcon_materialization_pipeline.RconMaterializationPipelineTests.test_match_detail_read_model_hides_raw_player_ids`
- `cd backend; python -m unittest tests.test_rcon_materialization_pipeline.RconMaterializationPipelineTests.test_active_time_counts_full_match_for_player_connected_before_start`
- `cd backend; python -m unittest tests.test_rcon_materialization_pipeline.RconMaterializationPipelineTests.test_active_time_counts_until_disconnect_for_player_connected_before_start`
- `cd backend; python -m unittest tests.test_rcon_materialization_pipeline.RconMaterializationPipelineTests.test_active_time_counts_from_connect_until_match_end`
- `cd backend; python -m unittest tests.test_rcon_materialization_pipeline.RconMaterializationPipelineTests.test_active_time_sums_multiple_connection_intervals`
- `cd backend; python -m unittest tests.test_rcon_materialization_pipeline.RconMaterializationPipelineTests.test_active_time_uses_event_span_fallback_without_ready_kpm_when_connection_intervals_missing`
- `cd backend; python -m unittest tests.test_rcon_materialization_pipeline.RconMaterializationPipelineTests.test_kpm_is_null_when_active_time_is_below_threshold`
- `cd backend; python -m unittest tests.test_rcon_materialization_pipeline.RconMaterializationPipelineTests.test_kpm_payload_helper_returns_ready_for_ten_kills_in_ten_minutes`
- `cd backend; python -m unittest tests.test_rcon_materialization_pipeline.RconMaterializationPipelineTests.test_kpm_payload_helper_returns_zero_for_zero_kills_with_valid_active_time`
- `cd backend; python -m unittest tests.test_rcon_materialization_pipeline.RconMaterializationPipelineTests.test_kpm_payload_helper_returns_missing_when_active_time_is_null`
- `node --check frontend/assets/js/historico-partida.js`

## Notes

- No scheduler changes were required.
- No RCON host/port/server config changes were made.
- No weapon/icon assets were touched.
- Historical KPM remains forward-valid only. Old rows stay null until real interval evidence exists.
