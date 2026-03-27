# TASK-117

## Goal

Implement the ingestion and canonical storage flow for the tactical event
families defined in TASK-116, and expand the Elo canonical fact foundation so
tactical events can be materialized into per-player, per-match facts.

## Context

The current repository already persists:

- canonical matches
- canonical player-match facts
- scoreboard-derived per-minute rates
- scoreboard-derived participation fields
- persistent Elo/MMR rating state
- monthly ranking state

That means the repository already has a stable competitive fact foundation for
scoreboard-style historical data. What is still missing is the ingestion path
that converts real tactical events into reusable canonical facts for each player
and match.

This task depends on the event taxonomy, contracts and instrumentation
prerequisites defined in TASK-116. It should not invent tactical values from
unrelated scoreboard totals. Instead, it must wire actual available event
sources into canonical event storage and then expand the canonical player-match
fact layer so later Elo logic can consume real tactical facts.

Execution status: depends_on_previous_tasks

Dependency:

- TASK-116

## Steps

1. Read the event schema/contracts from TASK-116.
2. Implement or wire ingestion for available event sources only.
3. Materialize canonical tactical events with stable player and match lineage.
4. Expand canonical player-match facts to accumulate tactical event counts and
   rates.
5. Keep exact, approximate and unavailable capability boundaries explicit per
   accumulated field.
6. Make the canonical fact layer rebuildable from persisted event data.
7. Document any event family that remains unavailable after ingestion work.
8. For each event family that is actually supported after TASK-116, persist the
   canonical event rows with:
   - canonical event identity
   - source identity if available
   - stable player lineage
   - canonical match lineage
   - server lineage
   - timestamp lineage
   - capability status
   - source reliability
9. Expand canonical player-match facts so they accumulate, when data exists:
   - garrison builds
   - garrison destroys
   - outpost builds
   - outpost destroys
   - revives given
   - revives received
   - supplies placed
   - supply effectiveness proxy or exact usage if available
   - nodes built
   - nodes destroyed
   - repairs performed
   - mines placed
   - mine kills
   - mine destroys
   - commander abilities used
   - strongpoint occupancy seconds
   - role-time seconds by role
   - leave/disconnect/admin action counts
   - death-type counters by category if event feed supports them
10. Define and implement the accumulation rules for every tactical fact field,
    including:
    - whether it is a count, duration, rate, binary marker or proxy
    - whether it is exact, approximate or unavailable
    - whether it is player-owned, team-owned or match-context-owned
11. Ensure the expanded canonical fact layer remains deterministic by requiring
    that a rebuild from persisted tactical events produces the same canonical
    tactical fact totals.
12. Preserve lineage from accumulated tactical facts back to canonical events or
    explicitly mark the fact as proxy-derived if the event family only supports
    a documented proxy.
13. Document which requested tactical fact fields still remain unavailable after
    ingestion, and why.

## Files to Read First

- `AGENTS.md`
- `backend/app/historical_storage.py`
- `backend/app/rcon_historical_read_model.py`
- `backend/app/elo_mmr_storage.py`
- `backend/app/elo_mmr_engine.py`
- output contracts from TASK-116

## Expected Files to Modify

- `backend/app/historical_storage.py`
- `backend/app/rcon_historical_read_model.py`
- `backend/app/elo_mmr_storage.py`
- `backend/app/elo_mmr_engine.py`
- supporting storage/model files only as required

## Constraints

- Only ingest event families actually supported by repository data after
  TASK-116.
- Do not fabricate tactical facts from unrelated scoreboard totals.
- Every accumulated tactical fact must preserve lineage to canonical events or
  explicitly state proxy status.
- Keep the canonical fact layer deterministic for rebuilds.
- Do not widen scope into a full Elo formula rewrite.
- Do not silently drop unsupported event families; keep them explicitly
  unavailable with documented reasons.
- Do not expose a tactical fact field as exact unless it is backed by persisted
  exact event capture.
- Keep canonical event storage and canonical tactical fact aggregation separate
  enough to remain auditable.

Push policy for future execution:

* If this task is implemented and other pending tasks from the same Elo backlog batch still remain open, the worker must not push yet.
* In that case, the worker may commit locally if the repo workflow requires it, but final push must wait until the last pending task of the same backlog batch is completed.
* If this task is the last remaining pending task in the same Elo backlog batch and final validation passes, the worker must commit and push.
* The final implementation response must always state:

  * modified files
  * validations run
  * validation results
  * branch name
  * final commit SHA
  * whether push was executed or intentionally deferred because more pending tasks from the same batch remain
* No task should claim final backlog completion without the required final push, unless a blocking error is documented.

## Validation

- persisted tactical events exist with player and match lineage
- expanded canonical facts contain populated tactical fields where events exist
- unsupported event families remain explicitly unavailable
- no fake event-derived fields appear without backing events
- canonical tactical fact rebuilds are deterministic from persisted event data
- every new tactical fact field has an explicit exact/proxy/unavailable status

## Change Budget

- Keep this task limited to event ingestion plus canonical fact expansion.
- Do not rewrite the full Elo engine in this task.
- Defer scoring-model changes to later tasks that explicitly consume the richer
  tactical fact layer.
