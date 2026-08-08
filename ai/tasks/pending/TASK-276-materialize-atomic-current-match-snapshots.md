---
id: TASK-276
title: Materialize atomic current-match snapshots
status: pending
type: backend
team: Backend Senior
supporting_teams: ["Arquitecto de Base de Datos", "Arquitecto Python"]
roadmap_item: current-match-crcon-parity
priority: high
---

# TASK-276 - Materialize atomic current-match snapshots

## Goal

Calculate the active match once in the background and publish an atomic, versioned snapshot instead of rebuilding player statistics independently for every public request.

## Context

The current `/kills` and `/players` paths query and replay AdminLog rows independently. The browser also polls them at different intervals from the direct RCON match summary. This allows inconsistent maps, scores, kills and player totals to be displayed together and multiplies aggregation cost by the number of visitors.

CRCON calculates a shared live-game snapshot and serves it to every visitor. HLL Vietnam should use the same architectural pattern while retaining its local event feed.

## Steps

1. Define a repository-owned current-match snapshot model containing:
   - lifecycle and `match_instance_id`
   - map/mode/start/status
   - scores and population when available
   - snapshot version/timestamps/freshness
   - source and confidence metadata
   - normalized players and combat totals
   - bounded recent kill feed and latest event cursor
   - ingestion gap/degraded metadata
2. Implement an incremental projector that updates the snapshot after each successfully persisted event batch.
3. Materialize player kills, deaths, teamkills, deaths by teamkill, weapon counts, team, identity and connection state once per snapshot version.
4. Ensure the projector consumes only events correlated to the active match.
5. Publish snapshots atomically so readers never observe half-updated player/feed data.
6. Preserve the latest valid snapshot during a transient source failure while marking it stale/degraded.
7. Clear active players/feed when the lifecycle leaves `live` and publish an ended/between-matches snapshot.
8. Add efficient lookup helpers for the latest snapshot by server and optional incremental kill cursor.
9. Add tests for monotonic counters, duplicate events, match transitions, atomic versions, stale preservation and ended-match clearing.

## Files to Read First

- `AGENTS.md`
- `docs/current-match-crcon-parity-contract.md`
- `backend/app/rcon_admin_log_storage.py`
- `backend/app/rcon_current_match_worker.py`
- `backend/app/postgres_rcon_storage.py`
- `backend/tests/test_current_match_payload.py`

## Expected Files to Modify

- `ai/tasks/in-progress/TASK-276-materialize-atomic-current-match-snapshots.md`
- new focused snapshot/projector module under `backend/app/`
- `backend/app/rcon_current_match_worker.py`
- `backend/app/rcon_admin_log_storage.py`
- `backend/app/postgres_rcon_storage.py`
- new focused snapshot/projector tests under `backend/tests/`

## Constraints

- Do not aggregate the whole match separately on every HTTP request.
- Do not mix events from different `match_instance_id` values.
- Snapshot versions must increase monotonically per server.
- Preserve SQLite/PostgreSQL compatibility and idempotent schema initialization.
- Keep the kill feed bounded; do not duplicate the full historical event store inside every snapshot.
- Do not add CRCON network calls in this task.
- Do not modify frontend layout or polling here.

## Validation

Before completing the task ensure:

- all fields in one snapshot share the same `match_instance_id` and version
- duplicate event batches do not inflate counters
- player totals are monotonic within one live match
- a new match starts with empty counters/feed even if the map repeats
- an ended match does not remain exposed as live
- stale/degraded snapshots preserve the last valid data with explicit metadata
- snapshot reads are bounded and do not replay the full event window
- focused tests and compile checks pass
- `git diff --name-only` matches the projector/storage scope

## Outcome

Document snapshot storage, update triggers, bounded feed retention and performance characteristics.

## Change Budget

- Prefer a new focused projector module over expanding `payloads.py` or storage files excessively.
- Do not expose the final public API contract in this task.
