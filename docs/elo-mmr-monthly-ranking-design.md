# Elo/MMR Monthly Ranking Design

## Scope

This repository now exposes an operational Elo/MMR system inspired by
`sistema_elo_mensual_hll.pdf`, but constrained to signals that are really
available today.

Current implementation label:

- practical PDF alignment at the `v3` level

Deferred explicitly:

- telemetry-complete `v3` evolution

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
  - proxied with opponent average MMR pressure plus match quality because there
    is no full roster-strength graph yet
- `DisciplineIndex`
  - combines exact teamkills with participation-based leave/AFK risk proxy

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
- player participation must be at least `600` seconds and at least `35%` of the
  resolved match duration for that player's row to count as valid

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
- canonical resolved match duration with explicit source status
- mode retention through `game_mode`
- approximate `role_bucket`
- explicit participation bucket per player-match fact
- per-time derived rates from existing stored metrics
  - `kills_per_minute`
  - `combat_per_minute`
  - `support_per_minute`
  - `objective_proxy_per_minute`

Not implemented yet:

- literal class role bucket

### Subindices

Implemented now:

- `OutcomeScore`: `exact`
- `CombatIndex`: `exact`
- `ObjectiveIndex`: `approximate`
- `UtilityIndex`: `exact`
- `LeadershipIndex`: `not_available`
- `DisciplineIndex`: `approximate`
  - exact for teamkills
  - approximate for leave/AFK risk via participation proxy

### ImpactScore

Implemented with role-inspired weights, but the role itself is approximate, so
the final `ImpactScore` is operationally `approximate`.

### DeltaMMR

Implemented from:

- `OutcomeScore`
- `ImpactScore`
- `StrengthOfScheduleMatch`
- player participation
- quality factor `Q`

The resulting `DeltaMMR` is real and persisted, but inherits the mixed
availability of the inputs above. The movement is now closer to an Elo pattern:

- expected result against opponent average MMR
- actual result from the player's mixed match score
- quality and participation scaling

## Storage Model

Tables added in backend SQLite:

- `elo_mmr_player_ratings`
- `elo_mmr_match_results`
- `elo_mmr_monthly_rankings`
- `elo_mmr_monthly_checkpoints`
- `elo_mmr_canonical_players`
- `elo_mmr_canonical_matches`
- `elo_mmr_canonical_player_match_facts`

Meaning:

- `elo_mmr_player_ratings`
  - current persistent rating per player and scope
- `elo_mmr_match_results`
  - per-match scoring trace used to explain rating movement
- `elo_mmr_monthly_rankings`
  - monthly ranking rows ready for product/API
- `elo_mmr_monthly_checkpoints`
  - generated-at metadata plus source policy and capability summary
- `elo_mmr_canonical_matches`
  - canonical closed-match context with resolved duration, duration bucket and
    player count
- `elo_mmr_canonical_player_match_facts`
  - player-match fact foundation with explicit participation buckets,
    objective proxy fields and per-minute derived rates

Canonical fact lineage now persisted and reused:

- `fact_schema_version = "elo-canonical-v3"`
- `source_input_version = "historical-closed-match-v1-plus-player-event-summary-v1"`

Current model/version family:

- persistent rating model:
  - `elo-pdf-v3-persistent-practical`
- persistent match formula revision:
  - `elo-pdf-v3-persistent-match-rev4`
- monthly ranking model:
  - `elo-pdf-v3-monthly-practical`
- monthly ranking formula revision:
  - `elo-pdf-v3-monthly-rev4`
- match result contract:
  - `elo-mmr-match-result-v4`
- monthly ranking contract:
  - `elo-mmr-monthly-ranking-v4`
- monthly checkpoint contract:
  - `elo-mmr-monthly-checkpoint-v4`

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
- a telemetry-rich v3 implementation

## Planned Expansion Path

The current design is compatible with future upgrades once real telemetry exists:

- replace approximate `ObjectiveIndex` with event-driven tactical signals
- add `LeadershipIndex` when squad/command telemetry exists
- replace approximate `StrengthOfSchedule` with opponent MMR graph logic
- feed V2 duels and weapon signals into richer combat weighting when their
  coverage is sufficient

## PDF Gap Analysis

This section closes the current repository audit against the formal monthly
Elo/MMR PDF design.

Important boundary:

- the original `sistema_elo_mensual_hll.pdf` is not present in this workspace
- this audit therefore uses the repository's own PDF-derived artifacts as the
  baseline source of truth:
  - this document
  - `backend/README.md`
  - `ai/tasks/done/TASK-097-elo-mmr-capabilities-and-data-contract.md`
  - `ai/tasks/done/TASK-098-elo-mmr-core-engine-v1-backed-by-real-signals.md`

That means the gap analysis below is a repository-grounded inference of the PDF
contract, not a verbatim re-read of the missing file.

### Component Matrix

