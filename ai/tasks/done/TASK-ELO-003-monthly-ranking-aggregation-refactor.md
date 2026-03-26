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

- Status: completed on 2026-03-26
- Closure summary:
  - monthly aggregation is now materialized through a dedicated monthly-ranking builder boundary instead of being implied by the persistent match-scoring loop
  - monthly ranking rows remain distinct from persistent player ratings and now stamp explicit:
  - `model_version`
  - `formula_version`
  - `contract_version`
  - monthly checkpoints now persist auditable generation contracts and capability summaries with an embedded aggregation contract description
  - leaderboard/profile payloads still resolve while exposing the monthly model boundary more clearly

### Modified Files

- `backend/app/elo_mmr_storage.py`
- `backend/app/elo_mmr_engine.py`
- `backend/app/payloads.py`
- `backend/app/elo_mmr_models.py`

### Validations Run

- `python -m compileall app`
- `HLL_BACKEND_STORAGE_PATH=backend/data/elo_mmr_task001_validation.sqlite3 python -m app.elo_mmr_engine rebuild`
- SQLite verification of monthly ranking rows, checkpoint contract stamps and explicit eligibility outputs
- leaderboard/profile payload smoke validation using the scoped validation DB

### Validation Results

- monthly rebuild succeeded from persisted model state
- monthly ranking rows with explicit eligibility outcome and version stamps: `3030`
- monthly checkpoint rows with generated metadata, source policy and v2 checkpoint contract: `2`
- leaderboard payload resolved from the persisted monthly model with separated persistent/monthly contracts
- player profile payload resolved with monthly `rating_breakdown`

### Notes

- No integration test script exists for this Elo/MMR scope, so validation stayed at compile, rebuild, SQLite contract checks and payload smoke checks.
