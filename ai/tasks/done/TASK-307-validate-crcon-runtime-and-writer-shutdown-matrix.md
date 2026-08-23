---
id: TASK-307
title: Validate CRCON-first runtime reads and writer-shutdown matrix
status: done
type: research
team: Analista
supporting_teams:
  - Backend Senior
  - Arquitecto de Base de Datos
  - Arquitecto Python
roadmap_item: CRCON-first migration
priority: high
---

# TASK-307 - Validate CRCON-first runtime reads and writer-shutdown matrix

## Goal

Perform a non-mutating local runtime-readiness validation of every implemented
CRCON-first public read path and update the evidence and legacy writer-shutdown
matrices without disabling, deploying, or modifying any runtime component.

## Context

TASK-293 through TASK-306 implemented the selectable CRCON 12.0.1 readers and
isolated the legacy rollback paths. Runtime evidence must now be separated from
source-contract and synthetic evidence so later shutdown decisions are based on
the actual authorized configuration available locally.

## Steps

1. Verify the prescribed clean branch and HEAD and preserve unexpected changes.
2. Detect canonical target, API-token, Log Stream and SELECT-only database
   configuration by name/presence only; never discover or print credentials.
3. Exercise bounded CRCON REST, authenticated player-search, Log Stream and
   PostgreSQL reads only where explicitly authorized configuration exists.
4. Validate application DTO/service and local HTTP contracts without legacy
   fallback when a CRCON selector is under test.
5. Record separate HLL/HLLV runtime status, query safety/plan evidence, load
   safeguards and product/rollback writer dependencies.
6. Run the existing focused and regression validation without inventing tests
   when product code does not change.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `docs/CRCON_12_0_1_CONTRACT_VERIFICATION.md`
- `docs/CRCON_FIRST_LEGACY_DEPENDENCY_LEDGER.md`
- `backend/app/services/historical_aggregates.py`
- `backend/app/config.py`

## Expected Files to Modify

- `docs/CRCON_12_0_1_CONTRACT_VERIFICATION.md`
- `docs/CRCON_FIRST_LEGACY_DEPENDENCY_LEDGER.md`
- `ai/tasks/in-progress/TASK-307-validate-crcon-runtime-and-writer-shutdown-matrix.md`

## Constraints

- Read-only evidence only: no PostgreSQL/Redis writes, direct RCON, AdminLog,
  deployment, worker/scheduler changes, remote Log Stream enablement, stress
  testing, new persistence, CRCON changes, or full-match parity waiting.
- Use only already-authorized canonical configuration; do not search deployment
  files, reuse write-capable credentials intentionally, or expose identities.
- Treat `player_id` as opaque and retain HLLV as unverified without a real
  authorized HLLV target.
- Keep explicit CRCON failures visible; never permit silent legacy fallback.
- Leave MVP, player-events and Elo/MMR as `PRODUCT_DECISION_REQUIRED`.

## Validation

- Focused CRCON, route, current-match, history, player-search and aggregate tests
- Frontend regression scripts
- Python `compileall`
- JavaScript syntax checks
- `git diff --check`
- `git diff --name-only` scope review

## Outcome

Completed locally on 2026-08-23 without deployment, writer shutdown, remote
mutation, database/Redis writes, direct RCON, GetAdminLog or CRCON changes.

- The prescribed branch, HEAD and clean base were verified before work.
- Canonical configuration was inspected by variable presence only. The current
  process had no ServerTargets, aligned CRCON bindings, Log Stream tokens or
  SELECT-only CRCON DSN; no alternate credential source was searched.
- Existing real HLL evidence retains server-list runtime `GO` and
  current-match runtime transport evidence while preserving
  `CURRENT_MATCH_HLL=INSUFFICIENT_EVIDENCE`. HLLV remains `UNVERIFIED`.
- A loopback backend smoke forced all four selectors to `crcon`. Missing
  configuration produced explicit empty/degraded/error/`UNVERIFIED_SCHEMA`
  results and never selected legacy fallback.
- Because authorization was absent, no new external REST, authenticated player
  search, Log Stream, PostgreSQL schema/game/role query or `EXPLAIN` was run.
- `docs/CRCON_12_0_1_CONTRACT_VERIFICATION.md` now separates source, local
  contract, prior runtime and deployed runtime evidence and contains the full
  HLL/HLLV capability and final status matrices.
- `docs/CRCON_FIRST_LEGACY_DEPENDENCY_LEDGER.md` now contains the required
  per-writer shutdown matrix and distinguishes `ROLLBACK_HOT` periodic writers
  from `ROLLBACK_COLD` manual backfills. Shutdown readiness is `NOT_READY`.
- MVP, player-events and Elo/MMR remain `PRODUCT_DECISION_REQUIRED`; no product
  disposition was inferred.

Validation:

- focused CRCON/service/route/current-match/history/player-search/aggregate
  stack: 179 tests passed;
- current-match snapshot frontend: 37 tests passed;
- Historical UI and Stats regression scripts: passed;
- JavaScript syntax for every frontend runtime file: passed;
- `python -m compileall -q backend/app backend/tests`: passed;
- broad backend discovery: 324 tests with the unchanged baseline of one missing
  optional `pytest` import, two legacy materialization/Windows SQLite errors
  and one historical-runner `ok`/`partial` expectation failure;
- `git diff --check`: passed with only repository line-ending warnings.

No product-code change or new test was justified. The recommended next task is
a repeat of the bounded runtime pass with explicit canonical HLL targets, an
aligned player-history Bearer credential, an enabled Log Stream credential and
an authorized SELECT-only CRCON DSN. Product/storage decisions should follow
only after those runtime gates are complete.

## Change Budget

- Product code should remain unchanged unless a real bounded runtime defect is
  discovered.
- Documentation may exceed the normal line budget where required to provide the
  explicit capability and writer matrices.
