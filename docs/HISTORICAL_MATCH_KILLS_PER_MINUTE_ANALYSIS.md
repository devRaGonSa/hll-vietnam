# Historical Match Kills Per Minute Analysis

## Scope

This analysis covers the player table inside `historico-partida.html` for historical match detail.

## Question

Can the UI add a `Kills por minuto` column now without reintroducing false KPM?

## Short Answer

No.

## Why It Cannot Be Implemented Honestly Yet

The current historical match detail payload exposes player combat totals and match-level timing, but it does not expose a trustworthy player-level active time.

Available today:

- per player:
  - `kills`
  - `deaths`
  - `teamkills`
  - `kd_ratio` or enough data to derive it
  - `top_weapons`
  - `most_killed`
  - `death_by`
- per match:
  - `duration_seconds`
  - `started_at`
  - `ended_at`

Missing for real KPM:

- `player_active_seconds`
- real played minutes per player
- presence intervals
- a quality flag that tells whether playtime is exact, observed, estimated or unknown

## Data Review

`build_historical_match_detail_payload()` serves `item` from the RCON historical read model when available.

`historico-partida.js` currently renders the player table with:

- `Jugador`
- `Equipo`
- `Kills`
- `Muertes`
- `TK`
- `KD`

There is no frontend or payload field for honest KPM.

## Important Constraint

Real KPM must mean:

```text
kills / (player_active_seconds / 60)
```

It must not mean:

```text
kills / match_duration_minutes
```

unless the product intentionally introduces a different metric with a clearly different label.

## Existing Design Reference

`docs/REAL_KPM_PLAYER_ACTIVE_SECONDS_DESIGN.md` already documents the correct long-term direction:

- materialize `player_active_seconds`
- carry a playtime quality classification
- compute KPM in backend read models and snapshots
- never compute real KPM in frontend JavaScript

## Recommendation

Do not add the column now.

Safe next step:

1. Add real `player_active_seconds` to the historical player detail model.
2. Expose it in the match detail payload.
3. Add `Kills por minuto` only when backed by that field.

Optional weaker alternative, only with explicit product approval:

- `Kills/min partida`
- clearly labeled as match-duration-based
- never presented as player KPM