| PDF design component | Current repository implementation | Status | Notes |
| --- | --- | --- | --- |
| Persistent `MMR` | Persisted by scope in `elo_mmr_player_ratings` and rebuilt from closed matches | `implemented_approximate` | Real persistence exists, but delta behavior is still constrained by proxy inputs and does not yet use the full PDF telemetry set |
| `DeltaMMR` | Computed per player and stored in `elo_mmr_match_results` | `implemented_approximate` | Operational and deterministic, but still inherits approximate quality, role and discipline signals |
| `MatchScore` | Computed per valid match and stored in `elo_mmr_match_results` | `implemented_approximate` | Exists, but today is driven by the available scoreboard telemetry rather than a full tactical event model |
| `MonthlyRankScore` | Computed monthly and stored in `elo_mmr_monthly_rankings` | `implemented_approximate` | Visible in API and persistence, but still combines exact and proxy components |
| Quality factor `Q` | Match-level bounded quality factor | `implemented_approximate` | Duration and score coverage are real when present; lobby density and coverage remain a practical proxy, not the full PDF notion |
| `OutcomeScore` | Derived from final team result | `implemented_exact` | Based on real allied/axis score and player team side |
| `ImpactScore` | Weighted mix of role-oriented subindices | `implemented_approximate` | Structure exists, but role inference and some subindices still use proxies |
| `StrengthOfSchedule` | Monthly proxy based on opponent average MMR pressure and match quality | `partially_implemented` | Exists only as an approximation; no full opponent-strength graph is persisted yet |
| role weighting | Role buckets inferred from scoreboard axes | `implemented_approximate` | Weighting exists, but the role identity itself is inferred rather than observed |
| discipline / penalties | Teamkills plus participation-based leave-risk proxy | `implemented_approximate` | Teamkills are real; AFK, leaves and other conduct signals are still absent |
| eligibility per match | Valid match gate plus player-level participation threshold | `implemented_approximate` | Player rows now require minimum time and participation, but not all desired telemetry exists |
| eligibility per leaderboard | Monthly valid-match, playtime and participation minimums | `implemented_approximate` | Operational thresholds exist, but they are still closer to a safe product contract than to a final PDF parity model |
| `LeadershipIndex` | No direct calculation | `not_implemented` | No leadership telemetry is persisted in the repo |
| exact tactical objective event stream | No direct calculation | `not_implemented` | `ObjectiveIndex` still uses offense and defense as proxy inputs |

### Formula Alignment Summary

Convergences already present:

- the system is split between persistent rating and monthly leaderboard score
- valid-match gating exists before rating changes count
- a bounded quality factor `Q` exists and affects rating movement
- the engine uses explicit subindices such as `OutcomeScore`,
  `ObjectiveIndex`, `UtilityIndex` and `DisciplineIndex`
- role-dependent weighting exists in the `ImpactScore` stage
- monthly eligibility is enforced separately from match scoring
- exact/approximate/not-available capability metadata is already exposed

Divergences or weak areas in the current implementation:

- `StrengthOfSchedule` now uses opponent rating pressure, but still not a full
  roster-strength graph
- role is inferred from scoreboard points, not from literal class or command role
- `DisciplineIndex` still cannot directly observe AFK, disconnect or
  abandonment behavior and must proxy that boundary through participation
- `ObjectiveIndex` is still a scoreboard proxy and not a tactical event model
- `LeadershipIndex` is absent rather than approximated
- match eligibility focuses on global match validity more than on player-level
  participation quality inside that match
- the formulas remain operationally aligned with the PDF intent, but not fully
  paralleled to a formal spec with all desired telemetry inputs

### Signal Inventory

Real signals available today:

- final allied and axis score
- team side
- kills
- deaths
- teamkills
- support points
- combat points
- offense points
- defense points
- match closed timestamps
- player playtime seconds
- persisted historical player identity
- canonical resolved match duration
- canonical duration buckets
- player participation buckets derived from persisted playtime and resolved
  duration
- per-minute rates derived from existing scoreboard metrics
- persisted player-event V2 summaries outside the current core Elo/MMR formula

Signals that currently exist only as proxies:

- player role via dominant scoreboard axis
- tactical objective contribution via `offense + defense`
- objective pace via `objective_proxy_per_minute`
- strength of schedule via opponent average MMR plus match quality proxy
- discipline beyond teamkills via participation-style heuristics when needed

Signals still not available in the repository:

- explicit commander, officer or squad-lead role identity
- garrison and outpost destruction
- revives and support actions with fine tactical granularity
- AFK, disconnect and voluntary leave events
- exact event-by-event objective capture timeline
- direct opponent roster-strength graph at the player level

### Recommended V2 Alignment Sequence

Safe to align now without fictional telemetry:

Already aligned in the current practical v3 implementation:

1. match eligibility uses player-level participation checks
2. `StrengthOfSchedule` uses persisted opponent-MMR pressure as an honest proxy
3. `DeltaMMR` depends on expected-vs-actual outcome rather than only on a flat
   combined score
4. discipline and participation boundaries are explicit
5. payloads expose richer component-level accuracy and fact-foundation metadata

Depends on future telemetry:

1. exact `LeadershipIndex`
2. exact role identity instead of inferred role buckets
3. exact tactical objective weighting
4. exact leave / AFK / discipline tracking
5. full parity `StrengthOfSchedule` from roster-strength graphs rather than
   opponent-rating approximations
