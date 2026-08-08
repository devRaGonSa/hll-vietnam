---
id: TASK-272
title: Audit and freeze CRCON current-match parity contract
status: pending
type: research
team: Analista
supporting_teams: ["Backend Senior", "Arquitecto Python"]
roadmap_item: current-match-crcon-parity
priority: high
---

# TASK-272 - Audit and freeze CRCON current-match parity contract

## Goal

Define the exact live-match behavior and data contract that HLL Vietnam must reproduce from CRCON before changing persistence, APIs or frontend behavior.

## Context

The current page mixes direct RCON session data with AdminLog-derived kills and player statistics. The public CRCON scoreboard instead maintains a map lifecycle, calculates a shared live-game snapshot and exposes separate session and match statistics.

Implementation must not proceed from assumptions. This task must document the authoritative semantics for match start/end, player identity, kill/teamkill accounting, snapshot freshness and degraded states for both trusted Comunidad Hispana servers.

## Steps

1. Inspect the current-match backend, frontend, worker, storage and existing freshness documentation.
2. Capture sanitized representative responses from the trusted CRCON endpoints for both configured servers:
   - `get_public_info`
   - `get_live_game_stats`
   - `get_live_scoreboard`
3. Document the meaning and lifecycle of all fields used by the current-match page, including map identity, map start, scores, player connection state, kills, deaths, teamkills, weapons and snapshot timestamps.
4. Define the HLL Vietnam target contract with mandatory fields:
   - `match_instance_id`
   - `match_status`
   - `match_started_at`
   - `map_id`
   - `snapshot_version`
   - `snapshot_at`
   - `source_event_at`
   - `source_age_seconds`
   - `confidence`
   - `is_stale`
   - `is_degraded`
5. Define source precedence and reconciliation rules between direct RCON, CRCON live statistics and local AdminLog events.
6. Define acceptance scenarios for start, live play, end, between matches, repeated maps, missed boundaries, worker restart, source outage and recovery.
7. Record explicit non-goals and rollout compatibility requirements for the existing public endpoints.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `docs/current-match-adminlog-freshness.md`
- `backend/app/payloads.py`
- `backend/app/rcon_admin_log_storage.py`
- `frontend/assets/js/partida-actual.js`

## Expected Files to Modify

- `ai/tasks/in-progress/TASK-272-audit-and-freeze-crcon-current-match-parity-contract.md`
- `docs/current-match-crcon-parity-contract.md`
- optional sanitized JSON fixtures under `backend/tests/fixtures/crcon/`

## Constraints

- Do not expose RCON passwords, tokens, private headers or non-public infrastructure details.
- Only use the two trusted Comunidad Hispana scoreboard origins already configured in the repository.
- Do not reintroduce `comunidad-hispana-03`.
- Do not change code, database schema, deployment or frontend behavior in this task.
- Do not copy an unstable CRCON response blindly; normalize it into a repository-owned contract.
- Preserve existing public URLs and current HLL Vietnam product identity.

## Validation

Before completing the task ensure:

- every target field has a documented source and fallback
- all lifecycle states and transitions are defined
- repeated-map and missing-boundary scenarios are covered
- fixture data is sanitized and contains no credentials
- subsequent tasks can implement the contract without unresolved semantic ambiguity
- `git diff --name-only` matches the documentation/fixture scope

## Outcome

Document the accepted parity contract, unresolved CRCON-version risks and any endpoint fields that cannot be guaranteed from all sources.

## Change Budget

- Prefer documentation plus a small fixture set.
- Do not implement production behavior in this task.
