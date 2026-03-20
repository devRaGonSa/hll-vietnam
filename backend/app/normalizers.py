"""Normalization helpers for provisional server collection flows."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Mapping

if TYPE_CHECKING:
    from .a2s_client import A2SServerInfo


def normalize_server_record(
    raw_record: Mapping[str, object],
    *,
    source_name: str,
) -> dict[str, object]:
    """Normalize a raw server record into the collector's internal shape."""
    external_server_id = _string_or_none(raw_record.get("external_server_id"))
    return {
        "external_server_id": external_server_id,
        "server_name": _string_or_default(raw_record.get("server_name"), "Unknown server"),
        "status": _normalize_status(raw_record.get("status")),
        "players": _coerce_int(raw_record.get("players")),
        "max_players": _coerce_int(raw_record.get("max_players")),
        "current_map": _string_or_none(raw_record.get("current_map")),
        "region": _string_or_none(raw_record.get("region")),
        "source_name": source_name,
        "snapshot_origin": "controlled-fallback",
        "source_ref": external_server_id or source_name,
    }


def normalize_a2s_server_info(
    server_info: "A2SServerInfo",
    *,
    source_name: str,
    external_server_id: str | None = None,
    region: str | None = None,
) -> dict[str, object]:
    """Normalize a probed A2S payload into the collector's internal shape."""
    resolved_external_id = external_server_id or (
        f"a2s:{server_info.host}:{server_info.query_port}"
    )
    return {
        "external_server_id": resolved_external_id,
        "server_name": server_info.server_name or "Unknown server",
        "status": "online",
        "players": server_info.players,
        "max_players": server_info.max_players,
        "current_map": server_info.map_name,
        "region": region,
        "source_name": source_name,
        "snapshot_origin": "real-a2s",
        "source_ref": f"a2s://{server_info.host}:{server_info.query_port}",
    }


def _normalize_status(value: object) -> str:
    if not isinstance(value, str):
        return "unknown"

    normalized = value.strip().lower()
    if normalized in {"online", "offline", "unknown"}:
        return normalized

    return "unknown"


def _coerce_int(value: object) -> int | None:
    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _string_or_none(value: object) -> str | None:
    if not isinstance(value, str):
        return None

    stripped = value.strip()
    return stripped or None


def _string_or_default(value: object, default: str) -> str:
    normalized = _string_or_none(value)
    return normalized or default
