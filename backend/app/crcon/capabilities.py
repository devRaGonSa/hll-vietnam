"""Verified CRCON schema requirements and capability reporting."""

from __future__ import annotations

from collections.abc import Mapping, Set

from .models import (
    CrconCapability,
    CrconCapabilityReport,
    CrconCapabilityResult,
    CrconCapabilityStatus,
    CrconContractStatus,
)


SchemaColumns = Mapping[str, Set[str]]


CAPABILITY_SCHEMA: Mapping[CrconCapability, Mapping[str, frozenset[str]]] = {
    CrconCapability.HISTORICAL_MAPS: {
        "map_history": frozenset(
            {"id", "start", "end", "server_number", "map_name", "result"}
        ),
    },
    CrconCapability.HISTORICAL_PLAYER_STATS: {
        "map_history": frozenset({"id", "start", "end", "server_number", "game"}),
        "player_stats": frozenset(
            {
                "id",
                "playersteamid_id",
                "map_id",
                "name",
                "kills",
                "deaths",
                "teamkills",
                "deaths_by_tk",
                "time_seconds",
                "combat",
                "offense",
                "defense",
                "support",
                "weapons",
            }
        ),
    },
    CrconCapability.PLAYER_AGGREGATES: {
        "map_history": frozenset({"id", "start", "end", "server_number", "map_name", "game"}),
        "steam_id_64": frozenset({"id", "steam_id_64", "steam_id"}),
        "player_stats": frozenset(
            {
                "playersteamid_id",
                "map_id",
                "kills",
                "deaths",
                "teamkills",
                "deaths_by_tk",
                "time_seconds",
                "combat",
                "offense",
                "defense",
                "support",
                "vehicle_kills",
                "vehicles_destroyed",
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


API_ENDPOINTS_12_0_1 = (
    "get_public_info",
    "get_live_game_stats",
    "get_live_scoreboard",
    "get_scoreboard_maps",
    "get_map_scoreboard",
    "get_map_history",
    "get_previous_map",
)

# Evidence observed on 2026-08-21 from two authorized public HLL targets that
# both reported v12.0.1 before any contract response was used. No HLLV target
# and no deployed PostgreSQL read-only role were available.
CRCON_12_0_1_EVIDENCE_MATRIX: Mapping[
    str, Mapping[str, CrconContractStatus]
] = {
    **{
        endpoint: {
            "hll": CrconContractStatus.SUPPORTED,
            "hllv": CrconContractStatus.UNVERIFIED,
        }
        for endpoint in API_ENDPOINTS_12_0_1
    },
    "live_game_match_scoped": {
        "hll": CrconContractStatus.SUPPORTED,
        "hllv": CrconContractStatus.UNVERIFIED,
    },
    "live_scoreboard_connected_only": {
        "hll": CrconContractStatus.SUPPORTED,
        "hllv": CrconContractStatus.UNVERIFIED,
    },
    "scoreboard_maps_empty_player_stats": {
        "hll": CrconContractStatus.SUPPORTED,
        "hllv": CrconContractStatus.UNVERIFIED,
    },
    "map_history_recent_only": {
        "hll": CrconContractStatus.SUPPORTED,
        "hllv": CrconContractStatus.UNVERIFIED,
    },
    "identity_player_id_opaque": {
        "hll": CrconContractStatus.SUPPORTED,
        "hllv": CrconContractStatus.UNVERIFIED,
    },
    "identity_platform": {
        "hll": CrconContractStatus.SUPPORTED,
        "hllv": CrconContractStatus.UNVERIFIED,
    },
    # The seven verified API responses do not expose these explicit fields.
    # This does not deny that other CRCON APIs/tables can provide them.
    "identity_explicit_steam_id": {
        "hll": CrconContractStatus.UNSUPPORTED,
        "hllv": CrconContractStatus.UNVERIFIED,
    },
    "identity_explicit_eos_id": {
        "hll": CrconContractStatus.UNSUPPORTED,
        "hllv": CrconContractStatus.UNVERIFIED,
    },
    "postgres_map_history": {
        "hll": CrconContractStatus.UNVERIFIED,
        "hllv": CrconContractStatus.UNVERIFIED,
    },
    "postgres_player_stats": {
        "hll": CrconContractStatus.UNVERIFIED,
        "hllv": CrconContractStatus.UNVERIFIED,
    },
    "postgres_player_sessions": {
        "hll": CrconContractStatus.UNVERIFIED,
        "hllv": CrconContractStatus.UNVERIFIED,
    },
    "postgres_identity": {
        "hll": CrconContractStatus.UNVERIFIED,
        "hllv": CrconContractStatus.UNVERIFIED,
    },
    "postgres_log_lines": {
        "hll": CrconContractStatus.UNVERIFIED,
        "hllv": CrconContractStatus.UNVERIFIED,
    },
    "logs_server_semantics": {
        "hll": CrconContractStatus.UNVERIFIED,
        "hllv": CrconContractStatus.UNVERIFIED,
    },
    "logs_game_string_filter": {
        "hll": CrconContractStatus.UNSUPPORTED,
        "hllv": CrconContractStatus.UNSUPPORTED,
    },
}

API_ENDPOINT_CONTRACTS_12_0_1: Mapping[str, CrconContractStatus] = {
    endpoint: CRCON_12_0_1_EVIDENCE_MATRIX[endpoint]["hll"]
    for endpoint in API_ENDPOINTS_12_0_1
}


def get_contract_evidence_status(
    capability: str,
    *,
    game: str,
) -> CrconContractStatus:
    """Return a game-specific evidence state without collapsing unknown to false."""
    normalized_game = str(game or "").strip().lower()
    if normalized_game not in {"hll", "hllv"}:
        return CrconContractStatus.UNSUPPORTED
    row = CRCON_12_0_1_EVIDENCE_MATRIX.get(str(capability or "").strip())
    if row is None:
        return CrconContractStatus.UNSUPPORTED
    return row[normalized_game]


def get_api_contract_status(
    endpoint: str,
    *,
    game: str = "hll",
) -> CrconContractStatus:
    """Return the version/game-specific endpoint evidence state."""
    return get_contract_evidence_status(endpoint, game=game)

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
    api_contract_status: CrconContractStatus = CrconContractStatus.UNVERIFIED,
    log_semantics_verified: bool = False,
) -> CrconCapabilityReport:
    """Build independent API/database capability states without side effects."""
    results = [
        CrconCapabilityResult(
            capability=CrconCapability.LIVE_STATE,
            status=(
                CrconCapabilityStatus.SUPPORTED
                if api_configured and api_contract_status is CrconContractStatus.SUPPORTED
                else CrconCapabilityStatus.UNSUPPORTED
                if api_configured and api_contract_status is CrconContractStatus.UNSUPPORTED
                else CrconCapabilityStatus.UNKNOWN
                if api_configured
                else CrconCapabilityStatus.UNAVAILABLE
            ),
            reason=(
                None
                if api_configured and api_contract_status is CrconContractStatus.SUPPORTED
                else "CRCON 12.0.1 API contract is unverified."
                if api_configured and api_contract_status is CrconContractStatus.UNVERIFIED
                else "CRCON API contract is unsupported."
                if api_configured
                else "CRCON API is not configured."
            ),
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

        if capability is CrconCapability.EVENT_LOGS and not log_semantics_verified:
            results.append(
                CrconCapabilityResult(
                    capability=capability,
                    status=CrconCapabilityStatus.UNKNOWN,
                    reason=(
                        "CRCON log server/game discriminator semantics are unverified."
                    ),
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
