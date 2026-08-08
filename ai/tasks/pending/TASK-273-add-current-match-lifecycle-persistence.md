---
id: TASK-273
title: Add persistent current-match lifecycle and match identity
status: pending
type: backend
team: Backend Senior
supporting_teams: ["Arquitecto de Base de Datos", "Arquitecto Python"]
roadmap_item: current-match-crcon-parity
priority: high
---

# TASK-273 - Add persistent current-match lifecycle and match identity

## Goal

Persist one authoritative current-match lifecycle per trusted server and generate a stable `match_instance_id` that all events, snapshots and public responses can share.

## Context

The current implementation determines the active match by querying the latest `match_start` or `match_end` event at read time. When no open start exists it falls back to recent events, which allows ended-match data to appear as current and prevents the frontend from detecting map transitions reliably.

CRCON maintains an explicit map history with start and end boundaries. HLL Vietnam needs an equivalent repository-owned lifecycle model before further live-stat changes.

## Steps

1. Design SQLite and PostgreSQL-compatible storage for current matches.
2. Add a persistent current-match record containing at least:
   - server/target identity
   - `match_instance_id`
   - map id/name and game mode
   - start/end source timestamps
   - lifecycle status
   - scores/winner when known
   - boundary confidence and source
   - created/updated timestamps
3. Generate `match_instance_id` from trusted server identity plus the canonical match start timestamp or an explicit deterministic inferred-start fallback.
4. Implement idempotent lifecycle transitions for:
   - `MATCH START`
   - `MATCH ENDED`
   - inferred map change
   - duplicate boundaries
   - service restart
5. Ensure a new match closes any stale open record for the same server without corrupting historical audit data.
6. Expose storage helpers for retrieving the active, latest and specifically identified match.
7. Add focused SQLite and PostgreSQL-compatible tests for repeated maps, duplicate events, missing end and inferred transitions.

## Files to Read First

- `AGENTS.md`
- `docs/current-match-crcon-parity-contract.md`
- `backend/app/rcon_admin_log_storage.py`
- `backend/app/postgres_rcon_storage.py`
- `backend/app/rcon_admin_log_parser.py`
- `backend/tests/test_rcon_admin_log_storage.py`

## Expected Files to Modify

- `ai/tasks/in-progress/TASK-273-add-current-match-lifecycle-persistence.md`
- `backend/app/rcon_admin_log_storage.py`
- `backend/app/postgres_rcon_storage.py`
- `backend/tests/test_rcon_admin_log_storage.py`
- optional new focused module/test for current-match lifecycle storage

## Constraints

- Do not rely only on map name because the same layer may repeat consecutively.
- Do not delete historical AdminLog events or historical matches.
- Keep SQLite and PostgreSQL behavior equivalent.
- Schema initialization must remain idempotent and safe on existing production data.
- Do not change frontend behavior in this task.
- Do not introduce CRCON network calls in this task.
- Do not reintroduce server #03 or alter RCON credentials/targets.

## Validation

Before completing the task ensure:

- one and only one active lifecycle record can exist per server
- duplicate start/end events are idempotent
- consecutive identical maps receive different `match_instance_id` values
- an ended match is never returned as active
- inferred starts are explicitly marked with reduced confidence
- existing databases upgrade without destructive migration
- focused unit tests pass for SQLite and PostgreSQL compatibility paths
- `git diff --name-only` matches the intended backend/storage scope

## Outcome

Document the schema, transition rules, migration behavior and any ambiguity retained for later CRCON reconciliation.

## Change Budget

- Prefer a focused lifecycle module if storage helpers would otherwise make an existing file too large.
- Do not add snapshot projection or frontend work here.
