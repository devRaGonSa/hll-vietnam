# TASK-118

## Goal

Replace approximate role/bucket assumptions with stronger role-truth and
normalization inputs, and introduce persistent normalization baselines for fair
player comparison across role, mode and match-shape buckets.

## Context

The current Elo/MMR model already uses:

- duration buckets
- participation buckets
- quality buckets
- approximate role logic

That foundation is useful, but it is still not strong enough for fair tactical
comparison across different player contexts. A fuller model needs more truthful
role-time attribution and a persistent normalization baseline system so players
are not compared only through ad hoc within-match heuristics.

The stronger comparison model should be able to organize player performance
using, when available:

- truthful role-time
- game mode
- duration bucket
- participation shape
- potentially team-size / match-shape buckets
- persistent normalization baselines rather than ad hoc comparisons

This task depends on TASK-117 because richer role/event data is required before
role truth and stronger normalization baselines can be materialized honestly.

Execution status: depends_on_previous_tasks

Dependency:

- TASK-117

## Steps

1. Define the canonical bucket model used for Elo normalization.
2. Promote role-truth from event/assignment data when available.
3. Define fallback rules when role-truth is unavailable.
4. Create persistent normalization baseline storage for bucket-level
   distributions.
5. Materialize normalization-ready values or percent-rank-ready inputs for
   match facts and monthly components.
6. Keep every bucket and normalization field versioned and auditable.
7. Define at least these buckets in the canonical normalization model:
   - `role_primary`
   - `game_mode`
   - `duration_bucket`
   - `participation_bucket`
   - optional `player_count_bucket` if supported
   - optional `match_shape_bucket` if supported
8. Define how `role_primary` is resolved, including:
   - exact role-truth from role assignment events
   - time-weighted role resolution if a player changed role during a match
   - fallback behavior if role assignment coverage is partial
   - explicit approximate or unavailable status when role-truth cannot be
     established
9. Introduce persistent normalization baseline storage that captures, at
   minimum:
   - bucket key/version
   - sample count per bucket
   - baseline distribution metadata
   - normalization version
   - percentile/rank-ready derived values or equivalent persisted normalization
     inputs
   - explicit fallback path when a bucket has insufficient data
10. Define which Elo-related measures should become normalization-ready, such as:
    - tactical per-match component values
    - tactical per-minute rates
    - participation-adjusted outputs
    - monthly component comparisons
11. Define how insufficient-sample buckets are handled, including:
    - fallback to a broader bucket
    - fallback to a parent bucket version
    - explicit persisted marker that the bucket sample is insufficient
12. Ensure every normalization field remains auditable by preserving:
    - source fact lineage
    - bucket resolution path
    - normalization version
    - fallback reason if the primary bucket was not used

## Files to Read First

- `AGENTS.md`
- `backend/app/elo_mmr_models.py`
- `backend/app/elo_mmr_storage.py`
- `backend/app/elo_mmr_engine.py`
- outputs from TASK-117
- `docs/elo-mmr-monthly-ranking-design.md`

## Expected Files to Modify

- `backend/app/elo_mmr_models.py`
- `backend/app/elo_mmr_storage.py`
- `backend/app/elo_mmr_engine.py`
- docs for bucket/normalization contracts

## Constraints

- Do not rely on display-name heuristics for role truth.
- Do not mix normalization baselines with leaderboard presentation-only logic.
- Every normalization field must have a versioned contract.
- If a bucket lacks enough data, persist the fallback strategy explicitly.
- Keep role-truth and fallback logic inspectable and auditable.
- Do not merge bucket resolution rules into opaque scoring code without
  persisted baseline metadata.
- Do not widen scope into final persistent rating completion or monthly-ranking
  completion.

Push policy for future execution:

* If this task is implemented and other pending tasks from the same Elo backlog batch still remain open, the worker must not push yet.
* In that case, the worker may commit locally if the repo workflow requires it, but final push must wait until the last pending task of the same backlog batch is completed.
* If this task is the last remaining pending task in the same Elo backlog batch and final validation passes, the worker must commit and push.
* The final implementation response must always state:

  * modified files
  * validations run
  * validation results
  * branch name
  * final commit SHA
  * whether push was executed or intentionally deferred because more pending tasks from the same batch remain
* No task should claim final backlog completion without the required final push, unless a blocking error is documented.

## Validation

- proof that bucket keys are explicit and persisted
- proof that normalization inputs or baseline tables are persisted
- proof that role-truth and fallback logic are documented
- proof that insufficient-sample handling is explicit
- proof that normalization versioning is visible and auditable
- proof that bucket resolution paths are reconstructable from persisted data

## Change Budget

- Keep this task centered only on normalization and bucket foundation.
- Do not widen scope into a major scoring-model rewrite.
- Defer final rating and monthly consumption changes to later tasks.
