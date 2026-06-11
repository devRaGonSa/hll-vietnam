---
id: TASK-239
title: Analyze kills per minute column for historical match detail
status: done
type: research
team: Analista
supporting_teams:
  - Frontend Senior
  - Backend Senior
roadmap_item: foundation
priority: medium
---

# TASK-239 - Analyze kills per minute column for historical match detail

## Goal

Determine whether a `Kills por minuto` column can be added honestly to the historical match detail page without reintroducing false KPM.

## Files Read First

- `docs/REAL_KPM_PLAYER_ACTIVE_SECONDS_DESIGN.md`
- `frontend/assets/js/historico-partida.js`
- `backend/app/payloads.py`
- `backend/app/rcon_historical_read_model.py`
- `backend/app/rcon_historical_player_stats.py`

## Findings

1. `historico-partida.js` currently shows only:
   - player name
   - team
   - kills
   - deaths
   - teamkills
   - KD
2. The historical match detail payload comes from `build_historical_match_detail_payload()` and `get_rcon_historical_match_detail()`.
3. The current match detail data includes:
   - match duration
   - match start/end
   - player kills/deaths/teamkills
   - `top_weapons`, `most_killed`, `death_by`
4. The current detail payload does not expose:
   - `player_active_seconds`
   - `play_time`
   - per-player presence intervals
   - any trustworthy per-player played-minutes field
5. The existing design document already states that real KPM is blocked until `player_active_seconds` exists as a real materialized field.

## Conclusion

Do not implement `Kills por minuto` now.

The repository still lacks a trustworthy player-level time-played field for historical match detail. Using match duration would only produce `kills por minuto de partida`, not real player KPM, and that was explicitly ruled out.

## Honest Alternatives

Possible future options:

1. Real KPM:
   - only after `player_active_seconds` is materialized per player and per match
2. Explicitly different metric:
   - `Kills/min partida`
   - only if product explicitly wants that weaker metric and labels it as match-duration-based

## Implementation Recommendation

Current recommendation: do not add the column yet.

Required before implementation:

1. Backend field such as `player_active_seconds`
2. Payload exposure for that field in historical match detail
3. Clear UI distinction between:
   - real KPM
   - kills per match
   - any match-duration-derived metric

## Validation

- Analysis only
- No frontend implementation changed for this task
- No backend code changed
- No API contract changed

## Outcome

The task confirms that real `Kills por minuto` cannot be implemented safely today and should remain out of the UI until the data model supports it.
