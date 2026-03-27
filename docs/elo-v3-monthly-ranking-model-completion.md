# Elo V3 Monthly Ranking Model Completion

## Scope

This document records the monthly ranking contract completed in TASK-121.

## Monthly Layer Boundary

The monthly layer remains separate from persistent MMR.

Persistent MMR is used as an input, but monthly ranking still persists its own:

- `baseline_mmr`
- `current_mmr`
- `mmr_gain`
- `avg_match_score`
- `strength_of_schedule`
- `consistency`
- `activity`
- `confidence`
- `penalty_points`
- `eligible`
- `eligibility_reason`
- `monthly_rank_score`

## Added Monthly Comparison Metadata

Persisted inside monthly component scores:

- `role_primary`
- `role_primary_mode`
- `comparison_path`
- `comparison_bucket_key`
- `role_bucket_sample_sufficient`
- `normalization_fallback_used`
- `minimum_participation_quality_threshold`
- `discipline_capability_status`
- `leave_admin_capability_status`
- `death_type_capability_status`

## Eligibility Rules

Current monthly eligibility requires:

- minimum valid matches
- minimum playtime
- minimum participation ratio
- minimum participation quality score

Current participation quality threshold:

- `45.0`

## Comparison Path

Primary monthly comparison:

- role-primary bucket comparison

Fallback comparison:

- role-all parent bucket when bucket coverage is insufficient

## Checkpoint Auditability

Monthly checkpoints now expose:

- versioned aggregation contract metadata
- monthly aggregation lineage summary
- explicit role-aware comparison and fallback boundary
- penalty boundary wording
