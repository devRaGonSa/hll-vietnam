# TASK-ELO-001

## Goal

Introduce a canonical Elo fact layer ahead of the current Elo/MMR read model so the repository can rebuild persistent rating and monthly ranking from persisted match/player facts instead of API-oriented composition.

## Context

The repository already contains a working Elo/MMR area with a rebuild engine in `backend/app/elo_mmr_engine.py`, dedicated SQLite persistence in `backend/app/elo_mmr_storage.py`, enriched API payloads in `backend/app/payloads.py`, and orchestration logic in `backend/app/historical_runner.py`.

The next correct evolution is not to keep extending payload composition or read-model enrichment. The system needs a canonical, traceable fact layer that:

- captures match-level player facts from historical closed-match data
- decouples calculation from exposure
- enables deterministic rebuilds of persistent rating and monthly ranking
- supports future rating formula versions without depending on payload enrichment or legacy compatibility bridges

This task builds on the existing Elo/MMR system and does not replace the current API surface yet. Its purpose is to create the canonical foundation that later tasks can consume.

## Steps

1. Inspect the existing Elo/MMR pipeline and the current persistence/read-model split.
2. Design and add a canonical match/player fact layer for Elo/MMR.
3. Introduce canonical entities or tables for stable player identity, closed-match identity and per-player match facts.
4. Persist the minimum inputs required to rebuild rating and monthly ranking without depending on API-only composition.
5. Version the canonical layer inputs so future formula revisions remain auditable.
6. Wire the canonical layer to historical closed-match consolidation without breaking the current read model.
7. Document any structural boundary or migration assumption if the implementation changes architecture expectations.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_storage.py`
- `backend/app/historical_runner.py`

## Expected Files to Modify

- `backend/app/elo_mmr_storage.py`
- `backend/app/elo_mmr_engine.py`
- `backend/app/historical_runner.py`
- `backend/app/historical_*` modules if needed for canonical consolidation
- migration or schema support files if the repository pattern requires them

## Constraints

- Keep the change focused on the canonical Elo data foundation.
- Do not redesign frontend or public API in this task.
- Do not collapse read-model and fact-model responsibilities into one table.
- Preserve current repository identity and existing Elo/MMR API surface as much as possible.
- Minimize coupling to CRCON internal structures.
- Do not claim exact telemetry where only proxy data exists.
- Keep future rebuilds deterministic and auditable.
- When this task is implemented in a future execution, the worker must create a commit and push it if final validation passes.
- The implementation response must include modified files, validations run, validation results, branch name, final commit SHA and explicit push confirmation.
- The task must not be marked complete without commit and push unless a blocking error is documented.

## Validation

- canonical player-match facts can be persisted from existing historical closed-match data
- stable player identity does not depend on display name only
- the canonical layer contains enough information to rebuild rating and monthly ranking later
- capability status can distinguish `exact`, `approximate` and `not_available`
- unrelated files remain untouched
- documentation stays consistent if architecture assumptions change

## Change Budget

- prefer fewer than 5 modified files when feasible
- split follow-up work if the scope expands
- keep the first implementation bounded to the canonical layer

## Outcome

- Status: completed
- Scope kept to the canonical Elo foundation and existing rebuild path
- Canonical storage added for:
  - stable player identities
  - closed-match identities
  - per-player closed-match facts
- Canonical facts are versioned with:
  - `fact_schema_version = "elo-canonical-v1"`
  - `source_input_version = "historical-closed-match-v1"`
- The Elo rebuild now materializes and reads the canonical fact layer before scoring

### Modified Files

- `backend/app/elo_mmr_storage.py`
- `backend/app/elo_mmr_engine.py`

### Validations Run

- `python -m compileall app`
- full canonical fact materialization against `backend/data/hll_vietnam_dev.sqlite3`
- end-to-end rebuild against scoped validation DB `backend/data/elo_mmr_task001_validation.sqlite3`

### Validation Results

- canonical players persisted: `163766` on the full local historical DB
- canonical matches persisted: `9673` on the full local historical DB
- canonical player-match facts persisted: `1064496` on the full local historical DB
- scoped validation rebuild succeeded with canonical inputs:
  - canonical players: `1515`
  - canonical matches: `30`
  - canonical player-match facts: `3611`
- stable identity does not depend on display name only:
  - `245` canonical players in the scoped validation DB had no `steam_id` but still resolved through stable non-name identity
- canonical capability statuses persisted and distinguish:
  - `exact`
  - `approximate`
  - `not_available`

### Notes

- Full Elo rebuild on the full development DB did not finish within the interactive command timeout, so end-to-end rebuild validation was completed on a scoped SQLite copy while canonical fact materialization was validated on the full local DB.

### Audit Correction

- Audit status: kept in `done`.
- Reason:
  - a canonical Elo fact layer now exists in real repository code
  - canonical players, canonical matches and canonical player-match facts are materially persisted in dedicated Elo tables
  - the rebuild engine consumes canonical match rows instead of reading historical stats tables directly
- Boundary kept explicit:
  - this task is considered closed for the canonical fact foundation only
  - downstream persistent-rating and monthly-aggregation concerns remain subject to separate audit decisions
