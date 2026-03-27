# TASK-116

## Goal

Define and prepare the event-telemetry foundation required for a full tactical
Elo/MMR model, including canonical storage contracts for match-level and
player-level tactical events that are not currently represented by the existing
scoreboard-style facts.

## Context

The repository already contains:

- canonical match facts
- canonical player-match facts
- persistent MMR materialization
- monthly ranking materialization
- a practical v1-v2 competitive data foundation derived from stored historical
  scoreboard-style stats

That current foundation is useful and honest, but it is still structurally
insufficient for a fuller tactical Elo/MMR model. The repository does not yet
have canonical event-telemetry contracts for the tactical and administrative
signals that would be needed to support more exact competitive modeling.

The missing structured telemetry includes, at minimum:

- garrison build / destroy interactions
- outpost build / destroy interactions
- revive events
- supply placement / consumption events
- node build / destroy / active-time events
- repair / maintenance events
- mine placement / mine kill / mine destroy events
- commander ability usage events
- strongpoint presence / occupancy / contest time
- truthful role-time tracking
- leave / disconnect / kick / ban / admin action lineage
- explicit death-type classification when available

This task is not about tactical scoring yet. It is about designing the canonical
event schema, lineage rules, capability boundaries and instrumentation
prerequisites required before later Elo tasks can consume these signals.

Execution status: blocked_by_missing_telemetry

## Steps

1. Inspect current historical, RCON and Elo/MMR storage/model boundaries.
2. Define a canonical event taxonomy for tactical Elo inputs.
3. Define event families and minimum required payload fields for each family.
4. Define canonical storage tables or equivalent storage contracts for those
   events.
5. Define identity, match lineage and timestamp requirements for every event.
6. Define exact / approximate / not_available capability rules for each event
   family.
7. Document which event families are currently unavailable in the repository.
8. Specify the minimum instrumentation work required before later Elo tasks can
   consume these events.
9. Define the canonical contract for each of these event families:
   - `garrison_events`
   - `outpost_events`
   - `revive_events`
   - `supply_events`
   - `node_events`
   - `repair_events`
   - `mine_events`
   - `commander_ability_events`
   - `strongpoint_presence_events`
   - `role_assignment_events`
   - `disconnect_leave_admin_events`
   - `death_classification_events`
10. For every event family, define the minimum canonical fields or equivalent
    persisted contract entries required for future implementation:
    - canonical event id
    - external/source event id if available
    - stable player key
    - optional actor player key
    - optional target player key
    - canonical match key
    - server slug
    - event timestamp
    - event type
    - event subtype
    - team side
    - role at event time if known
    - source kind
    - source reliability
    - exact/proxy/unavailable capability flag
    - raw payload storage strategy or normalized equivalent
    - deduplication strategy
    - replay/rebuild safety expectations
11. Define whether each family should use:
    - one shared canonical events table plus typed child tables
    - one family-specific canonical table per event family
    - or a hybrid approach with a common lineage header and family-specific
      detail tables
12. Define timestamp expectations for every event family, including:
    - event-time exact timestamp when captured
    - match-relative timestamp if only relative timing exists
    - fallback behavior when only match-level windows exist
    - explicit rules for when event timing remains `not_available`
13. Define actor/target semantics for ambiguous events, including:
    - self-authored actions such as building or placing
    - team-authored or commander-authored actions
    - multi-player events such as revive actor vs revive recipient
    - area-state events such as strongpoint occupancy where a single target
      player may not exist
14. Define canonical identity requirements so later workers know exactly how to
    relate events to:
    - stable player identity
    - server scope
    - canonical match identity
    - optional role-at-time identity
15. Document the minimum instrumentation prerequisites for each event family,
    including which families are:
    - implementable now from repository data
    - implementable only as proxy
    - blocked until new capture/instrumentation exists

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `backend/app/historical_storage.py`
- `backend/app/rcon_historical_read_model.py`
- `backend/app/elo_mmr_storage.py`
- `docs/elo-v3-competitive-gap-and-telemetry-boundary.md`

## Expected Files to Modify

- `backend/app/historical_storage.py`
- `backend/app/rcon_historical_read_model.py`
- `backend/app/elo_mmr_storage.py`
- new storage/schema helpers if needed
- docs covering telemetry/event contracts

## Constraints

- Do not implement tactical scoring in this task.
- Do not guess unavailable events from scoreboard-only fields.
- Do not collapse tactical events into opaque JSON-only storage without
  canonical lineage.
- Keep the event model rebuild-safe and auditable.
- Mark unsupported event families explicitly instead of simulating them.
- The task must stay focused on schema/contracts/instrumentation prerequisites,
  not on rating-formula changes.
- Every event family must have an explicit capability classification:
  - `exact`
  - `approximate`
  - `not_available`
- Every event family must define canonical lineage requirements even when the
  implementation status is currently blocked.
- Event contracts must make it possible for a later worker to rebuild canonical
  tactical facts from persisted event data without relying on API-only
  composition.

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

- schema/contract review exists for every listed event family
- every event family has an explicit capability status
- identity and match lineage are explicitly defined for every event family
- timestamp expectations are defined for every event family
- deduplication and rebuild-safety expectations are defined for every event
  family
- blocked or unavailable telemetry is documented explicitly, not hidden
- instrumentation prerequisites are listed for every family that is currently
  blocked

## Change Budget

- Keep this task focused on schema/contracts/instrumentation prerequisites only.
- Do not widen scope into Elo engine scoring, monthly ranking or payload
  redesign.
- If the schema surface becomes too large for one implementation pass, split the
  implementation later, but keep this task itself responsible for the complete
  contract definition.
