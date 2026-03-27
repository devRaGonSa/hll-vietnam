# TASK-119

## Goal

Implement the exact/proxy discipline boundary required for the full Elo model,
including explicit leave/admin-action lineage and death-type classification when
supported by available event capture.

## Context

The current Elo/MMR system already uses:

- teamkills
- participation heuristics
- approximate discipline boundaries

That is a practical starting point, but it is not yet sufficient for a fuller
discipline model. The complete system needs a more explicit separation between:

- exact teamkill discipline
- leave/disconnect penalties
- kick/ban/admin penalties
- exact death-type exclusion when supported
- honest fallback when unsupported

This task should make the discipline and death-classification boundary explicit
in persisted Elo inputs, contracts and documentation. It should not overstate
telemetry quality. Exact treatment is only valid where exact event capture
exists.

Execution status: depends_on_previous_tasks

## Steps

1. Define the discipline and leave model inputs.
2. Materialize exact discipline events when available.
3. Materialize exact leave/admin-action lineage when available.
4. Add exact death-type classification support where event capture allows it.
5. Define fallback behavior when exact death/departure telemetry is missing.
6. Expose exact/proxy/unavailable boundaries to stored Elo inputs and
   contracts.
7. Ensure the implementation explicitly distinguishes these persisted states:
   - `teamkill_exact`
   - `leave_disconnect_exact`
   - `kick_or_ban_exact`
   - `admin_action_exact`
   - `death_type_exact`
   - `discipline_proxy_only`
   - `death_type_not_available`
8. Support, when exact event data exists, explicit tracking for:
   - redeploy deaths
   - suicide deaths
   - menu-exit deaths
   - combat deaths
   - friendly-fire deaths
   - disconnect before end
   - explicit leave without return
   - kick/ban/admin removals
9. Define how these exact or proxy inputs flow into persisted Elo-side facts,
   including:
   - match-level counters
   - player-level counters
   - penalty eligibility markers
   - capability status per counter
10. Define how to handle cases where partial support exists, such as:
    - teamkills exact but leave reasons unavailable
    - death feed exact for combat/friendly-fire but not for menu exits
    - admin actions exact at match level but not yet attributable to player with
      confidence
11. Ensure the model distinguishes unsupported categories from zero-valued exact
    categories so later workers do not confuse:
    - no event happened
    - event family unsupported
    - event family partially supported

## Files to Read First

- `AGENTS.md`
- outputs from TASK-116 and TASK-117
- `backend/app/elo_mmr_storage.py`
- `backend/app/elo_mmr_engine.py`
- `docs/elo-v3-competitive-gap-and-telemetry-boundary.md`

## Expected Files to Modify

- `backend/app/elo_mmr_storage.py`
- `backend/app/elo_mmr_engine.py`
- event ingestion/model files if required
- docs for discipline/death contracts

## Constraints

- Do not claim exact death-type exclusion unless backed by exact event capture.
- Do not hide leave/admin limitations behind generic penalty fields.
- Preserve exact/proxy/not_available boundaries in persisted fields and docs.
- Keep discipline lineage auditable from source events to Elo-facing persisted
  inputs.
- Do not conflate unsupported categories with zero event counts.
- Do not widen scope into a full persistent-rating rewrite.

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

- persisted discipline/death fields clearly show exact vs proxy
- exact event-backed counters exist where supported
- unsupported death or leave categories remain explicitly unavailable
- no wording overstates telemetry quality
- lineage exists from persisted discipline/death counters back to their source
  event family or explicit proxy rule

## Change Budget

- Keep this task focused only on discipline, death and leave boundaries.
- Do not combine it with unrelated tactical scoring or monthly-ranking work.
