# TASK-251 - Investigate teamkills ranking zeroes

## Summary

This task audits why annual `teamkills` ranking data is missing or zeroed in practice.

No fix was implemented because the issue is upstream from the public ranking UI and needs a source decision first.

## Files Read First

- `backend/app/rcon_admin_log_parser.py`
- `backend/app/rcon_admin_log_storage.py`
- `backend/app/rcon_admin_log_materialization.py`
- `backend/app/rcon_historical_player_stats.py`
- `backend/app/rcon_annual_rankings.py`
- `backend/app/routes.py`
- `backend/tests/test_rcon_materialization_pipeline.py`

## Findings

### 1. Parser support exists

The parser already extracts:

- `killer_team`
- `victim_team`

The materialization code already increments:

- `teamkills`
- `deaths_by_teamkill`

when `killer_team == victim_team`.

Tests already cover this logic.

### 2. Local match facts contain no positive teamkills

Read-only local checks on `backend/data/hll_vietnam_dev.sqlite3` show:

- `rcon_admin_log_events` has many `kill` rows
- `rcon_match_player_stats where teamkills > 0` returns zero rows
- `rcon_annual_ranking_snapshot_items where teamkills > 0` returns zero rows

### 3. Local kill events contain no same-team kills

Read-only checks on parsed event payloads show:

- kill payloads include `killer_team` and `victim_team`
- but the local dataset contains zero `kill` rows where both teams are equal

That means the materialized player facts never receive a positive `teamkills` increment in this dataset.

### 4. Player profile snapshots do contain teamkill totals

`rcon_player_profile_snapshots` contains positive values for:

- `teamkills_done`
- `teamkills_received`

So the broader AdminLog/profile ecosystem does know about teamkills somewhere, but those totals are:

- lifetime-oriented
- not tied to one exact closed match window
- not directly usable for annual or per-match ranking backfills without a separate design

### 5. Annual public ranking payload currently returns empty for teamkills

Production and local checks both show:

- `/api/ranking?timeframe=annual&metric=teamkills&...` returns `items = []`

So the user-visible issue is not a frontend parse bug. It is a data-source gap for annual teamkill ranking inputs.

## Cause Probable

The annual ranking consumes `rcon_match_player_stats.teamkills`.

That field is derived from same-team `kill` events in the materialized AdminLog match stream.

In the audited dataset:

- same-team `kill` events are not present
- therefore `rcon_match_player_stats.teamkills` stays at zero
- therefore annual `teamkills` ranking has no rows

Meanwhile, profile snapshots expose lifetime teamkill totals, but they are not an annual closed-match ranking source.

## Decision

Do not patch the public ranking UI.

Do not inject lifetime `teamkills_done` into annual ranking, because that would mix incompatible time models.

Do not fabricate teamkills from unrelated signals.

## Follow-up Direction

The next correct task should choose one of these paths explicitly:

1. Confirm whether the real RCON/AdminLog kill stream should include same-team kills and why they are absent.
2. If same-team kills are absent by product/API behavior, define a separate ranking source for teamkills.
3. If an alternate raw source exists, backfill `rcon_match_player_stats.teamkills` from that source with tests.

## Validation

Read-only checks executed:

- local SQLite schema audit for:
  - `rcon_admin_log_events`
  - `rcon_match_player_stats`
  - `rcon_annual_ranking_snapshots`
  - `rcon_annual_ranking_snapshot_items`
- local count of `event_type='kill'`
- local count of `teamkills > 0` in materialized player stats
- local count of same-team parsed kill events
- local inspection of `parsed_payload_json` samples
- local inspection of `rcon_player_profile_snapshots.teamkills_done/teamkills_received`
- production endpoint checks for:
  - annual all-servers teamkills ranking
  - annual comunidad-hispana-01 teamkills ranking
  - annual comunidad-hispana-02 teamkills ranking

## Notes

- No backend code changed.
- No frontend code changed for this audit.
- No migrations or data writes were performed.
