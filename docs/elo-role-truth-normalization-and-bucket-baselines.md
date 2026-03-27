# Elo Role Truth Normalization And Bucket Baselines

## Scope

This document records the normalization foundation added in TASK-118.

Implemented now:

- explicit normalization bucket keys on canonical player-match facts
- persisted bucket baseline tables
- explicit fallback metadata when the primary bucket sample is insufficient
- persisted role-primary resolution using the best currently available input

Current role-truth status:

- exact role-truth: unavailable
- current fallback: approximate scoreboard-axis role resolution

## Canonical Buckets

Persisted dimensions:

- `role_primary`
- `game_mode`
- `duration_bucket`
- `participation_bucket`
- `player_count_bucket`
- `match_shape_bucket`

Persisted fact columns:

- `role_primary`
- `role_primary_mode`
- `normalization_bucket_key`
- `normalization_bucket_version`
- `normalization_fallback_bucket_key`
- `normalization_fallback_reason`
- `normalization_version`
- `player_count_bucket`
- `match_shape_bucket`

## Role Resolution

Current resolution order:

1. exact role assignment events
   - unavailable in the current repo
2. fallback scoreboard-axis role
   - `support`
   - `offense`
   - `defense`
   - `combat`
   - `generalist`

Current `role_primary_mode`:

- `approximate` when scoreboard participation or score axes exist
- `not_available` otherwise

## Baseline Storage

Tables:

- `elo_mmr_normalization_buckets`
- `elo_mmr_normalization_baselines`

Bucket table stores:

- bucket key and version
- normalization version
- bucket dimensions
- sample count
- insufficient-sample marker
- fallback bucket key
- fallback reason

Baseline table stores per metric:

- sample count
- average
- min
- max
- p50
- p90

## Metrics Prepared For Normalization

- `kills_per_minute`
- `combat_per_minute`
- `support_per_minute`
- `objective_proxy_per_minute`
- `participation_ratio`
- `participation_quality_score`
- `death_summary_combat_kills`
- `death_summary_combat_deaths`
- `death_summary_teamkills`
- `tactical_event_count`

## Fallback Rule

Primary bucket:

- full bucket with resolved `role_primary`

Current parent fallback:

- same bucket dimensions with `role_primary = all`

Fallback is persisted when:

- primary bucket sample count is below `NORMALIZATION_MIN_BUCKET_SAMPLE`

Current fallback reason values:

- `primary-bucket-insufficient-fallback-to-role-all`
- `primary-bucket-insufficient-no-parent-bucket`

## Boundary

This task does not claim exact role truth.

It only makes the fallback path explicit and auditable so later Elo tasks can
consume:

- explicit bucket resolution
- explicit bucket sample sufficiency
- explicit baseline lineage
