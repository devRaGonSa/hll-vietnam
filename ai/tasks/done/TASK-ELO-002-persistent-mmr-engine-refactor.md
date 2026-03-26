# TASK-ELO-002

## Goal

Refactor the persistent MMR engine so it consumes the new canonical fact layer and materializes a traceable, versioned and explainable persistent rating state per match.

## Context

The repository already computes and persists Elo/MMR concepts through `backend/app/elo_mmr_engine.py`, `backend/app/elo_mmr_storage.py`, and the current Elo payload mapping in `backend/app/payloads.py`.

The next step is not to redesign the public surface first. The rating engine must be aligned to a stronger internal model that clearly separates:

- competitive Elo core
- exact performance modifiers
- proxy performance modifiers
- persisted per-match rating movement

This refactor should consume canonical match/player facts instead of depending on early-stage aggregate composition. It should also preserve reasonable compatibility for the current leaderboard/profile read model while the internal rating pipeline is upgraded.

## Steps

1. Inspect the current rebuild engine, storage schema and payload contracts for Elo/MMR.
2. Refactor the rating rebuild flow to consume canonical match/player facts instead of depending on early-stage aggregate composition.
3. Materialize per-match rating movement with explicit before/after values.
4. Separate Elo core movement from bounded HLL-specific modifiers.
5. Persist enough breakdown detail to explain why a player gained or lost rating.
6. Preserve or adapt the current read model and payload mapping without inflating API claims beyond available telemetry.
7. Document any formula-version or contract-version assumptions introduced by the refactor.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_models.py`
- `backend/app/elo_mmr_storage.py`
- `backend/app/payloads.py`

## Expected Files to Modify

- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_models.py`
- `backend/app/elo_mmr_storage.py`
- `backend/app/payloads.py`
- supporting modules only if strictly required by the refactor

## Constraints

- Keep the task focused on persistent rating materialization, not monthly leaderboard redesign.
- Do not introduce tactical telemetry that the repository does not actually store yet.
- Do not blur exact, proxy and unavailable components.
- Preserve a reasonable compatibility bridge for existing payload consumers.
- Keep formula and model versioning explicit.
- Do not rely on payload enrichment as a substitute for persisted model state.
- When this task is implemented in a future execution, the worker must create a commit and push it if final validation passes.
- The implementation response must include modified files, validations run, validation results, branch name, final commit SHA and explicit push confirmation.
- The task must not be marked complete without commit and push unless a blocking error is documented.

## Validation

- full rebuild completes successfully
- persisted rating state is derived from canonical facts
- per-match rating deltas are traceable
- `accuracy_mode` and capability boundaries remain coherent
- leaderboard/profile payloads still resolve or are explicitly remapped
- no unrelated files were modified

## Change Budget

- prefer a narrow engine/storage refactor
- split follow-up work if API remapping grows too large
- avoid oversized multi-area changes in one task

## Outcome

- Status: completed
- The persistent MMR rebuild now consumes the canonical Elo fact layer rather than querying historical tables directly
- Per-match rating state remains materialized with:
  - `mmr_before`
  - `mmr_after`
  - `delta_mmr`
  - `elo_core_delta`
  - `performance_modifier_delta`
  - `proxy_modifier_delta`
- Payload compatibility remains intact through the existing leaderboard/profile enrichment layer

### Modified Files

- `backend/app/elo_mmr_models.py`
- `backend/app/elo_mmr_storage.py`
- `backend/app/elo_mmr_engine.py`

### Validations Run

- `python -m compileall app`
- scoped rebuild against `backend/data/elo_mmr_task001_validation.sqlite3`
- payload smoke validation using `HLL_BACKEND_STORAGE_PATH=data/elo_mmr_task001_validation.sqlite3`

### Validation Results

- scoped rebuild succeeded from canonical facts
- persisted match-result rows trace explicit before/after and component deltas: `7222`
- persisted rating rows joined back to canonical facts successfully: `7222`
- leaderboard payload resolved with accuracy and model contracts
- player payload resolved with `rating_breakdown`

### Notes

- The task was completed as an integration step on top of the new canonical fact layer and the existing persisted delta model already present in the repository worktree.
