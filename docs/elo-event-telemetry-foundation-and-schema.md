# Elo Event Telemetry Foundation And Schema

## Scope

This document defines the canonical event-telemetry contract required before the
telemetry-rich Elo/MMR backlog can consume tactical and administrative signals.

Contract version:

- `elo-event-telemetry-v1`

Storage strategy:

- `hybrid-header-plus-family-detail`

Current boundary:

- all tactical/admin families below remain `not_available` in the base
  `public-scoreboard` and `rcon-historical-competitive-read-model` sources
- current scoreboard facts and V2 aggregated player-event summaries remain
  useful, but they do not justify canonical rows for these families
- after TASK-117, the repo additionally supports approximate
  `death_classification_events` from `public-scoreboard-match-summary` through
  `player_event_raw_ledger`

## Shared Canonical Contract

Every event family must persist or explicitly reserve these common fields:

- `canonical_event_id`
- `source_event_id`
- `stable_player_key`
- `actor_player_key`
- `target_player_key`
- `canonical_match_key`
- `server_slug`
- `occurred_at`
- `match_second`
- `event_time_status`
- `event_window_start_second`
- `event_window_end_second`
- `event_type`
- `event_subtype`
- `team_side`
- `role_at_event_time`
- `source_kind`
- `source_reliability`
- `capability_status`
- `source_payload_ref`
- `raw_payload_strategy`
- `dedupe_key`
- `dedupe_strategy`
- `replay_safe`

Rules:

- `canonical_match_key` and `server_slug` are required for every family
- `stable_player_key` is required when one primary player owner exists
- timing may be `exact`, `relative`, `window` or `not_available`
- workers must never invent timestamps from scoreboard-only totals
- primary dedupe is `canonical_event_id`
- secondary dedupe uses a deterministic key derived from family, source, match,
  actor/target lineage and timing
- later tactical facts must be rebuildable from persisted event tables alone

## Actor And Target Semantics

- self-authored actions use the acting player as `actor_player_key`
- revive rows use medic as actor and recipient as target
- death rows use victim as target and killer as actor when known
- area-state events such as strongpoint presence normally keep target player
  null
- leave/admin rows use the affected player as the owner row; admin actor is
  optional and only stored when emitted by source

## Storage Tables

Shared header and registry:

- `elo_event_lineage_headers`
- `elo_event_capability_registry`

Family detail tables:

- `elo_event_garrison_details`
- `elo_event_outpost_details`
- `elo_event_revive_details`
- `elo_event_supply_details`
- `elo_event_node_details`
- `elo_event_repair_details`
- `elo_event_mine_details`
- `elo_event_commander_ability_details`
- `elo_event_strongpoint_presence_details`
- `elo_event_role_assignment_details`
- `elo_event_disconnect_leave_admin_details`
- `elo_event_death_classification_details`

## Capability Matrix

| Event family | `public-scoreboard` | `rcon-historical-competitive-read-model` | Why |
| --- | --- | --- | --- |
| `garrison_events` | `not_available` | `not_available` | no raw structure event feed |
| `outpost_events` | `not_available` | `not_available` | no raw structure event feed |
| `revive_events` | `not_available` | `not_available` | no actor-recipient revive feed |
| `supply_events` | `not_available` | `not_available` | no supply interaction feed |
| `node_events` | `not_available` | `not_available` | no node lifecycle feed |
| `repair_events` | `not_available` | `not_available` | no repair or maintenance feed |
| `mine_events` | `not_available` | `not_available` | no mine lifecycle or kill feed |
| `commander_ability_events` | `not_available` | `not_available` | no commander ability feed |
| `strongpoint_presence_events` | `not_available` | `not_available` | no occupancy or contest timing |
| `role_assignment_events` | `not_available` | `not_available` | current role logic is proxy-only |
| `disconnect_leave_admin_events` | `not_available` | `not_available` | no explicit leave/admin lineage |
| `death_classification_events` | `not_available` | `not_available` | no per-death reason feed |

## Family Contracts

### `garrison_events`

Detail fields:

