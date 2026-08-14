"""Verified CRCON schema requirements and capability reporting."""

from __future__ import annotations

from collections.abc import Mapping, Set

from .models import (
    CrconCapability,
    CrconCapabilityReport,
    CrconCapabilityResult,
    CrconCapabilityStatus,
)


SchemaColumns = Mapping[str, Set[str]]


CAPABILITY_SCHEMA: Mapping[CrconCapability, Mapping[str, frozenset[str]]] = {
    CrconCapability.HISTORICAL_MAPS: {
        "map_history": frozenset(
            {"id", "start", "end", "server_number", "map_name", "result"}
        ),
    },
    CrconCapability.HISTORICAL_PLAYER_STATS: {
        "map_history": frozenset({"id", "start", "end", "server_number"}),
        "player_stats": frozenset(
            {
                "id",
                "playersteamid_id",
                "map_id",
                "name",
                "kills",
                "deaths",
                "teamkills",
                "time_seconds",
                "combat",
                "offense",
                "defense",
                "support",
                "weapons",
            }
        ),
    },
    CrconCapability.EVENT_LOGS: {
        "log_lines": frozenset(
            {
                "id",
                "event_time",
                "type",
                "player1_name",
                "player1_steamid",
                "player2_name",
                "player2_steamid",
                "weapon",
                "server",
                "game",
            }
        ),
        "steam_id_64": frozenset({"id", "steam_id_64"}),
    },
    CrconCapability.PLAYER_IDENTITIES: {
        "steam_id_64": frozenset({"id", "steam_id_64"}),
        "player_soldier": frozenset(
            {"playersteamid_id", "eos_id", "name", "level", "platform", "clan_tag"}
        ),
        "player_names": frozenset(
            {"playersteamid_id", "name", "created", "last_seen"}
        ),
    },
    CrconCapability.PLAYER_SESSIONS: {
        "player_sessions": frozenset(
            {"playersteamid_id", "start", "end", "server_number", "server_name"}
        ),
    },
    CrconCapability.SERVER_COUNT_HISTORY: {
        "server_counts": frozenset(
            {"server_number", "datapoint_time", "map_id", "count", "vip_count"}
        ),
    },
}

PROBED_TABLES = frozenset(
    table_name
    for requirements in CAPABILITY_SCHEMA.values()
    for table_name in requirements
)


def build_capability_report(
    *,
    schema_columns: SchemaColumns | None,
    database_configured: bool,
    api_configured: bool,
) -> CrconCapabilityReport:
    """Build independent API/database capability states without side effects."""
    results = [
        CrconCapabilityResult(
            capability=CrconCapability.LIVE_STATE,
            status=(
                CrconCapabilityStatus.SUPPORTED
                if api_configured
                else CrconCapabilityStatus.UNAVAILABLE
            ),
            reason=None if api_configured else "CRCON API is not configured.",
        )
    ]

    for capability, requirements in CAPABILITY_SCHEMA.items():
        if not database_configured:
            results.append(
                CrconCapabilityResult(
                    capability=capability,
                    status=CrconCapabilityStatus.UNAVAILABLE,
                    reason="CRCON database is not configured.",
                )
            )
            continue

        available = schema_columns or {}
        missing_tables = sorted(table for table in requirements if table not in available)
        if missing_tables:
            results.append(
                CrconCapabilityResult(
                    capability=capability,
                    status=CrconCapabilityStatus.UNAVAILABLE,
                    reason=f"Missing table: {missing_tables[0]}.",
                )
            )
            continue

        missing_columns = [
            (table, column)
            for table, required_columns in requirements.items()
            for column in sorted(required_columns - set(available[table]))
        ]
        if missing_columns:
            table, column = missing_columns[0]
            results.append(
                CrconCapabilityResult(
                    capability=capability,
                    status=CrconCapabilityStatus.INCOMPATIBLE,
                    reason=f"Missing column: {table}.{column}.",
                )
            )
            continue

        results.append(
            CrconCapabilityResult(
                capability=capability,
                status=CrconCapabilityStatus.SUPPORTED,
            )
        )

    return CrconCapabilityReport(results=tuple(results))
