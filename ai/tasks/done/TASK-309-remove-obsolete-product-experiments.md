---
id: TASK-309
title: Remove MVP, player-event compatibility and Elo/MMR vertical slices
status: done
type: refactor
team: Backend Senior
supporting_teams:
  - Frontend Senior
  - Arquitecto Python
  - Arquitecto de Base de Datos
roadmap_item: CRCON-first migration
priority: high
---

# TASK-309 - Remove obsolete product experiments

## Goal

Remove the approved MVP V1/V2, player-event compatibility and Elo/MMR
application vertical slices while preserving stored data, migrations, shared
rollback writers, deployment configuration and every surviving CRCON-first
public domain.

## Context

TASK-308 proved these features have no frontend consumer but retained their
public contracts pending product approval. Product has now explicitly approved
removal and accepts the compatibility break.

## Steps

1. Trace exclusive routes, payloads, algorithms, entrypoints, tests, frontend
   helpers, exports and current documentation.
2. Remove complete safe application slices without changing schemas, stored
   data, deployment or shared rollback writers.
3. Reclassify retained writer/storage artifacts whose lifecycle is deferred.
4. Validate removed-route behavior and all surviving CRCON-first domains.
5. Record reduction, move this task to done and create one local commit.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `docs/CRCON_FIRST_LEGACY_DEPENDENCY_LEDGER.md`
- `docs/CODE_STRUCTURE.md`
- `backend/app/api/routes/product_features.py`
- `backend/app/api/payloads/product_features.py`
- `backend/app/api/routes/__init__.py`
- `backend/app/api/payloads/__init__.py`

## Expected Files to Modify

- exclusive MVP, player-event and Elo/MMR application modules
- route/payload registries and focused tests
- unreachable exclusive Historical frontend helpers/styles
- current architecture documentation and this task record

## Constraints

- No table/schema/data deletion, migration rewrite, deployment edit, shared
  writer shutdown, remote access, CRCON change, credential search, parity wait
  or production action.
- Preserve normal monthly/annual rankings and opaque player IDs.
- Do not leave compatibility tombstones or empty product-feature modules.

## Validation

- Removed-route and route ownership contracts
- Focused CRCON/current-match/Log Stream/history/search/ranking tests
- Frontend current-match, Historical and Stats/Ranking regressions
- Python compileall, JavaScript syntax, full backend discovery and diff checks

## Outcome

- Removed the complete MVP V1/V2, player-event compatibility and Elo/MMR
  application slices, including eight public routes, payload exports,
  algorithms/read models, exclusive worker/rebuild code, configuration,
  frontend helpers/styles and obsolete current documentation.
- Removed the now-empty product-feature route/payload modules. The public
  registry is reduced from 37 to 29 URLs across six uniquely owned routers;
  removed URLs use normal unmatched-route behavior.
- Proved the rivalry/duel readers, `player_event_worker` and Elo rebuild path
  had no surviving reader, rollback, startup, Compose, systemd, CI or script
  dependency, then removed them. No dead writer implementation remains.
- Preserved all database tables, rows, SQLite files, migrations, old snapshot
  artifacts, deployment and shared rollback writers. Seven feature tables plus
  old MVP/player-event snapshots are `DEAD_STORAGE_CANDIDATE`.
- Recorded `APPLICATION_GAMEPLAY_STORAGE_TARGET = NONE`,
  `LEGACY_FEATURE_BLOCKERS = NONE` and
  `LEGACY_WRITER_DISABLE_READINESS = READY_AFTER_RUNTIME_VALIDATION` in the
  dependency ledger.
- Reduction before this outcome update: 18 deleted files, approximately 5,824
  removed Python lines, 609 removed JavaScript lines and 82 removed test lines
  (8,177 net lines removed overall).
- Validation passed: Python compileall; JavaScript syntax; 195 focused
  CRCON/current-match/Log Stream/history/search/ranking tests; 37 frontend
  current-match tests; Historical UI regression; Stats/Ranking regression;
  route ownership/removal tests; and `git diff --check`.
- Full backend discovery ran 325 tests and retained only the four declared
  baseline/environment issues: missing optional pytest, two legacy RCON
  materialization expectations and the runner `ok`/`partial` expectation. No
  new regression was found.

## Change Budget

- This is an approved complete vertical-slice deletion; prefer fewer surviving
  edits, and measure deleted Python, JavaScript and test lines explicitly.
