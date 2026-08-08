---
id: TASK-278
title: Expose unified current-match snapshot API
status: pending
type: backend
team: Backend Senior
supporting_teams: ["Arquitecto Python", "Frontend Senior"]
roadmap_item: current-match-crcon-parity
priority: high
---

# TASK-278 - Expose unified current-match snapshot API

## Goal

Expose one coherent public current-match contract per server and make the existing summary, kills and players endpoints read the same snapshot identity during migration.

## Context

The current endpoints are produced independently. `/api/current-match` reads direct RCON while `/kills` and `/players` read AdminLog storage, and errors are often converted into empty `status: ok` payloads. The frontend cannot distinguish no kills from unavailable data or a changed match.

The snapshot from TASK-276 and CRCON reconciliation from TASK-277 must become the only public read model for the page.

## Steps

1. Add `GET /api/current-match/snapshot?server=...` backed only by the latest materialized snapshot.
2. Return the normalized contract including:
   - `match_instance_id`
   - lifecycle status
   - map/mode/start/scores/population
   - players
   - recent kills and latest cursor
   - snapshot/source timestamps
   - source policy, confidence, stale/degraded/gap metadata
3. Define explicit response states such as `starting`, `live`, `between_matches`, `stale`, `degraded` and `unavailable`.
4. Stop representing storage/source failures as indistinguishable empty-success data.
5. Adapt `/api/current-match`, `/api/current-match/kills` and `/api/current-match/players` to read the same snapshot and return the same `match_instance_id` during a compatibility period.
6. Remove the recent-AdminLog fallback from the meaning of “current match”; an ended or unknown lifecycle must not return old kills as current.
7. Preserve incremental kill access through `since_event_id` or an equivalent cursor without rebuilding the whole match.
8. Add `Cache-Control: no-store` headers for live current-match endpoints.
9. Add contract, route and backward-compatibility tests.

## Files to Read First

- `AGENTS.md`
- `docs/current-match-crcon-parity-contract.md`
- `backend/app/routes.py`
- `backend/app/payloads.py`
- current-match snapshot/projector module from TASK-276
- `backend/tests/test_current_match_payload.py`

## Expected Files to Modify

- `ai/tasks/in-progress/TASK-278-expose-unified-current-match-snapshot-api.md`
- `backend/app/routes.py`
- `backend/app/payloads.py`
- current-match snapshot read module from TASK-276
- `backend/tests/test_current_match_payload.py`
- optional focused route/contract tests
- `docs/frontend-backend-contract.md` or current-match contract documentation

## Constraints

- Public GET requests must not recalculate all player statistics or make unbounded RCON/CRCON calls.
- Compatibility endpoints must share the same snapshot version and match identity.
- Do not return ended-match kills under a current-match scope.
- Do not leak internal exception text or upstream URLs.
- Preserve trusted server validation.
- Do not change frontend code in this task.
- Do not change unrelated historical/ranking APIs.

## Validation

Before completing the task ensure:

- all current-match endpoints expose the same `match_instance_id` and snapshot version
- live, between-matches, stale, degraded and unavailable states are distinguishable
- ended matches return no current kill/player data
- `since_event_id` returns only compatible events from the same match
- current-match responses send no-store caching headers
- endpoint reads are bounded and database-only in the hot path
- focused payload/route tests pass
- `git diff --name-only` matches the API/contract scope

## Outcome

Document the new endpoint, compatibility period, error semantics and planned removal or simplification of legacy endpoints.

## Change Budget

- Prefer a thin payload layer over duplicating projection logic.
- Keep historical APIs out of scope.