- `action_kind`
- `structure_team_side`
- `sector_name`
- `grid_reference`
- `placement_rule`
- `red_zone_flag`
- `structure_health_state`
- `linked_spawn_type`

Instrumentation prerequisite:

- raw garrison placement/destruction feed with stable structure identity

### `outpost_events`

Detail fields:

- `action_kind`
- `structure_team_side`
- `squad_ref`
- `sector_name`
- `grid_reference`
- `placement_rule`
- `structure_health_state`

Instrumentation prerequisite:

- outpost placement/destruction feed with squad or owner lineage

### `revive_events`

Detail fields:

- `revive_method`
- `target_role`
- `target_team_side`
- `distance_meters`
- `success_state`
- `downed_cause_category`

Instrumentation prerequisite:

- actor-recipient revive feed

### `supply_events`

Detail fields:

- `action_kind`
- `supply_channel`
- `supply_amount`
- `supply_amount_used`
- `target_object_type`
- `sector_name`
- `grid_reference`
- `effectiveness_mode`

Instrumentation prerequisite:

- supply placement/consumption source with amount semantics

### `node_events`

Detail fields:

- `action_kind`
- `node_type`
- `node_tier`
- `active_seconds`
- `resource_generated_amount`
- `sector_name`
- `grid_reference`
- `structure_health_state`

Instrumentation prerequisite:

- node lifecycle feed or authoritative node-state snapshots

### `repair_events`

Detail fields:

- `repair_target_type`
- `repair_target_name`
- `repair_amount`
- `repair_seconds`
- `target_team_side`
- `repair_result`

Instrumentation prerequisite:

- repair feed with target classification

### `mine_events`

Detail fields:

- `action_kind`
- `mine_type`
- `placement_grid_reference`
- `trigger_result`
- `victim_team_side`
- `destroyed_by_category`
- `multi_kill_count`

Instrumentation prerequisite:

- mine placement, trigger and destroy feed with lifecycle linkage

### `commander_ability_events`

Detail fields:

- `ability_type`
- `ability_variant`
- `target_team_side`
- `target_sector_name`
- `target_grid_reference`
- `cooldown_seconds`
- `impact_window_seconds`

Instrumentation prerequisite:

- commander ability feed plus target-area metadata

### `strongpoint_presence_events`

Detail fields:

- `presence_kind`
- `strongpoint_name`
- `strongpoint_phase`
- `occupancy_seconds`
- `contest_seconds`
- `presence_team_side`
- `occupancy_source_granularity`

Instrumentation prerequisite:

- authoritative occupancy timeline or spatial presence capture

### `role_assignment_events`

Detail fields:

- `role_name`
- `role_class`
- `assignment_kind`
- `assigned_by_player_key`
- `role_start_second`
- `role_end_second`
- `role_duration_seconds`
- `squad_ref`

Instrumentation prerequisite:

- role-change or spawn role feed with per-match player lineage

### `disconnect_leave_admin_events`

Detail fields:

- `action_kind`
- `action_reason_code`
- `action_reason_text`
- `admin_action_type`
- `removal_scope`
- `returned_before_match_end`
- `return_delay_seconds`

Instrumentation prerequisite:

- leave, disconnect, kick or ban feed plus rejoin correlation

### `death_classification_events`

Detail fields:

- `death_class`
- `death_subclass`
- `weapon_name`
- `weapon_category`
- `damage_source_kind`
- `is_friendly_fire`
- `is_redeploy`
- `is_self_inflicted`
- `is_menu_exit`

Instrumentation prerequisite:

- raw death feed with reason classification and victim lineage

Current implemented fallback:

- approximate summary-backed rows from:
  - `player_kill_summary`
  - `player_death_summary`
  - `player_weapon_kill_summary`
  - `player_weapon_death_summary`
  - `player_teamkill_summary`
- these rows preserve match and player lineage but do not claim exact per-death
  timing or exact redeploy/suicide/menu classification

## Implementable-Now Boundary

Implementable now:

- contract module
- header/detail storage schema
- capability registry

Blocked until new instrumentation exists:

- ingestion of every family above
- exact or proxy canonical event rows for those families
