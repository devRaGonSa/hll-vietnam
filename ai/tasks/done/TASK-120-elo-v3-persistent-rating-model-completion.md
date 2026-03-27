# TASK-120

## Goal

Complete the persistent Elo/MMR model so it consumes the richer canonical fact
foundation and tactical inputs, and implements a fuller competitive rating model
with explicit formula contracts, bounded modifiers and auditable component
lineage.

## Context

The current persistent model already has:

- expected vs actual structure
- core delta
- performance modifier split
- proxy modifier split
- versioned contracts

That means the persistent competitive rating model is already structured and
auditable at a practical level. What is still missing is the completion step
that makes the model consume the richer tactical facts, role-truth inputs,
normalization inputs and discipline boundaries prepared by earlier tasks.

This task must complete the persistent model without removing auditability. It
must preserve explicit separation between exact and proxy components, and it
must keep every formula and contract version visible in storage and payload
surfaces.

Execution status: depends_on_previous_tasks

Dependencies:

- TASK-117
- TASK-118
- TASK-119

## Steps

1. Consume the richer canonical facts and normalization inputs.
2. Formalize the persistent rating formula contract end to end.
3. Implement or refine exact and proxy component boundaries.
4. Keep the rating delta auditable per match and per player.
5. Persist explicit before/after values and component breakdowns.
6. Version every formula and contract involved.
7. Use and document these required formula components explicitly:
   - `ExpectedWin = 1 / (1 + 10 ^ ((EnemyTeamMMR - OwnTeamMMR) / 400))`
   - `OutcomeScore = 2 * (Won - ExpectedWin)`
   - `OutcomeAdjusted = clamp(OutcomeScore + MarginBoost, -1, 1)`
8. Materialize a persistent rating formula equivalent to:
   - `DeltaMMR = K * Q * (0.80 * OutcomeAdjusted + 0.20 * MatchImpact)`
9. Keep the meaning of each formula term explicit:
   - `K` = rating movement constant
   - `Q` = match quality factor
   - `MatchImpact` = bounded player impact component
   - `OutcomeAdjusted` = result component after expected-vs-actual and allowed
     margin adjustment
10. Require the future implementation to build `MatchImpact` from explicit
    components, separating at least:
    - combat contribution
    - objective contribution
    - utility contribution
    - survival/discipline contribution
    - role-adjusted weighting
    - exact vs proxy source of each component
11. Define how `MatchImpact` remains bounded, including:
    - allowed min/max range
    - component clipping rules if required
    - normalization behavior when exact tactical data is incomplete
12. Define how team-level context should feed the rating formula, including:
    - own-team MMR basis
    - enemy-team MMR basis
    - margin boost allowance and bounds
    - role-aware weighting if supported by TASK-118
13. Ensure persisted match-result rows expose enough detail for a reviewer to
    trace:
    - expected result inputs
    - outcome adjustment inputs
    - match quality factor
    - exact component contributions
    - proxy component contributions
    - final delta composition

## Files to Read First

- `AGENTS.md`
- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_models.py`
- `backend/app/elo_mmr_storage.py`
- outputs from TASK-117, TASK-118, TASK-119

## Expected Files to Modify

- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_models.py`
- `backend/app/elo_mmr_storage.py`
- `backend/app/payloads.py`
- docs for persistent model contract

## Constraints

- Do not collapse tactical exact components into proxy-only fields.
- Do not remove auditable delta lineage.
- Keep the delta bounded and explainable.
- Keep model, formula and contract versioning explicit.
- Keep exact vs proxy component sources inspectable in persisted rows.
- Do not hide normalization or bucket fallback behavior inside opaque totals.
- Preserve backward compatibility reasonably where practical, but not by hiding
  the richer contract.

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

- rebuild succeeds from expanded canonical facts
- persisted player-rating rows are versioned
- persisted match-result rows expose balanced delta lineage
- exact vs proxy components are inspectable
- payloads still resolve without overstating unsupported data
- formula terms and contract versions are visible and auditable
- bounded `MatchImpact` and `OutcomeAdjusted` behavior are documented and
  inspectable

## Change Budget

- Keep this task centered only on persistent rating completion.
- Do not combine it with monthly-ranking completion or full-surface audit work.
