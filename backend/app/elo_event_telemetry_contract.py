"""Canonical telemetry contracts for tactical Elo/MMR event families."""

from __future__ import annotations

from copy import deepcopy
from typing import Final

ELO_EVENT_TELEMETRY_CONTRACT_VERSION: Final[str] = "elo-event-telemetry-v1"
ELO_EVENT_STORAGE_STRATEGY: Final[str] = "hybrid-header-plus-family-detail"

COMMON_EVENT_FIELDS: Final[tuple[str, ...]] = (
    "canonical_event_id",
    "source_event_id",
    "stable_player_key",
    "actor_player_key",
    "target_player_key",
    "canonical_match_key",
    "server_slug",
    "occurred_at",
    "match_second",
    "event_time_status",
    "event_window_start_second",
    "event_window_end_second",
    "event_type",
    "event_subtype",
    "team_side",
    "role_at_event_time",
    "source_kind",
    "source_reliability",
    "capability_status",
    "source_payload_ref",
    "raw_payload_strategy",
    "dedupe_key",
    "dedupe_strategy",
    "replay_safe",
)

COMMON_EVENT_RULES: Final[dict[str, object]] = {
    "identity": {
        "canonical_match_key": "Required for every family.",
        "server_slug": "Required for every family.",
        "stable_player_key": "Required when one primary player owner exists.",
        "actor_player_key": "Used when the acting player differs from the owner row.",
        "target_player_key": "Used for revive recipients, death victims or admin targets.",
    },
    "timing": {
        "exact": "Persist `occurred_at`.",
        "relative": "Persist `match_second` when only match-relative timing exists.",
        "window": "Persist event window bounds when only a timing window exists.",
        "not_available": "Never invent timing when the source lacks it.",
    },
    "deduplication": {
        "primary": "Unique on `canonical_event_id`.",
        "secondary": "Deterministic `dedupe_key` from family, source, match lineage, actor/target lineage and timing tuple.",
    },
    "replay_safety": {
        "expectation": "Canonical tactical facts must be rebuildable from persisted event tables alone.",
    },
}


def _contract(
    *,
    event_type: str,
    current_capability: str,
    actor_semantics: str,
    target_semantics: str,
    detail_fields: tuple[str, ...],
    instrumentation_prerequisites: tuple[str, ...],
    notes: str,
) -> dict[str, object]:
    return {
        "event_type": event_type,
        "contract_version": ELO_EVENT_TELEMETRY_CONTRACT_VERSION,
        "storage_strategy": ELO_EVENT_STORAGE_STRATEGY,
        "current_repository_capability": current_capability,
        "actor_semantics": actor_semantics,
        "target_semantics": target_semantics,
        "minimum_common_fields": list(COMMON_EVENT_FIELDS),
        "detail_fields": list(detail_fields),
        "notes": notes,
        "instrumentation_prerequisites": list(instrumentation_prerequisites),
    }


