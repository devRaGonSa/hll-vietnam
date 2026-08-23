---
id: TASK-301
title: Migrate historical match list and detail to CRCON 12.0.1
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Frontend Senior
  - Arquitecto Python
roadmap_item: crcon-cutover
priority: high
---

# TASK-301 - Migrate historical match list and detail to CRCON 12.0.1

## Goal

Make the existing recent-match list and historical match-detail public contracts selectable from CRCON 12.0.1, while keeping the complete legacy path available as an immediate feature-flag rollback.

## Context

The current-match cutover is locally complete. Historical match list and detail are the next bounded read path: the browser must keep using the current endpoints and visual contract while the backend reads only CRCON REST `get_scoreboard_maps` and `get_map_scoreboard`. This task does not migrate aggregates, rankings, player profiles, workers or storage.

## Exact Implementation Plan

1. Add the canonical `HLL_HISTORICAL_MATCH_SOURCE=legacy|crcon` selector, defaulting to `legacy` and rejecting unknown values.
2. Extend only the verified CRCON historical DTO parser fields required by the public detail contract. Keep every match and player identifier opaque.
3. Add a `HistoryService` that resolves enabled `ServerTarget` entries, performs bounded paginated map-list reads, validates `server_number`, fetches one detail only on demand, and uses bounded process-local TTL caches.
4. Add compatibility serializers for the existing recent-list and match-detail JSON shapes, including explicit empty, unavailable, malformed and wrong-target states with no automatic legacy fallback.
5. Delegate only the two existing public payload builders and routes when `crcon` is selected. Leave every legacy branch unchanged and add bounded `page` support to the recent-list route.
6. Preserve the current historical frontend structure, changing only unknown list player-count presentation so an absent CRCON list count is not rendered as a fabricated zero.
7. Add fixture-backed tests for selector behavior, pagination, N targets, cache behavior, opaque IDs, HLL/HLLV metadata, detail mappings, wrong-target rejection and error states.
8. Run focused backend/frontend validation, Python compile checks and scope review. Run real read-only CRCON checks only when locally configured and authorized.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/backend-senior.md`
- `backend/app/crcon/api.py`
- `backend/app/payloads.py`
- `frontend/assets/js/historico-partida.js`

## Expected Files to Modify

- `backend/app/config.py`
- `backend/app/crcon/dto.py`
- `backend/app/history_service.py`
- `backend/app/payloads.py`
- `backend/app/routes.py`
- `frontend/assets/js/historico.js`
- `frontend/assets/js/historico-recent-live.js`
- `frontend/assets/js/historico-partida.js`
- `backend/tests/test_crcon_history_service.py`
- `docs/decisions.md`
- `ai/tasks/in-progress/TASK-301-migrate-historical-match-list-detail-to-crcon.md`

The scope intentionally exceeds the preferred five-file budget because transport, DTO parsing, service isolation, public route compatibility, frontend unknown-state handling, tests and workflow evidence are separate responsibilities. No unrelated subsystem is included.

## Constraints

- Use CRCON REST only: `get_scoreboard_maps` for lists and `get_map_scoreboard` for detail.
- Never use `get_map_history` as the permanent source and never make detail N+1 calls from a list request.
- Do not use PostgreSQL, Redis, direct RCON, AdminLog or new persistence.
- Keep legacy behavior intact behind the selector; do not silently fall back from CRCON.
- Treat `map_id`, `match_id` and `player_id` as opaque application strings. Never infer Steam or EOS identity from their shape.
- Create Steam links only from explicit Steam metadata.
- Support any enabled number of canonical targets and validate every returned `server_number`.
- Preserve the current frontend data and visual contracts. HLLV remains explicitly unverified.
- Do not migrate historical aggregates, rankings, stats, server summary, leaderboard, workers or storage.
- Do not modify CRCON, deploy, or mutate remote services.

## Validation

- Focused `HistoryService`, DTO, route and payload tests pass.
- Existing TASK-293 through TASK-300 focused suites remain green.
- Historical frontend checks pass and unknown player counts are not fabricated.
- `python -m compileall backend/app backend/tests` passes.
- Real read-only validation is attempted only with authorized local CRCON bindings and verified version 12.0.1.
- `git diff --name-only` confirms only expected TASK-301 files plus pre-existing user changes.

## Outcome

Implemented locally with legacy rollback preserved.

- Added `HLL_HISTORICAL_MATCH_SOURCE=legacy|crcon`, default `legacy`.
- Added a bounded `HistoryService` using only CRCON REST `get_scoreboard_maps` and `get_map_scoreboard` with canonical `ServerTarget` resolution, N-target aggregation, pagination and strict `server_number` validation.
- Added a 30-second bounded list cache and a one-hour bounded cache for completed details only. No cache persistence was introduced.
- Added compatibility mappings for list metadata, result/winner/timestamps and complete detail player scores, weapons, vehicles, units and CRCON encounters.
- Kept match and player IDs opaque. Steam links require explicit Steam metadata; synthetic EOS-like IDs do not create Steam links.
- Kept list `player_count` explicitly unknown and updated only the affected frontend renderers to display `No disponible` instead of zero. Missing scores are likewise no longer coerced to `0 - 0`.
- Left server summary, leaderboards, rankings, player profiles, workers and every legacy storage path unchanged. CRCON mode never silently falls back.
- Added TASK-302 as the pending PostgreSQL read-only verification and aggregate-migration phase.

Validation completed:

- TASK-301 focused backend: 21 passed.
- CRCON foundation/current-match/log-stream regression: 70 passed.
- Current-match frontend: 37 passed.
- Historical UI regression: passed.
- JavaScript syntax for all three touched historical scripts: passed.
- `python -m compileall -q backend/app backend/tests`: passed.
- `git diff --check`: passed (line-ending warnings only).
- Full backend discovery: 292 tests run; retained four pre-existing unrelated baseline failures/errors: missing optional `pytest`, two legacy materialization/SQLite failures, and one maintenance-status expectation.
- Real CRCON validation was not eligible: AVG processes were active and no authorized CRCON bindings or canonical targets were configured in this shell. No remote request was made and no real identity evidence was stored.

## Change Budget

The service and tests may exceed 200 lines because the public compatibility contract contains list, match, player, unit and encounter mappings. The cutover remains a single cohesive task and does not add persistence or unrelated historical products.
