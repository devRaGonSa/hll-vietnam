# TASK-ELO-003

## Goal

Rebuild the monthly ranking aggregation from canonical persisted facts and materialized rating state, keeping it clearly separate from the persistent MMR domain.

## Context

The repository already exposes leaderboard and player-profile Elo/MMR data through `backend/app/payloads.py` and persists monthly ranking state in `backend/app/elo_mmr_storage.py`.

The next correct evolution is for the visible monthly ranking to be driven by:

- canonical facts
- persisted rating movement
- monthly eligibility rules
- explicit confidence, activity, consistency and penalty scoring

This should replace opportunistic API-only composition and tighten the separation between persistent player rating and the monthly visible ranking. The existing API surface should remain reasonably compatible while the internal monthly model becomes clearer and more auditable.

## Steps

1. Inspect the current monthly Elo/MMR ranking persistence and payload flow.
2. Rebuild monthly ranking aggregation on top of canonical facts and persisted rating movement.
3. Materialize monthly baseline, gain, match-score and schedule/context components explicitly.
4. Add or refine monthly eligibility, confidence, activity, consistency and penalty handling.
5. Keep monthly ranking distinct from persistent player rating in storage and payload contracts.
6. Preserve checkpoint metadata and generation traceability.
7. Document any ranking-formula or checkpoint-contract changes required by the refactor.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_storage.py`
- `backend/app/payloads.py`
- `backend/app/historical_runner.py`

## Expected Files to Modify

- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_storage.py`
- `backend/app/payloads.py`
- `backend/app/historical_runner.py`
- checkpoint or snapshot support only if truly required

## Constraints

- Keep this task focused on monthly ranking aggregation, not on redesigning the persistent rating engine from scratch.
- Do not merge monthly leaderboard score with persistent MMR semantics.
- Do not redesign frontend/UI in this task.
- Keep checkpoint generation auditable.
- Preserve reasonable API compatibility while strengthening the internal monthly model.
- Do not pretend that advanced tactical telemetry already exists.
- Push requirement:
- After implementing this task, if final validation passes, the worker must commit and push the changes.
- The final response must include:
  - modified files
  - validations run
  - validation results
  - branch name
  - final commit SHA
  - explicit confirmation that push was completed
- The task must not be marked as completed without commit and push, unless a blocking error is documented.

## Validation

- monthly rebuild succeeds from persisted model state
- leaderboard items are derived from canonical facts plus persisted rating movement
- eligibility and eligibility reasons are explicit and testable
- monthly checkpoint metadata remains coherent
- player profile and leaderboard contracts remain explainable
- no unrelated files were modified

## Change Budget

- keep the first implementation of this refactor bounded
- split role-specific or telemetry-advanced ranking work into later tasks
- avoid oversized API/frontend spillover

## Outcome

- Status: reopened after audit
- Progress already delivered:
  - monthly ranking remains distinct from persistent MMR in storage terms and rebuilds on top of:
  - canonical persisted match facts
  - materialized per-match rating movement
  - explicit eligibility, confidence, activity, consistency and penalty fields
- checkpoint metadata and payload contracts remain explainable

### Modified Files

- `backend/app/elo_mmr_storage.py`
- `backend/app/elo_mmr_engine.py`

### Validations Run

- `python -m compileall app`
- scoped rebuild against `backend/data/elo_mmr_task001_validation.sqlite3`
- leaderboard/profile payload smoke validation using the scoped validation DB

### Validation Results

- monthly rebuild succeeded from persisted model state
- monthly ranking rows with explicit eligibility outcome: `3030`
- monthly checkpoint rows with generated metadata and source policy: `2`
- leaderboard payload resolved from the persisted monthly model
- player profile payload resolved with monthly `rating_breakdown`

### Notes

- Audit correction:
  - this task was reopened because the published branch does not clearly demonstrate that the monthly aggregation refactor is fully closed as a distinct internal layer
  - the monthly ranking logic is still embedded inside the Elo engine rather than shown as a clearly separated aggregation boundary
  - the branch evidence is sufficient to show progress, but not sufficient to justify leaving the task in `done` under a conservative audit standard
