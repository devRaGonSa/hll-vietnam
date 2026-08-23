---
id: TASK-308
title: Resolve MVP, player-events and Elo/MMR ownership
status: done
type: research
team: Analista
supporting_teams:
  - Backend Senior
  - Frontend Senior
  - Arquitecto de Base de Datos
  - Arquitecto Python
roadmap_item: CRCON-first migration
priority: high
---

# TASK-308 - Resolve MVP, player-events and Elo/MMR ownership

## Goal

Resolve the remaining product-decision legacy domains, identify the minimum
genuine application-owned gameplay state, and reduce false writer blockers
without waiting for runtime credentials or changing any deployed writer/data.

## Context

TASK-307 separated implementation and runtime evidence and left MVP V1/V2,
player-events and Elo/MMR as the remaining product decisions. This task traces
their complete frontend-to-writer chains and removes code only if every
SAFE_DELETE gate is satisfied.

## Steps

1. Trace current HTML/JavaScript, route, payload, helper, table, writer, job,
   test, documentation and dynamic-entrypoint references for all three domains.
2. Classify actual product visibility, event semantics, CRCON replacement,
   storage ownership and rollback temperature.
3. Remove only complete dead vertical slices with conclusive SAFE_DELETE
   evidence; retain uncertainty and active compatibility contracts.
4. Update the dependency ledger and create a short product-decision document
   only if usage evidence cannot resolve a choice.
5. Run focused product/CRCON/frontend tests and full backend discovery.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `docs/CRCON_FIRST_LEGACY_DEPENDENCY_LEDGER.md`
- `backend/app/api/routes/product_features.py`
- `backend/app/api/payloads/product_features.py`
- `frontend/assets/js/historico.js`

## Expected Files to Modify

- `docs/CRCON_FIRST_LEGACY_DEPENDENCY_LEDGER.md`
- `docs/PRODUCT_FEATURE_DECISIONS_REQUIRED.md` only if a choice remains
- conclusively dead product-feature vertical slices and their obsolete tests,
  only if SAFE_DELETE evidence is complete
- this task lifecycle record

## Constraints

- Local-only audit/cleanup: no deployment, writer shutdown, table/data deletion,
  remote CRCON/PostgreSQL mutation, credential search, parity observation or
  runtime-validation work.
- Preserve opaque player IDs and never merge HLL/HLLV identity.
- Do not keep duplicated gameplay facts for a retained feature when CRCON REST,
  Log Stream or read-only PostgreSQL already owns the semantic source.
- Do not invent a product choice where current usage and contracts are
  genuinely ambiguous.

## Validation

- Route and CRCON contract tests
- Current match, History, player search, Ranking/Stats and product-feature tests
- Current-match, Historical and Stats/Ranking frontend regressions
- Python compileall and JavaScript syntax
- Full backend discovery with known baseline separated
- `git diff --check` and changed-file scope review

## Outcome

Completed as a documentation-only ownership decision pass.

- Verified that MVP V1, MVP V2, all five player-event aggregate views and
  Elo/MMR are `ACTIVE_API_ONLY`; none has a current HTML or active JavaScript
  consumer. Public routes, route tests, audit probes and documentation remain,
  so no complete feature slice meets `SAFE_DELETE`.
- Traced each route through payload, snapshot/read helper, table and writer.
  Documented the exact MVP formulas, player-event summary types and Elo/MMR
  inputs/weights.
- Recorded `MVP_V1=PRODUCT_DECISION_REQUIRED` and
  `MVP_V2=PRODUCT_DECISION_REQUIRED`, each with technical usage
  `ACTIVE_API_ONLY`, plus per-event consumer classifications.
- Classified duplicated gameplay facts as CRCON-owned. A retained MVP must be
  calculated from CRCON with only an in-memory TTL. A retained event feature
  must use Log Stream/map scoreboard/bounded `log_lines`, not an application
  raw ledger. A retained Elo needs only same-game opaque-player rating state
  and an idempotency cursor.
- Reclassified `player_event_worker` and Elo rebuild as
  `APPLICATION_FEATURE_REQUIRED` rather than rollback writers. Shared legacy
  ingestion/materialization remains `ROLLBACK_HOT` for the base legacy pages;
  manual repair/backfill tools remain `ROLLBACK_COLD`.
- Updated `docs/CRCON_FIRST_LEGACY_DEPENDENCY_LEDGER.md` and added the short,
  actionable `docs/PRODUCT_FEATURE_DECISIONS_REQUIRED.md`. The recommendation
  is to remove all three paused/API-only feature families, but the repository
  cannot prove that external API clients do not rely on their documented
  compatibility routes.
- Removed no code, route, job, table or stored data. Did not deploy, disable a
  writer, access credentials, modify CRCON/PostgreSQL, modify the parity
  observer or wait for a match.

Validation:

- Focused route, CRCON, current-match, History, player-search,
  Ranking/Stats and product-feature backend modules: 208 tests passed.
- `node --test frontend/tests/current-match-snapshot.test.js`: 37 passed.
- `scripts/run-historical-ui-regression-tests.ps1`: passed.
- `scripts/run-stats-validation.ps1`: passed; live backend was unavailable, so
  its route checks used local Python imports as designed.
- `python -m compileall -q backend/app`: passed.
- JavaScript syntax checks for current match, Historical list and match detail:
  passed.
- `git diff --check`: passed (Git emitted only the repository's LF-to-CRLF
  working-copy warning).
- Full backend discovery ran 324 tests and retained known baseline/environment
  failures: missing optional `pytest` during discovery, two RCON
  materialization expectation failures with Windows SQLite cleanup locks, and
  one historical-runner maintenance `partial`/`ok` mismatch. Focused affected
  suites pass and TASK-308 changes no executable code.
- Changed-file scope before task lifecycle move: dependency ledger, decision
  document and this task record only.

## Change Budget

- Prefer documentation-only resolution unless SAFE_DELETE is conclusive.
- If a dead vertical slice exceeds the normal budget, document and split it
  rather than partially deleting the feature.
