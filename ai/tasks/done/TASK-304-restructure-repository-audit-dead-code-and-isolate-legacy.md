---
id: TASK-304
title: Restructure repository, audit dead code and isolate legacy
status: done
type: backend
team: Arquitecto Python
supporting_teams:
  - Backend Senior
  - Analista
roadmap_item: crcon-cutover
priority: high
---

# TASK-304 - Restructure repository, audit dead code and isolate legacy

## Goal

Make the CRCON-first architecture visually discoverable, isolate only proven
rollback/unmigrated legacy code, and classify genuinely unused code without
changing public behavior or disabling writers.

## Context

TASK-293 through TASK-303 established selectable CRCON REST, WebSocket and
read-only PostgreSQL paths while retaining legacy rollback. The backend is now
large and flat enough that services, workers, storage and tools are difficult
to distinguish. This task is a move-first structural refactor and evidence-led
audit, not a product redesign or shutdown task.

Safety checkpoint: before any move, branch, HEAD, status and diff were audited.
Local commit `9a7592d` preserves the complete pre-TASK-304 worktree, including
stacked CRCON work and pre-existing user files. No stash, reset, clean or push
was used.

## Steps

1. Inventory and classify every `backend/app` Python module and audit tests,
   frontend, deployment, docs, tasks, entrypoints and environment variables.
2. Publish a coherent proposed tree before moving files; preserve the cohesive
   existing `app/crcon` package unless dependency evidence justifies churn.
3. Move in independently testable batches, updating imports and module-name
   entrypoints without changing public URLs or contracts.
4. Split only clearly migrated orchestration/serialization responsibilities
   from `payloads.py`; do not rewrite the façade or migrate frameworks.
5. Isolate only modules proven rollback-only by the TASK-303 ledger. Keep
   MVP/player-event/Elo as `PRODUCT_DECISION_REQUIRED`.
6. Audit dead code through imports, routes, frontend, Compose, scripts,
   schedulers, `python -m`, dynamic entrypoints, tests and documentation.
7. Delete only candidates satisfying every `SAFE_DELETE` condition; preserve
   unknown, rollback, dynamic and product-owned code.
8. Audit duplication, configuration, frontend/test structure and dependency
   direction; consolidate only proven-equivalent helpers.
9. Create `docs/CODE_STRUCTURE.md`, update the dependency ledger paths, run the
   full required validation matrix and document baseline failures separately.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/python-architect.md`
- `backend/README.md`
- `docs/decisions.md`
- `docs/CRCON_FIRST_LEGACY_DEPENDENCY_LEDGER.md`

## Expected Files to Modify

- backend application module paths and their imports
- focused tests/imports when paths move
- Compose/scripts only when a moved dynamic module entrypoint requires it
- `docs/CODE_STRUCTURE.md`
- `docs/CRCON_FIRST_LEGACY_DEPENDENCY_LEDGER.md`
- architecture index/repository context
- this task file

The change budget is intentionally larger than normal because this task is an
authorized structural refactor. Moves must be batched and behavior-preserving.

## Constraints

- No deployment, CRCON modification, mutable production access, writer
  shutdown, gameplay database deletion or broad frontend redesign.
- Do not classify by filename alone and do not delete `UNKNOWN`.
- Preserve public URLs, JSON contracts, feature flags and immediate rollback.
- Domain code must not import clients, drivers, environment parsing or legacy
  storage. New CRCON-first services must not acquire hidden legacy dependencies.
- Prefer practical packages over many one-file micro-packages.

## Validation

- Run TASK-293–303 CRCON/current-match/history/ranking/stats tests.
- Run frontend snapshot, Historical UI and Stats/Ranking regression checks.
- Run compileall, JavaScript syntax, integration validation and diff checks.
- Run full discovery; document pre-existing failures without expanding scope.
- Confirm every deletion has recorded `SAFE_DELETE` evidence and every move is
  reflected in docs, Compose/scripts and dynamic entrypoints.

## Outcome

Completed locally without deployment or runtime/storage mutation.

- Created safety checkpoint `9a7592d` before moving files.
- Classified all 76 pre-refactor backend Python modules and inventoried tests,
  frontend, deployment, docs, tasks, environment variables and dynamic
  entrypoints in `docs/CODE_STRUCTURE.md`.
- Added `app/api`, `app/services` and `app/tools`; retained the cohesive
  `app/crcon` integration package.
- Moved six application services, four documented tools and the API
  route/payload facade; updated imports, scripts and current documentation.
- Kept the TASK-298 parity observer at its existing module path; only import
  paths required by the service/API moves changed, with no observer behavior
  change and no new observation wait.
- Extracted pure compatibility serializers, reducing the payload facade from
  2,990 to 2,904 lines. Routes remain 572 lines and contain no SQL or transport
  parsing.
- Removed only `SAFE_DELETE` code: `crcon/database.py`, the test-only
  `CrconDatabase` alias, and deprecated PostgreSQL player name/exact-ID search
  SQL/methods superseded by CRCON REST in TASK-303.
- Did not mass-move mixed legacy modules. Snapshot history, RCON workers,
  historical materialization/storage and derived writers remain required for
  rollback or undecided product features.
- MVP, player-event and Elo/MMR remain `PRODUCT_DECISION_REQUIRED`.
- Updated `docs/CRCON_FIRST_LEGACY_DEPENDENCY_LEDGER.md`, architecture index and
  repository context. No writer is shutdown-ready.

Validation:

- 197 CRCON/current-match focused tests: pass.
- 48 historical/ranking/stats/scoreboard focused tests: pass (existing SQLite
  connection `ResourceWarning`s remain non-failing).
- Historical UI plus Stats/Ranking integration script: pass; live HTTP check
  skipped cleanly because no backend was running, while imported route-contract
  checks passed.
- frontend snapshot Node tests: 37 pass.
- all frontend JavaScript `node --check`: pass.
- `compileall app tests`: pass.
- tool `--help`/import smoke checks: pass.
- `git diff --check`: pass (Git only reports repository line-ending warnings).
- Full unittest discovery ran 315 tests and retains four baseline issues not
  caused by TASK-304: missing optional `pytest` for
  `test_audit_rcon_match_materialization`; two already-stale legacy recent-match
  assertions contradicted by the pre-checkpoint snapshot fast path; and one
  historical-runner maintenance expectation (`ok` versus `partial`). The two
  recent-match failures also expose pre-existing unclosed SQLite handles on
  Windows cleanup. No product behavior was changed to mask these baselines.

Final assessment:

- `STRUCTURE_REFACTOR = GO`
- `DEAD_CODE_CLEANUP = PARTIAL` (only proven-safe code removed)
- `LEGACY_WRITER_DISABLE_READINESS = NOT_READY`

## Change Budget

The broader-than-normal file count is justified by behavior-preserving moves,
import/command-path updates and documentation path alignment. The checkpoint
and focused validation batches were used throughout; no mass legacy move was
attempted.
