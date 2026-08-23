"""Pure compatibility-serialization helpers shared by API payload families."""

from __future__ import annotations

from datetime import datetime, timezone


ALL_SERVERS_SCOPE = "all-servers"


def utc_timestamp_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def to_iso_or_none(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def normalize_public_server_id(server_id: str | None) -> str:
    normalized = str(server_id or "").strip().lower()
    if not normalized or normalized == "all":
        return ALL_SERVERS_SCOPE
    return str(server_id).strip()


def serialize_public_server_id(server_id: object) -> str:
    normalized = str(server_id or "").strip()
    if not normalized or normalized == ALL_SERVERS_SCOPE:
        return "all"
    return normalized


def normalize_global_ranking_items(items: object) -> list[dict[str, object]]:
    normalized_items: list[dict[str, object]] = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        matches_considered = int(item.get("matches_considered") or 0)
        kills = int(item.get("kills") or 0)
        normalized_items.append(
            {
                "ranking_position": int(item.get("ranking_position") or 0),
                "player_id": item.get("player_id"),
                "player_name": item.get("player_name"),
                "metric_value": coerce_public_metric_value(item.get("metric_value")),
                "matches_considered": matches_considered,
                "kills": kills,
                "deaths": int(item.get("deaths") or 0),
                "teamkills": int(item.get("teamkills") or 0),
                "kd_ratio": float(item.get("kd_ratio") or 0.0),
                "kills_per_match": float(
                    item.get("kills_per_match")
                    if item.get("kills_per_match") is not None
                    else round(kills / matches_considered, 2)
                    if matches_considered
                    else 0.0
                ),
            }
        )
    return normalized_items


def coerce_public_metric_value(value: object) -> int | float:
    try:
        numeric = float(value or 0)
    except (TypeError, ValueError):
        return 0
    if numeric.is_integer():
        return int(numeric)
    return round(numeric, 2)


def source_when_present(*values: object, source: str) -> str | None:
    return source if any(value is not None for value in values) else None


def snapshot_player_count_quality(item: dict[str, object] | None) -> str | None:
    if item is None or item.get("players") is None:
        return None
    if item.get("snapshot_origin") == "real-rcon":
        return "rcon-session-unverified"
    if item.get("snapshot_origin") == "real-a2s":
        return "a2s-query"
    return "snapshot-unverified"


def snapshot_player_count_source(item: dict[str, object] | None) -> str | None:
    if item is None or item.get("players") is None:
        return None
    if item.get("snapshot_origin") == "real-rcon":
        return "rcon-session"
    if item.get("snapshot_origin") == "real-a2s":
        return "a2s"
    return "live-server-snapshot"
