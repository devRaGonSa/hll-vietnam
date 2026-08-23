---
id: TASK-299
title: Cut over current match to the CRCON API snapshot
status: done
type: backend
team: Backend Senior
supporting_teams: [Frontend Senior, Arquitecto Python]
roadmap_item: crcon-migration
priority: critical
---

# TASK-299 - Cut over current match to the CRCON API snapshot

## Goal

Make CRCON 12.0.1 a fully functional selectable source for the public
current-match contract, using only `get_public_info` and
`get_live_game_stats`, while preserving immediate explicit rollback to the
complete legacy implementation.

When CRCON mode is selected, the already implemented frontend snapshot
transport must remain the sole current-match polling owner. Legacy mode keeps
the existing three-stream frontend and backend paths available for rollback.

## Context

TASK-291 introduced `/api/current-match/snapshot` and TASK-292 introduced the
single-stream frontend snapshot transport. TASK-293 through TASK-298 verified
the CRCON 12.0.1 contracts and gathered partial parity evidence. The product
owner has accepted `CURRENT_MATCH_HLL = INSUFFICIENT_EVIDENCE` as non-blocking
for local development and explicitly ended further observation.

The current CRCON runtime binding is API-only, but `CurrentMatchSnapshotService`
still carries the former PostgreSQL/log-derived design and intentionally hides
live K/D/TK values when database combat aggregates are absent. That is the
remaining cutover defect.

Target architecture:

```text
Frontend partida actual
  -> one snapshot polling stream
  -> GET /api/current-match/snapshot
  -> CurrentMatchSnapshotService
  -> CRCON 12.0.1
       -> get_public_info
       -> get_live_game_stats
```

No PostgreSQL is required for current match.

## Exact Implementation Plan

1. Preserve `HLL_CURRENT_MATCH_SOURCE=legacy|crcon|shadow` as the canonical
   backend selector. Do not change the safe default or add automatic fallback.
2. Make the production current-match service runtime API-only: its construction
   and cache fingerprint must not require or construct CRCON PostgreSQL access.
3. Build the deterministic ephemeral current-match identity from server, CRCON
   map start and layer; retain the existing public `match_id` and
   `identity_kind` fields.
4. Treat typed `get_live_game_stats` K/D/TK and scoring fields as canonical
   current-match player values. Carry weapon aggregates and teamkill-death data
   when the verified response supplies them.
5. Keep every `player_id` as an opaque string. Do not infer Steam/EOS or platform
   from its characters.
6. Preserve the snapshot, summary, players and kills JSON shapes. Do not invent
   kill events: the two authorized CRCON calls do not expose an ordered event
   feed, so CRCON snapshot mode returns the existing empty kill window while
   player combat totals remain functional.
7. Retain short process-local caching, request coalescing, stale last-good
   behavior and explicit 503 behavior. Never fall back from CRCON to legacy.
8. Validate that explicit frontend `snapshot` transport performs exactly one
   `/api/current-match/snapshot` call per cycle and starts none of the three
   legacy polling streams; explicit `legacy` remains the rollback transport.
9. Run focused backend/frontend tests, compileall, integration validation when
   relevant, `git diff --check`, and `git diff --name-only`.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/backend-senior.md`
- `ai/orchestrator/frontend-senior.md`
- `backend/app/current_match.py`
- `frontend/assets/js/partida-actual.js`

## Expected Files to Modify

- `backend/app/current_match.py`
- `backend/app/crcon/dto.py`
- `backend/tests/test_crcon_current_match.py`
- `ai/tasks/done/TASK-299-cut-over-current-match-to-crcon-api-snapshot.md`

Frontend files should remain unchanged unless a focused test proves the
existing TASK-292 transport does not satisfy the cutover contract.

## Constraints

- Local implementation and validation only; do not deploy.
- Do not modify CRCON or access its filesystem/database.
- Current match may call only `get_public_info` and `get_live_game_stats`.
- Do not use `get_live_scoreboard` as canonical current-match stats.
- Do not add persistence, a database, a worker, a cache service or a new
  frontend transport.
- Do not migrate historical, ranking, stats or player-profile paths.
- Do not remove legacy workers or storage.
- Do not modify the parity observer or wait for more matches.
- Preserve frontend markup, styling, layout and visible contracts.
- Preserve explicit legacy rollback; no automatic source mixing or fallback.

## Validation

- CRCON snapshot tests prove exactly one call to each authorized CRCON endpoint
  per uncached refresh and zero current-match database calls/construction.
- Player K/D/TK and weapon values come from `get_live_game_stats` without ID
  format inference.
- Snapshot and three compatibility routes preserve their public shapes in CRCON
  mode.
- Legacy mode does not construct the CRCON service.
- CRCON failure does not call legacy helpers.
- Frontend snapshot tests prove one snapshot request and no legacy requests.
- Focused Python tests and `python -m compileall -q app tests` pass.
- Relevant integration validation is run if configured.
- `git diff --check` passes and changed files match the task scope.

## Outcome

Implemented locally on 2026-08-23 without deployment or remote mutation.

- The production `CurrentMatchSnapshotService` runtime is now constructed with
  API-only bindings and no database factory. Its cache fingerprint ignores
  CRCON database configuration and API-only bindings discard any database URL.
- Each uncached production refresh uses exactly `get_public_info` plus
  `get_live_game_stats`. No `get_live_scoreboard` call was introduced.
- `get_public_info` supplies the deterministic ephemeral match identity, map,
  mode, start, score, time and population. `get_live_game_stats` now supplies
  canonical K/D/TK, deaths by teamkill, score categories and weapon aggregates.
- `player_id` passes through as one opaque string. No format or Steam/EOS
  inference was added.
- Snapshot and compatibility response shapes remain intact. Because the two
  authorized CRCON calls do not expose an ordered kill-event stream, CRCON API
  mode returns the existing empty kill window rather than inventing events.
  The player table remains fully populated from live match stats.
- `HLL_CURRENT_MATCH_SOURCE=legacy|crcon|shadow` remains unchanged, with
  `legacy` still the safe backend default and no automatic fallback. The
  existing frontend selector remains `currentMatchTransport=legacy|snapshot`;
  selecting `crcon` plus `snapshot` activates the target path, while selecting
  `legacy` plus `legacy` is the immediate rollback.
- The already committed TASK-292 frontend transport required no source changes:
  explicit snapshot mode owns one non-overlapping `/api/current-match/snapshot`
  poll and starts none of the three legacy streams.
- No historical, ranking, stats, worker, storage, deployment or upstream CRCON
  files were changed by this task. The parity observer was not modified or run.

Validation:

- focused TASK-293–299 backend suite: 126 tests passed;
- frontend snapshot transport suite: 37 tests passed;
- `python -m compileall -q app tests`: passed;
- `git diff --check`: passed with only pre-existing line-ending warnings;
- full backend discovery was attempted: 257 tests ran, with one missing
  `pytest` import plus three unrelated pre-existing historical runner/
  materialization failures, including Windows SQLite cleanup locks;
- `scripts/run-integration-tests.ps1` was run: historical UI validation passed,
  while the pre-existing stats validation failed because the annual ranking
  form is absent;
- the repository was already dirty from TASK-293–298 and older in-progress
  work. TASK-299 changed only its lifecycle document, `backend/app/current_match.py`,
  `backend/app/crcon/dto.py`, and `backend/tests/test_crcon_current_match.py`;
  TASK-298 was moved to done with its evidence status preserved as
  `INSUFFICIENT_EVIDENCE`.

## Change Budget

- Prefer fewer than 5 modified files excluding task lifecycle documentation.
- Prefer changes under 200 lines when feasible.
