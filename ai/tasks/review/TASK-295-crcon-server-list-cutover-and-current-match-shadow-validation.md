---
id: TASK-295
title: CRCON server list cutover and current-match shadow validation
status: review
type: backend
team: Backend Senior
supporting_teams: [Arquitecto Python, Analista]
roadmap_item: crcon-migration
priority: high
---

# TASK-295 - CRCON server list cutover and current-match shadow validation

## Goal

Allow `/api/servers` to use CRCON `get_public_info`, and add an API-only current-match shadow mode that measures legacy/CRCON parity without changing canonical legacy responses.

## Context

TASK-293 introduced the typed CRCON 12.0.1 adapter and TASK-294 verified the relevant HLL API contracts. This task converts that evidence into a reversible server-list cutover and bounded in-memory current-match diagnostics. HLLV remains synthetically covered but operationally unverified.

## Steps

1. Add one explicit legacy/CRCON selector for the server list and preserve legacy rollback.
2. Build frontend-compatible server items from enabled `ServerTarget` instances and typed `PublicInfo` DTOs.
3. Add legacy/crcon/shadow current-match selection; shadow must serve legacy while comparing an API-only CRCON candidate in memory.
4. Add a local final-match verifier using scoreboard list/detail GET APIs and the last live observation.
5. Validate focused, legacy, frontend-contract, compile, and integration checks without deployment or external writes.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/backend-senior.md`
- `backend/app/payloads.py`
- `backend/app/current_match.py`

## Expected Files to Modify

- `backend/app/config.py`
- `backend/app/payloads.py`
- `backend/app/current_match.py`
- `backend/app/server_service.py`
- `backend/app/current_match_shadow.py`
- `backend/tests/test_crcon_server_list.py`
- `backend/tests/test_current_match_shadow.py`
- `docs/CRCON_12_0_1_CONTRACT_VERIFICATION.md`
- `ai/tasks/review/TASK-295-crcon-server-list-cutover-and-current-match-shadow-validation.md`

## Constraints

- Local repository only; no deployment, SSH, CRCON/RCON mutation, or external database writes.
- Do not modify frontend, production Compose, historical/ranking/stats APIs, workers, tables, or backfills.
- CRCON paths use typed GET API clients only and never silently fall back to legacy.
- Player IDs remain opaque strings; diagnostics must not log raw player IDs or names.
- No persistent shadow data, new worker, ledger, or table.
- Preserve the current-match snapshot endpoint and short-TTL/single-flight behavior.

## Validation

- Focused server-list and current-match shadow tests pass.
- Existing CRCON/current-match tests pass.
- Legacy backend and frontend contract tests pass.
- Python compilation passes.
- Relevant integration script is attempted; pre-existing annual-ranking validator failure is documented if still present.
- `git diff --name-only` is reviewed against stacked TASK-293/TASK-294 work and protected user files remain untouched.

## Outcome

- Added `HLL_SERVER_LIST_SOURCE=legacy|crcon`. CRCON mode iterates enabled canonical `ServerTarget` entries, calls only typed `get_public_info`, preserves the frontend envelope, labels the producer as CRCON, and never silently invokes legacy.
- Added two-second process-local server-list TTL/single-flight behavior, per-target unavailable output, and in-memory last-good stale degradation without persistence.
- Extended `HLL_CURRENT_MATCH_SOURCE` to `legacy|crcon|shadow`. Direct and shadow CRCON runtime bindings are API-only (`get_public_info + get_live_game_stats`) and do not construct a CRCON PostgreSQL repository.
- Shadow mode returns the exact legacy public payload while storing a bounded private parity report. It compares match, timing, player-set, identity-adjacent, and seven stat fields by opaque player ID; reports contain only hashed player aliases and aggregate deltas.
- Added an in-memory final-match verifier using `get_scoreboard_maps` then `get_map_scoreboard`, with a configurable temporal tolerance and no worker/table/file history.
- Corrected the evidence: issue `#1186` is not used; `#1170` is treated as a retracted live-stats diagnosis requiring measurement rather than an assumed defect.
- Focused validation: 121 CRCON/server-list/current-match tests passed. Python compile, `git diff --check`, and historical UI regression passed.
- Fixture parity evidence: identical live sources produced zero kill delta; the verified 12.0.1 final-scoreboard fixture intentionally modeled a last poll 10 seconds before closure and observed absolute deltas of 1 kill and 1 combat point. No real-match shadow window was observed in this local-only task and no sensitive identifiers were emitted.
- The configured integration script reached the known pre-existing annual-ranking form validator and failed because that form no longer exists. The unrelated RCON pipeline fallback also still reports two existing materialization failures and the local environment has neither `pytest` nor a running Docker daemon; TASK-295 focused suites remain green.
- Recommendation: `/api/servers` is GO for enabled, verified HLL targets with `HLL_SERVER_TARGETS` configured. Direct CRCON current-match is SHADOW READY, not GO, pending full real-match live/final parity evidence.
- TASK-296 should observe complete HLL matches on both targets in shadow, define sanitized acceptance thresholds (especially kills/player churn), run final-scoreboard verification, decide direct-mode GO/NO-GO, and separately verify HLLV before enabling it.

## Change Budget

This explicitly scoped migration crosses configuration, services, payload adaptation, tests, and evidence documentation. It may exceed the repository preference of five files while remaining isolated from unrelated product areas.
