---
id: TASK-277
title: Integrate trusted CRCON live reconciliation
status: pending
type: backend
team: Backend Senior
supporting_teams: ["Arquitecto Python", "Analista"]
roadmap_item: current-match-crcon-parity
priority: high
---

# TASK-277 - Integrate trusted CRCON live reconciliation

## Goal

Use the trusted Comunidad Hispana CRCON live endpoints as a server-side reconciliation source for match identity, aggregate player statistics, connection state and current scores.

## Context

CRCON already maintains the map lifecycle and a shared `LIVE_GAME_STATS` snapshot. Local AdminLog remains valuable for the event-by-event kill feed, but relying on local event reconstruction alone can produce partial totals after gaps or missed boundaries.

The integration must be encapsulated behind a repository-owned adapter because CRCON's public API is not a formally versioned external contract.

## Steps

1. Implement an allowlisted CRCON client for the two trusted scoreboard origins already configured in `scoreboard_origins.py`.
2. Support and validate responses from:
   - `get_public_info`
   - `get_live_game_stats`
   - `get_live_scoreboard`
3. Add strict timeouts, bounded retries, schema validation, response-size limits and sanitized errors.
4. Normalize CRCON responses into the parity contract from TASK-272 rather than leaking upstream field names into public payloads.
5. Derive or reconcile `match_instance_id` using CRCON map start and local lifecycle state.
6. Merge source responsibilities explicitly:
   - CRCON: aggregate match/player totals and session connection state
   - local AdminLog: recent ordered combat events
   - direct RCON: bounded fallback for map/score/session fields
7. Detect source disagreement in map/start and prevent data from different matches from being merged.
8. Preserve the last valid normalized CRCON sample during transient failures with stale/degraded metadata.
9. Add tests using sanitized fixtures for healthy, malformed, stale, timeout, mismatched-match and partial-response cases.

## Files to Read First

- `AGENTS.md`
- `docs/current-match-crcon-parity-contract.md`
- `backend/app/scoreboard_origins.py`
- `backend/app/payloads.py`
- `backend/app/data_sources.py`
- current-match snapshot/projector module from TASK-276
- `backend/tests/test_current_match_payload.py`

## Expected Files to Modify

- `ai/tasks/in-progress/TASK-277-integrate-trusted-crcon-live-reconciliation.md`
- new CRCON client/adapter module under `backend/app/`
- current-match snapshot/projector module from TASK-276
- `backend/app/config.py` only if bounded CRCON settings are required
- focused CRCON adapter/reconciliation tests under `backend/tests/`
- sanitized fixtures under `backend/tests/fixtures/crcon/`

## Constraints

- Only contact trusted origins from the static repository allowlist.
- Never accept arbitrary user-provided CRCON URLs.
- Do not expose upstream errors, internal URLs or credentials publicly.
- Do not make the public HTTP request path wait on unbounded CRCON calls.
- Do not merge CRCON aggregate stats with an AdminLog feed from a different `match_instance_id`.
- Preserve a local fallback and explicit degraded behavior.
- Do not change historical scoreboard ingestion or rankings.

## Validation

Before completing the task ensure:

- trusted origins are the only callable hosts
- all upstream payloads are normalized and validated
- CRCON/local match mismatches produce degraded isolation, not mixed data
- timeout/malformed responses preserve the last valid snapshot safely
- aggregate player totals match fixture expectations, including teamkills
- connection state is sourced from the session endpoint without resetting match totals
- focused tests pass without real network dependency
- `git diff --name-only` matches the adapter/projector scope

## Outcome

Document source precedence, timeout/cache behavior, mismatch handling and compatibility risks for future CRCON upgrades.

## Change Budget

- Keep the adapter isolated and testable.
- Do not refactor unrelated historical scoreboard clients.
