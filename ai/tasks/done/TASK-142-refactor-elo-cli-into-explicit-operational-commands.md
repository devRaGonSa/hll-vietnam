# TASK-142-refactor-elo-cli-into-explicit-operational-commands

## Goal

Refactor the Elo/MMR CLI into explicit operational commands with clearly separated scope.

## Context

The current `backend/app/elo_mmr_engine.py` CLI exposes `rebuild`, `leaderboard`, and `player`, but the operational rebuild flow still bundles too many responsibilities behind one rebuild entrypoint. Maintenance, canonical rebuild, persistent rating rebuild, and monthly rematerialization remain too coupled for safe operations. That makes the CLI hard to use surgically and increases the chance that an operator triggers heavyweight work that was not actually needed.

Future implementation must separate maintenance, canonical rebuild, rating rebuild, and monthly refresh into explicit commands or submodes with clear naming and scope. `refresh-monthly` must remain lightweight and must not rebuild the entire pipeline. Any temporary compatibility layer should exist only if it is reasonable and clearly documented.

## Steps

1. Inspect the listed files first and document what the current CLI `rebuild` path actually does end to end.
2. Define and implement explicit commands or equivalent submodes such as:
   - `rebuild-full`
   - `rebuild-canonical`
   - `rebuild-ratings`
   - `refresh-monthly`
   - `historical-maintenance`
3. Make each command state clearly what it does and what it does not do, including whether it prepares storage, rebuilds canonical data, recalculates ratings, rematerializes monthly outputs, or runs historical maintenance.
4. Keep temporary compatibility for the current `rebuild` command only if it is operationally reasonable, and document the mapping clearly.
5. Validate that operators can now run only the needed part of the pipeline and that monthly refresh does not trigger a full rebuild.

## Files to Read First

- `AGENTS.md`
- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_storage.py`
- `backend/app/historical_storage.py`
- `backend/app/postgres_utils.py`
- `backend/app/writer_lock.py`

## Expected Files to Modify

- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_storage.py` only if narrower callable rebuild surfaces must be exposed there
- `backend/app/historical_storage.py` only if explicit maintenance entrypoints must be wired there
- minimal directly related docs or help text files if necessary
- only minimal directly related files if required

Rules:

- Prefer modifying only these files.
- If additional files become necessary, explain why in the task outcome or commit message.
- Do not modify unrelated files.

## Constraints

- Keep the change minimal.
- Preserve HLL Vietnam project identity.
- Do not introduce unnecessary frameworks or dependencies.
- Do not redesign Elo/MMR formulas or product-facing API payloads in this task.
- Keep the work focused on CLI separation, operator safety, and explicit scope boundaries.
- Historical maintenance must be explicit and outside the normal operational rebuild path.
- `refresh-monthly` must not rebuild canonical data or rerun the full scoring pipeline.
- Command names, help text, and output must make scope boundaries unambiguous.

## Validation

Before completing the task ensure:

- `python -m compileall backend/app` passes
- `python -m app.elo_mmr_engine --help` clearly exposes the new operational command separation
- operators can run only canonical rebuild, only ratings rebuild, only monthly refresh, or explicit historical maintenance
- monthly refresh no longer triggers a full rebuild
- historical maintenance is explicit and outside the normal rebuild path
- commands expose operationally clear scope and behavior
- `git diff --name-only` is reviewed
- `git status --short` is reviewed
- no unrelated files were modified
- documentation remains consistent with the repository state

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
