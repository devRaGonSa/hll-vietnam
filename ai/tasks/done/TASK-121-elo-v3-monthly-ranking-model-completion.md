# TASK-121

## Goal

Complete the monthly ranking model so it becomes a fully separated, event-aware
monthly competition layer built from persisted match facts and persistent rating
movement, with explicit eligibility, confidence, activity, consistency and
penalty logic.

## Context

The current monthly model already has:

- monthly ranking persistence
- checkpoints
- activity/consistency/confidence style components
- versioned contracts

That means the repository already has a clear separation between persistent
rating and monthly ranking at a practical level. What remains is to complete the
richer monthly system so it can incorporate:

- tactical/event-aware inputs
- normalization-aware inputs
- role-aware monthly comparison
- stronger penalty and eligibility handling

This task must keep monthly ranking clearly separate from persistent MMR while
making the monthly layer more complete, more auditable and more explicit about
eligibility and penalties.

Execution status: depends_on_previous_tasks

Dependencies:

- TASK-118
- TASK-119
- TASK-120

## Steps

1. Consume expanded canonical facts and richer persistent rating outputs.
2. Keep monthly ranking clearly separated from persistent rating.
3. Refine monthly score components and their persisted contracts.
4. Add richer monthly eligibility and penalty handling.
5. Add role-aware or bucket-aware monthly comparisons where supported.
6. Preserve checkpoint lineage and monthly rebuild auditability.
7. Materialize and persist these fields explicitly:
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
8. Require the future implementation to order the monthly ranking using a
   formula equivalent to an explicit combination of:
   - `MMRGain`
   - `AvgMatchScore`
   - `StrengthOfSchedule`
   - `Consistency`
   - `Activity`
   - `Confidence`
   - `PenaltyPoints`
9. Define how monthly eligibility should be evaluated, including explicit
   persisted rules for:
   - minimum valid matches
   - minimum playtime
   - minimum participation quality
   - role/bucket sample sufficiency when role-aware comparison is enabled
10. Define how monthly penalties should be applied, including:
    - discipline-linked penalties
    - leave/disconnect/admin penalties if available from TASK-119
    - explicit capability status when penalty categories remain proxy or
      unavailable
11. Define how role-aware or bucket-aware monthly comparison should work, when
    supported, including:
    - comparison within role/bucket baselines
    - fallback behavior when role/bucket data is insufficient
    - persisted explanation fields that show which comparison path was used
12. Preserve checkpoint-level auditability by requiring monthly checkpoint rows
    to expose:
    - generation timestamp
    - model version
    - formula version
    - contract version
    - source policy
    - capability summary
    - monthly aggregation lineage summary

## Files to Read First

- `AGENTS.md`
- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_storage.py`
- `backend/app/payloads.py`
- outputs from TASK-118, TASK-119, TASK-120
- `docs/elo-mmr-monthly-ranking-design.md`

## Expected Files to Modify

- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_storage.py`
- `backend/app/payloads.py`
- docs for monthly model contract

## Constraints

- Do not merge monthly score semantics with persistent MMR semantics.
- Do not hide eligibility rules inside opaque ranking totals.
- Keep checkpoint generation auditable and versioned.
- Make role-aware monthly comparison explicit, not implicit.
- Keep penalty logic inspectable and capability-aware.
- Preserve the distinction between event-aware exact inputs and proxy-only
  fallback inputs.

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

- monthly rebuild succeeds
- monthly rankings persist explicit component scores
- eligibility and eligibility reason are populated
- checkpoint rows expose versioned monthly contract data
- payloads clearly separate persistent rating from monthly ranking
- role-aware or bucket-aware comparison path is explicit where supported
- penalty and capability boundaries remain inspectable

## Change Budget

- Keep this task centered only on monthly ranking completion.
- Do not combine it with persistent-rating completion or final full-surface
  audit work.
