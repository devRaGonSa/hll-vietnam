# Elo V3 Persistent Rating Model Completion

## Scope

This document records the persistent-rating contract completed in TASK-120.

## Persisted Formula Terms

- `own_team_average_mmr`
- `enemy_team_average_mmr`
- `expected_result`
- `actual_result`
- `won_score`
- `margin_boost`
- `outcome_adjusted`
- `match_impact`
- `combat_contribution`
- `objective_contribution`
- `utility_contribution`
- `survival_discipline_contribution`
- `exact_component_contribution`
- `proxy_component_contribution`
- `elo_core_delta`
- `performance_modifier_delta`
- `proxy_modifier_delta`
- `normalization_bucket_key`
- `normalization_fallback_reason`

## Formula Contract

- `ExpectedWin = 1 / (1 + 10 ^ ((EnemyTeamMMR - OwnTeamMMR) / 400))`
- `OutcomeScore = 2 * (Won - ExpectedWin)`
- `OutcomeAdjusted = clamp(OutcomeScore + MarginBoost, -1, 1)`
- `DeltaMMR = K * Q * (0.80 * OutcomeAdjusted + 0.20 * MatchImpact)`

## MatchImpact Boundary

`MatchImpact` is bounded to `[-1, 1]` and separates:

- combat contribution
- objective contribution
- utility contribution
- survival and discipline contribution

Current source split:

- exact-oriented side:
  - combat
  - utility
- proxy-oriented side:
  - objective
  - survival and discipline

## Normalization Boundary

The current persistent model consumes:

- `role_primary`
- `role_primary_mode`
- `normalization_bucket_key`
- `normalization_fallback_reason`

It does not yet apply full percentile-based rescaling inside the rating
formula. The normalization foundation is persisted and auditable, and later
tasks can tighten formula consumption without changing the bucket contract.
