---
id: TASK-275
title: Add ingestion watermarks, heartbeats and event-to-match correlation
status: pending
type: backend
team: Backend Senior
supporting_teams: ["Arquitecto de Base de Datos", "Arquitecto Python"]
roadmap_item: current-match-crcon-parity
priority: high
---

# TASK-275 - Add ingestion watermarks, heartbeats and event-to-match correlation

## Goal

Replace the fixed fifteen-minute recovery assumption with persistent per-server ingestion progress, explicit gap detection and durable assignment of every live event to a `match_instance_id`.

## Context

The live worker currently polls a fixed lookback window. If it is stopped longer than that window, early match events and boundaries are permanently missed. Public reads then fall back to recent rows and can mix matches.

CRCON continuously tracks logs and calculates match statistics from the known map start. HLL Vietnam needs persistent ingestion state and event correlation so worker restarts do not silently produce incomplete totals.

## Steps

1. Add per-target ingestion state containing at least:
   - last poll attempt/success timestamps
   - last source `server_time`
   - last persisted event id
   - current lookback/recovery mode
   - detected gap interval
   - last error and consecutive failure count
2. Change worker polling to use the persisted watermark with a small overlap for deduplication instead of always relying on a fixed recent window.
3. On startup, recover from the last successful watermark within a configurable safety limit.
4. Detect and persist unrecoverable gaps rather than presenting partial totals as exact.
5. Correlate inserted AdminLog events to the active `match_instance_id` from TASK-273.
6. Handle boundary events transactionally so `MATCH START` creates/opens the target match before subsequent events are assigned.
7. Persist a heartbeat even when no AdminLog entries are returned.
8. Ensure one slow/failing target does not prevent progress metadata from being recorded for other targets.
9. Add tests for normal overlap, restart after short outage, outage beyond recovery limit, duplicate delivery, missing boundary and per-target failure isolation.

## Files to Read First

- `AGENTS.md`
- `docs/current-match-crcon-parity-contract.md`
- `backend/app/rcon_current_match_worker.py`
- `backend/app/rcon_admin_log_ingestion.py`
- `backend/app/rcon_admin_log_storage.py`
- `backend/app/postgres_rcon_storage.py`
- `backend/tests/test_rcon_current_match_worker.py`

## Expected Files to Modify

- `ai/tasks/in-progress/TASK-275-add-current-match-ingestion-watermarks-and-event-correlation.md`
- `backend/app/rcon_current_match_worker.py`
- `backend/app/rcon_admin_log_ingestion.py`
- `backend/app/rcon_admin_log_storage.py`
- `backend/app/postgres_rcon_storage.py`
- `backend/tests/test_rcon_current_match_worker.py`
- `backend/tests/test_rcon_admin_log_storage.py`

## Constraints

- Preserve idempotent event insertion and overlap-safe deduplication.
- Do not claim complete coverage when an unrecoverable gap exists.
- Keep SQLite and PostgreSQL behavior aligned.
- Do not perform heavy historical materialization in the live worker.
- Do not block all servers on one slow target.
- Do not change public endpoint or frontend contracts in this task.
- Do not alter trusted target hosts, ports or credentials.

## Validation

Before completing the task ensure:

- a restart within the recovery window restores all missed events
- a longer outage is reported as a durable gap with partial confidence
- duplicate overlap events remain idempotent
- each correlated live event has the correct `match_instance_id` where determinable
- heartbeat freshness advances even during quiet matches
- per-target errors are isolated
- worker/storage focused tests pass
- `python -m compileall backend/app` passes
- `git diff --name-only` matches the intended worker/storage scope

## Outcome

Document watermark semantics, recovery limits, gap states and operational queries for checking ingestion health.

## Change Budget

- Prefer one focused ingestion-state abstraction shared by SQLite and PostgreSQL.
- Do not add CRCON reconciliation or frontend changes here.
