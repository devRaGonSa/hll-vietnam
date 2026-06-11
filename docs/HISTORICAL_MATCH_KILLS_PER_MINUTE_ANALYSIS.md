# Historical Match Kills Per Minute Analysis

## Scope

This document defines how real historical KPM works for the match detail served to `historico-partida.html`.

## Why KPM Was Not Safe Before

Historical match detail already exposed:

- per player:
  - `kills`
  - `deaths`
  - `teamkills`
  - weapon and matchup counters
- per match:
  - `started_at`
  - `ended_at`
  - `duration_seconds`

What it did not expose was player-level active time. Because of that, dividing by total match duration would have produced a false player KPM.

## Real KPM Rule

Real KPM means:

```text
kills / (player_active_seconds / 60)
```

It does not mean:

```text
kills / match_duration_minutes
```

## Source of Truth

The current implementation uses connection intervals reconstructed from the materialized RCON AdminLog match model.

Reliable interval signals:

- `connected`
- `disconnected`
- `match_start`
- `match_end`

Supporting evidence still stored in the player fact:

- `first_seen_server_time`
- `last_seen_server_time`

The persisted field is:

- `player_active_seconds`

The source label is:

- `active_time_source = "event_log"`

## Persistence

Forward-only persistence now stores on `rcon_match_player_stats`:

- `player_active_seconds INTEGER NULL`
- `active_time_source TEXT`

Legacy rows remain valid. If they were materialized before these columns existed, they keep `player_active_seconds = NULL` until new materialization or new matches populate the field.

## Calculation

Observed active time is now:

```text
sum(connected_interval_seconds clamped to [match_start, match_end])
```

Rules:

- if the player connects during the match:
  - open interval at `connected.server_time`
- if the player disconnects during the match:
  - close interval at `disconnected.server_time`
- if the player was already connected before `match_start` and there is no later pre-match disconnect:
  - open interval at `match_start`
- if the player is still connected at `match_end`:
  - close interval at `match_end`
- if the player reconnects multiple times:
  - sum all non-overlapping intervals

This is still observed presence, not exact telemetry down to every silent second.

KPM is exposed only when:

- `player_active_seconds` exists
- `player_active_seconds >= HLL_KPM_MIN_ACTIVE_SECONDS`

Default:

- `HLL_KPM_MIN_ACTIVE_SECONDS = 60`

## Payload Contract

Historical match detail player rows may now expose:

- `player_active_seconds`
- `player_active_minutes`
- `kpm`
- `kpm_status`
- `active_time_source`

`active_time_source` values currently used:

- `connection_intervals`
- `connection_intervals_carryover`
- `event_span_fallback`
- `unavailable`

`kpm_status` values:

- `ready`
- `missing_active_time`
- `insufficient_active_time`
- `missing_connection_intervals`

Rules:

- missing active time:
  - `kpm = null`
  - `kpm_status = "missing_active_time"`
- fallback event span without reliable connection intervals:
  - `kpm = null`
  - `kpm_status = "missing_connection_intervals"`
- active time below threshold:
  - `kpm = null`
  - `kpm_status = "insufficient_active_time"`
- valid active time:
  - `kpm = round(kills / (player_active_seconds / 60), 2)`
  - `kpm_status = "ready"`
  - only when `active_time_source` is `connection_intervals` or `connection_intervals_carryover`

## Historical Matches Already Stored

Old matches are not backfilled with fake KPM.

For those rows:

- `player_active_seconds` can remain `null`
- `kpm` stays `null`
- frontend must not render `0.00` as if the value were real
- rows rematerialized without reliable connection intervals can still expose
  `event_span_fallback`, but that fallback must not be shown as real KPM

## Frontend Rule

`historico-partida.js` renders KPM only when:

- `kpm_status == "ready"`

If the value is missing or below threshold, the panel stays clean and does not show a fake metric.

## Limitations

- This is observed active time from AdminLog connection evidence, not exact join/leave telemetry for every silent second.
- Quiet players with kills/chat/team switches but no reliable connection chain can expose `event_span_fallback`; that span is intentionally blocked from KPM.
- Legacy matches remain without KPM unless rematerialized from stored AdminLog evidence.
- We do not discount time spent without squad/unit/role yet because there is no audited historical source for that dimension in this implementation.
