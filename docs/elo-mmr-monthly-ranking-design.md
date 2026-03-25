# Elo/MMR Monthly Ranking Design

## Scope

This repository now exposes a first operational Elo/MMR-like system inspired by
`sistema_elo_mensual_hll.pdf`, but constrained to signals that are really
available today.

The implementation keeps the same conceptual split:

- persistent `MMR`
- monthly `MonthlyRankScore`

It does **not** claim full parity with the PDF. Every major signal is labeled as:

- `exact`
- `approximate`
- `not_available`

## Real Inputs Available Today

Exact today from persisted historical CRCON/public-scoreboard data:

- closed match identity
- server scope
- player identity
- team side
- kills
- deaths
- support
- teamkills
- combat score
- offense score
- defense score
- match timestamps when present
- final allied/axis score

Exact today from current product state but not required by the core engine:

- player-event V2 summaries for duels, most-killed, death-by and weapon summaries

Approximate only:

- `role_bucket`
  - inferred from the dominant scoreboard axis among `combat`, `offense`,
    `defense` and `support`
- `ObjectiveIndex`
  - proxied with `offense + defense` because there is no tactical event feed
- `StrengthOfSchedule`
  - proxied with match quality and lobby density because there is no opponent MMR
    model yet

Not available today:

- explicit squad role / commander / SL role
- garrisons and OPs destroyed
- revives
- AFK and leave events
- precise leadership telemetry
- exact tactical objective event stream
- exact opponent-strength graph by roster

## Current Capability Contract

### Match validity

Current rule:

- match must be closed
- match duration must be at least `15` minutes
- match must have at least `20` persisted player rows

Duration source:

- `exact` if `started_at` and `ended_at` exist
- `approximate` if we must fall back to max player `time_seconds`

### Quality factor Q

Current `Q` is a bounded mix of:

- player density
- match duration
- score completeness

This is an operational approximation of the PDF quality factor and is labelled:

- `exact` for the density and score-completeness inputs
- `exact` or `approximate` for duration depending on timestamp availability

### Buckets

Implemented:

- duration bucket
- mode retention through `game_mode`
- approximate `role_bucket`

Not implemented yet:

- literal class role bucket

### Subindices

Implemented now:

- `OutcomeScore`: `exact`
- `CombatIndex`: `exact`
- `ObjectiveIndex`: `approximate`
- `UtilityIndex`: `exact`
- `LeadershipIndex`: `not_available`
- `DisciplineIndex`: `exact` for teamkills only

### ImpactScore

Implemented with role-inspired weights, but the role itself is approximate, so
the final `ImpactScore` is operationally `approximate`.

### DeltaMMR

Implemented from:

- `OutcomeScore`
- `ImpactScore`
- quality factor `Q`

The resulting `DeltaMMR` is real and persisted, but inherits the mixed
availability of the inputs above.

## Storage Model

Tables added in backend SQLite:

- `elo_mmr_player_ratings`
- `elo_mmr_match_results`
- `elo_mmr_monthly_rankings`
- `elo_mmr_monthly_checkpoints`

Meaning:

- `elo_mmr_player_ratings`
  - current persistent rating per player and scope
- `elo_mmr_match_results`
  - per-match scoring trace used to explain rating movement
- `elo_mmr_monthly_rankings`
  - monthly ranking rows ready for product/API
- `elo_mmr_monthly_checkpoints`
  - generated-at metadata plus source policy and capability summary

Scopes persisted:

- per historical server
- `all-servers`

## Runtime Source Policy

The Elo/MMR engine follows the same historical policy as the rest of backend:

- primary intent: `rcon`
- current competitive calculation fallback: `public-scoreboard`

Why fallback still exists here:

- the current RCON historical read model only supports coverage and recent
  activity
- it does not yet expose enough competitive match detail to support this Elo/MMR
  engine directly

That fallback is exposed in API metadata through:

- `primary_source`
- `selected_source`
- `fallback_used`
- `fallback_reason`
- `source_attempts`

## Product Read Model

Current API surfaces:

- `/api/historical/elo-mmr/leaderboard`
- `/api/historical/elo-mmr/player`

These payloads expose:

- persistent rating
- monthly ranking score
- eligibility
- component breakdown
- exact/approximate/partial capability metadata

## Important Limitations

This first version should be treated as:

- operational
- honest about accuracy
- compatible with future expansion

It should **not** be described as:

- a perfect Elo system
- full parity with the PDF
- a complete tactical rating model

## Planned Expansion Path

The current design is compatible with future upgrades once real telemetry exists:

- replace approximate `ObjectiveIndex` with event-driven tactical signals
- add `LeadershipIndex` when squad/command telemetry exists
- replace approximate `StrengthOfSchedule` with opponent MMR graph logic
- feed V2 duels and weapon signals into richer combat weighting when their
  coverage is sufficient
