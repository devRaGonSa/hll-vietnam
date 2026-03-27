# Elo Full System Contracts Surface And Auditability

## Scope

This document records the final contract and auditability surface after
TASK-116 through TASK-122.

## Implemented System Label

Implemented practical branch:

- `elo-pdf-v3-practical`

Deferred telemetry-complete branch:

- `telemetry-complete-v3`

The repository now exposes a practical v3 system with explicit exact,
approximate and unavailable boundaries. It does not claim telemetry-complete
v3 parity.

## Versioned Contract Surface

Canonical fact lineage:

- `canonical_fact_schema_version = "elo-canonical-v3"`
- `canonical_source_input_version = "historical-closed-match-v1-plus-player-event-summary-v1"`

Persistent rating layer:

- `model_version = "elo-pdf-v3-persistent-practical"`
- `formula_version = "elo-pdf-v3-persistent-match-rev4"`
- `contract_version = "elo-mmr-player-rating-v4"`
- `match_result_contract_version = "elo-mmr-match-result-v4"`

Monthly ranking layer:

- `model_version = "elo-pdf-v3-monthly-practical"`
- `formula_version = "elo-pdf-v3-monthly-rev4"`
- `contract_version = "elo-mmr-monthly-ranking-v4"`
- `checkpoint_contract_version = "elo-mmr-monthly-checkpoint-v4"`

Event lineage foundation:

- `contract_version = "elo-event-telemetry-v1"`
- storage strategy:
  - `hybrid-header-plus-family-detail`

## Auditable Lineage

The implemented lineage is now visible as:

1. `elo_event_lineage_headers`
2. `elo_mmr_canonical_player_match_facts`
3. `elo_mmr_match_results`
4. `elo_mmr_player_ratings`
5. `elo_mmr_monthly_rankings`
6. `elo_mmr_monthly_checkpoints`

Payload surfaces now expose:

- top-level `accuracy_contract`
- top-level `model_contract`
- top-level `auditability`
- `rating_breakdown.fact_foundation`
- `rating_breakdown.delta_sources`
- `rating_breakdown.materialization`
- monthly checkpoint aggregation lineage

## Exact, Approximate And Unavailable Boundary

Exact today:

- `OutcomeScore`
- `CombatIndex`
- `UtilityIndex`
- match validity gating
- player participation thresholds
- teamkills as an exact discipline signal

Approximate today:

- `ObjectiveIndex`
- role comparison buckets
- `StrengthOfSchedule`
- leave-risk and discipline proxies beyond teamkills
- approximate death-classification summary lineage

Unavailable today:

- leadership telemetry
- raw garrison and outpost telemetry
- revive, supply, node, repair and mine telemetry
- commander ability telemetry
- strongpoint presence event telemetry
- raw leave and admin event telemetry
- exact death-type telemetry for redeploy, suicide or menu exits

## Deferred Tactical Dependencies

The remaining blocked tactical families stay explicit:

- `garrison-events`
- `outpost-events`
- `revive-events`
- `supply-events`
- `node-events`
- `repair-events`
- `mine-events`
- `commander-ability-events`
- `strongpoint-presence-events`
- `role-assignment-events`
- `disconnect-leave-admin-events`
- `death-classification-events`
- `leadership-index`

## Review Outcome

A reviewer can now trace:

- canonical fact schema and source-input lineage
- event lineage availability and capability wording
- persistent rating versions and match-result contract versions
- monthly ranking versions and checkpoint lineage
- exact/proxy/unavailable signal boundaries
- remaining deferred telemetry dependencies