EVENT_FAMILY_CONTRACTS: Final[dict[str, dict[str, object]]] = {
    "garrison_events": _contract(
        event_type="garrison",
        current_capability="not_available",
        actor_semantics="Builder or destroyer when attributable.",
        target_semantics="Destroyed structure owner or defending team when known.",
        detail_fields=("action_kind", "structure_team_side", "sector_name", "grid_reference", "placement_rule", "red_zone_flag", "structure_health_state", "linked_spawn_type"),
        instrumentation_prerequisites=("Raw placement/destruction feed.", "Stable per-match structure identity.", "Actor attribution at event time."),
        notes="No current repository source emits garrison event rows.",
    ),
    "outpost_events": _contract(
        event_type="outpost",
        current_capability="not_available",
        actor_semantics="Builder or destroyer when attributable.",
        target_semantics="Destroyed outpost owner or affected squad when known.",
        detail_fields=("action_kind", "structure_team_side", "squad_ref", "sector_name", "grid_reference", "placement_rule", "structure_health_state"),
        instrumentation_prerequisites=("OP placement/destruction feed.", "Squad or owner lineage.", "Stable per-match structure identity."),
        notes="Current sources do not expose outpost telemetry.",
    ),
    "revive_events": _contract(
        event_type="revive",
        current_capability="not_available",
        actor_semantics="Reviving player.",
        target_semantics="Revive recipient.",
        detail_fields=("revive_method", "target_role", "target_team_side", "distance_meters", "success_state", "downed_cause_category"),
        instrumentation_prerequisites=("Actor-recipient revive feed.", "Event timing.", "Reliable success marker."),
        notes="No current repository source provides revive actor-recipient events.",
    ),
    "supply_events": _contract(
        event_type="supply",
        current_capability="not_available",
        actor_semantics="Player or commander who spawned, dropped or consumed supplies.",
        target_semantics="Affected player or structure when a single target exists.",
        detail_fields=("action_kind", "supply_channel", "supply_amount", "supply_amount_used", "target_object_type", "sector_name", "grid_reference", "effectiveness_mode"),
        instrumentation_prerequisites=("Supply placement/consumption feed.", "Amount semantics.", "Lineage to constructed object or squad context."),
        notes="Supply interactions are not exposed by current persisted data.",
    ),
    "node_events": _contract(
        event_type="node",
        current_capability="not_available",
        actor_semantics="Builder, destroyer or maintaining player.",
        target_semantics="Destroyed node owner when known.",
        detail_fields=("action_kind", "node_type", "node_tier", "active_seconds", "resource_generated_amount", "sector_name", "grid_reference", "structure_health_state"),
        instrumentation_prerequisites=("Node build/destroy events or authoritative node-state snapshots.", "Node type emitted by source.", "Lifecycle linkage."),
        notes="Node lifecycle telemetry is absent from current repository sources.",
    ),
    "repair_events": _contract(
        event_type="repair",
        current_capability="not_available",
        actor_semantics="Repairing player.",
        target_semantics="Vehicle, structure or asset owner only when attributable.",
        detail_fields=("repair_target_type", "repair_target_name", "repair_amount", "repair_seconds", "target_team_side", "repair_result"),
        instrumentation_prerequisites=("Repair action feed.", "Repair target classification.", "Duration or amount semantics."),
        notes="Current repo has no repair or maintenance event source.",
    ),
    "mine_events": _contract(
        event_type="mine",
        current_capability="not_available",
        actor_semantics="Mine placer, destroyer or detonation owner depending on subtype.",
        target_semantics="Killed victim or destroyed mine owner when known.",
        detail_fields=("action_kind", "mine_type", "placement_grid_reference", "trigger_result", "victim_team_side", "destroyed_by_category", "multi_kill_count"),
        instrumentation_prerequisites=("Mine placement and detonation feed.", "Mine-type classification.", "Linkage between placement and later trigger or destroy event."),
        notes="Mine placement and mine-cause telemetry is not available in current persisted sources.",
    ),
    "commander_ability_events": _contract(
        event_type="commander_ability",
        current_capability="not_available",
        actor_semantics="Commander or system actor invoking the ability.",
        target_semantics="Affected team or target asset area rather than a single player.",
        detail_fields=("ability_type", "ability_variant", "target_team_side", "target_sector_name", "target_grid_reference", "cooldown_seconds", "impact_window_seconds"),
        instrumentation_prerequisites=("Ability-use event source.", "Ability classification.", "Area target or team target metadata."),
        notes="No current source exposes commander ability invocation history.",
    ),
    "strongpoint_presence_events": _contract(
        event_type="strongpoint_presence",
        current_capability="not_available",
        actor_semantics="Player occupying the point when tracked per player; null for team-state rows.",
        target_semantics="Area-state event; target player is normally null.",
        detail_fields=("presence_kind", "strongpoint_name", "strongpoint_phase", "occupancy_seconds", "contest_seconds", "presence_team_side", "occupancy_source_granularity"),
        instrumentation_prerequisites=("Spatial capture or authoritative occupancy logs.", "Point identity per match.", "Per-player or per-team occupancy windows."),
        notes="No current repository source persists objective occupancy or contest timing.",
    ),
    "role_assignment_events": _contract(
        event_type="role_assignment",
        current_capability="not_available",
        actor_semantics="Assigned player; optional assigning actor when exposed.",
        target_semantics="Usually null because the owner row is the assigned player.",
        detail_fields=("role_name", "role_class", "assignment_kind", "assigned_by_player_key", "role_start_second", "role_end_second", "role_duration_seconds", "squad_ref"),
        instrumentation_prerequisites=("Role-change or spawn role feed.", "Stable per-match player identity at event time.", "Start/end windows to compute truthful role-time."),
        notes="Current role logic is scoreboard-derived proxy only.",
    ),
    "disconnect_leave_admin_events": _contract(
        event_type="disconnect_leave_admin",
        current_capability="not_available",
        actor_semantics="Affected player is the owner row; optional admin actor when emitted.",
        target_semantics="Usually null unless the source distinguishes actor and affected player.",
        detail_fields=("action_kind", "action_reason_code", "action_reason_text", "admin_action_type", "removal_scope", "returned_before_match_end", "return_delay_seconds"),
        instrumentation_prerequisites=("Disconnect/leave/kick/ban feed.", "Admin reason or code when moderation is involved.", "Session rejoin correlation inside the same match."),
        notes="Current repo proxies leave risk via participation only.",
    ),
    "death_classification_events": _contract(
        event_type="death_classification",
        current_capability="approximate",
        actor_semantics="Killer when known; null for self-authored or unclassified deaths.",
        target_semantics="Victim player.",
        detail_fields=("death_class", "death_subclass", "weapon_name", "weapon_category", "damage_source_kind", "is_friendly_fire", "is_redeploy", "is_self_inflicted", "is_menu_exit"),
        instrumentation_prerequisites=("Per-death event feed or raw log with death reason.", "Victim lineage and optional killer lineage.", "Exact classification semantics for redeploy, suicide, menu exit and combat death."),
        notes="Current repo can materialize approximate summary-backed canonical death classification rows from player_event_raw_ledger, but exact per-death reason capture remains unavailable.",
    ),
}


def build_elo_event_telemetry_contract() -> dict[str, object]:
    """Return the canonical telemetry contract for tactical event ingestion."""
    return {
        "contract_version": ELO_EVENT_TELEMETRY_CONTRACT_VERSION,
        "storage_strategy": ELO_EVENT_STORAGE_STRATEGY,
        "common_event_fields": list(COMMON_EVENT_FIELDS),
        "common_rules": deepcopy(COMMON_EVENT_RULES),
        "event_families": deepcopy(EVENT_FAMILY_CONTRACTS),
    }
