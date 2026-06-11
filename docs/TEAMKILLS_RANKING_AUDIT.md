# Teamkills Ranking Audit

## Scope

This document explains why annual public `teamkills` ranking currently returns no usable rows in the audited dataset.

## What Was Checked

Sources reviewed:

- `rcon_admin_log_events`
- `rcon_match_player_stats`
- `rcon_annual_ranking_snapshots`
- `rcon_annual_ranking_snapshot_items`
- `rcon_player_profile_snapshots`

Code reviewed:

- `backend/app/rcon_admin_log_parser.py`
- `backend/app/rcon_admin_log_storage.py`
- `backend/app/rcon_admin_log_materialization.py`
- `backend/app/rcon_annual_rankings.py`
- `backend/app/routes.py`
- `backend/tests/test_rcon_materialization_pipeline.py`

## What Works Already

The parser and materialization pipeline already support teamkills when the source event is explicit enough.

The key condition is:

```text
killer_team == victim_team
```

When that is true, the materializer increments:

- `teamkills` on the killer
- `deaths_by_teamkill` on the victim

This behavior is covered by regression tests.

## What The Local Dataset Shows

Read-only checks on `backend/data/hll_vietnam_dev.sqlite3` show:

- many `kill` events exist
- zero `rcon_match_player_stats` rows with `teamkills > 0`
- zero annual ranking snapshot items with `teamkills > 0`
- zero parsed `kill` events where `killer_team == victim_team`

That means the annual ranking source facts never receive positive teamkill values.

## What The Profile Snapshots Show

`rcon_player_profile_snapshots` does contain positive:

- `teamkills_done`
- `teamkills_received`

So the broader data ecosystem knows teamkills somewhere, but those values are:

- cumulative
- profile-oriented
- not scoped to exact closed match windows

Using them directly for annual ranking would be semantically wrong.

## Public Endpoint Check

The current public endpoint returns empty annual teamkill ranking items for:

- `all`
- `comunidad-hispana-01`
- `comunidad-hispana-02`

So the problem is not a frontend-only rendering issue.

## Conclusion

The current annual teamkills ranking depends on:

- `rcon_match_player_stats.teamkills`

In the audited dataset, that field remains zero because the match-level kill stream does not contain same-team kill events that the materializer can classify as teamkills.

## Safe Next Step

Do not fake teamkills from unrelated counters.

The next implementation task should first decide whether:

1. the event stream is incomplete and needs parser/source correction, or
2. teamkills need a dedicated ranking source different from match-level kill events.
