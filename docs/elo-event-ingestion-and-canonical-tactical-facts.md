# Elo Event Ingestion And Canonical Tactical Facts

## Scope

This document records what TASK-117 actually materializes from the current repo.

Implemented now:

- canonical event ingestion from `player_event_raw_ledger`
- one supported family:
  - `death_classification_events`
- capability level for that family:
  - `approximate`

Still unavailable:

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

## Implemented Ingestion Path

Source rows:

- `player_kill_summary`
- `player_death_summary`
- `player_weapon_kill_summary`
- `player_weapon_death_summary`
- `player_teamkill_summary`

Materialization flow:

1. read summary rows from `player_event_raw_ledger`
2. join them to canonical match lineage via `server_slug + external_match_id`
3. resolve primary player ownership:
   - killer-owned for kill, weapon-kill and teamkill summaries
   - victim-owned for death and weapon-death summaries
4. write canonical headers to `elo_event_lineage_headers`
5. write typed detail rows to `elo_event_death_classification_details`
6. aggregate those canonical event rows into canonical player-match facts

## Canonical Fact Fields Added

Supported and populated when event coverage exists:

- `death_summary_combat_kills`
- `death_summary_combat_deaths`
- `death_summary_weapon_kills`
- `death_summary_weapon_deaths`
- `death_summary_teamkills`
- `death_classification_event_mode`
- `tactical_event_lineage_status`
- `tactical_event_count`

Explicitly unavailable in the current repo and therefore persisted as zero plus
`not_available` mode:

- garrison counters
- outpost counters
- revive counters
- supply counters
- node counters
- repair counters
- mine counters
- commander ability counters
- strongpoint counters
- role-time counters
- disconnect/admin counters

## Accuracy Boundary

The implemented death-classification family is still only `approximate`.

Reasons:

- source rows are match summaries, not per-death raw events
- `occurred_at` reflects match-level timing, not exact death timing
- redeploy, suicide and menu-exit classification still do not exist
- teamkill summaries preserve useful lineage, but they are still summary-backed
  and not exact raw-event capture

## Rebuild Safety

Canonical tactical facts are rebuilt from persisted canonical event tables, not
directly from HTTP payload composition.

That means:

- rebuild order is deterministic
- event lineage stays auditable
- later tasks can consume the canonical event layer without re-reading source
  payloads
