"""Payload builders for the HLL Vietnam backend."""

from __future__ import annotations

from datetime import datetime, timezone

from .collector import collect_server_snapshots
from .config import get_refresh_interval_seconds
from .historical_storage import list_weekly_top_kills
from .normalizers import normalize_map_name
from .server_targets import load_a2s_targets
from .storage import list_latest_snapshots, list_server_history, list_snapshot_history


def build_health_payload() -> dict[str, str]:
    """Return a small status payload without committing to business contracts."""
    return {
        "status": "ok",
        "service": "hll-vietnam-backend",
        "phase": "bootstrap",
    }


def build_community_payload() -> dict[str, object]:
    """Return placeholder community content aligned with the documented contract."""
    return {
        "status": "ok",
        "data": {
            "title": "Comunidad Hispana HLL Vietnam",
            "summary": "Punto de encuentro para jugadores, escuadras y comunidad.",
            "discord_invite_url": "https://discord.com/invite/PedEqZ2Xsa",
        },
    }


def build_trailer_payload() -> dict[str, object]:
    """Return placeholder trailer metadata for future frontend consumption."""
    return {
        "status": "ok",
        "data": {
            "video_url": "https://www.youtube.com/embed/JzYzYNVWZ_A",
            "title": "Trailer HLL Vietnam",
            "provider": "youtube",
        },
    }


def build_discord_payload() -> dict[str, object]:
    """Return public Discord placeholder data without real integration."""
    return {
        "status": "ok",
        "data": {
            "invite_url": "https://discord.com/invite/PedEqZ2Xsa",
            "label": "Unirse al Discord",
            "availability": "manual",
        },
    }


def build_servers_payload() -> dict[str, object]:
    """Return current server status, refreshing stale snapshots before responding."""
    max_snapshot_age_seconds = get_refresh_interval_seconds()
    persisted_items = _select_primary_snapshot_items(
        _enrich_server_items(list_latest_snapshots())
    )
    persisted_snapshot_at = _resolve_last_snapshot_at(persisted_items)
    persisted_snapshot_age_seconds = _calculate_snapshot_age_seconds(persisted_snapshot_at)

    refresh_attempted = _should_refresh_snapshot(
        persisted_items,
        persisted_snapshot_age_seconds,
        max_snapshot_age_seconds,
    )
    refresh_errors: list[dict[str, object]] = []

    if refresh_attempted:
        refreshed_items, refresh_errors = _try_collect_real_time_snapshot()
        if refreshed_items:
            refreshed_snapshot_at = _resolve_last_snapshot_at(refreshed_items)
            refreshed_snapshot_age_seconds = _calculate_snapshot_age_seconds(refreshed_snapshot_at)
            return _build_servers_response(
                items=refreshed_items,
                response_source="real-time-a2s-refresh",
                last_snapshot_at=refreshed_snapshot_at,
                snapshot_age_seconds=refreshed_snapshot_age_seconds,
                max_snapshot_age_seconds=max_snapshot_age_seconds,
                refresh_attempted=True,
                refresh_status="success",
                refresh_errors=refresh_errors,
            )

    if persisted_items:
        refresh_status = "failed" if refresh_attempted else "not-needed"
        response_source = (
            "persisted-stale-snapshot" if refresh_attempted else "persisted-fresh-snapshot"
        )
        return _build_servers_response(
            items=persisted_items,
            response_source=response_source,
            last_snapshot_at=persisted_snapshot_at,
            snapshot_age_seconds=persisted_snapshot_age_seconds,
            max_snapshot_age_seconds=max_snapshot_age_seconds,
            refresh_attempted=refresh_attempted,
            refresh_status=refresh_status,
            refresh_errors=refresh_errors,
        )

    return {
        "status": "ok",
        "data": {
            "title": "Estado actual de servidores",
            "context": "current-hll-status",
            "source": "no-snapshot-available",
            "last_snapshot_at": None,
            "snapshot_age_seconds": None,
            "snapshot_age_minutes": None,
            "max_snapshot_age_seconds": max_snapshot_age_seconds,
            "is_stale": True,
            "freshness": "stale",
            "refresh_attempted": refresh_attempted,
            "refresh_status": "failed" if refresh_attempted else "not-needed",
            "refresh_errors": refresh_errors,
            "items": [],
        },
    }


def build_server_latest_payload() -> dict[str, object]:
    """Return the latest persisted snapshot for each known server."""
    items = _enrich_server_items(list_latest_snapshots())
    return {
        "status": "ok",
        "data": {
            "title": "Ultimo estado conocido de servidores",
            "context": "current-hll-history",
            "source": "local-snapshot-storage",
            "summary_window_size": 6,
            "items": items,
        },
    }


def build_server_history_payload(*, limit: int = 20) -> dict[str, object]:
    """Return recent persisted snapshots across all known servers."""
    items = _enrich_server_items(list_snapshot_history(limit=limit))
    return {
        "status": "ok",
        "data": {
            "title": "Historial reciente de servidores",
            "context": "current-hll-history",
            "source": "local-snapshot-storage",
            "limit": limit,
            "items": items,
        },
    }


def build_server_detail_history_payload(
    server_id: str,
    *,
    limit: int = 20,
) -> dict[str, object]:
    """Return recent persisted snapshots for one server."""
    items = _enrich_server_items(list_server_history(server_id, limit=limit))
    return {
        "status": "ok",
        "data": {
            "title": "Historial por servidor",
            "context": "current-hll-history",
            "source": "local-snapshot-storage",
            "server_id": server_id,
            "limit": limit,
            "items": items,
        },
    }


def build_error_payload(message: str) -> dict[str, str]:
    """Return the shared error payload shape used by the backend bootstrap."""
    return {
        "status": "error",
        "message": message,
    }


def build_weekly_top_kills_payload(
    *,
    limit: int = 10,
    server_id: str | None = None,
) -> dict[str, object]:
    """Return weekly top kills grouped by real community server."""
    result = list_weekly_top_kills(limit=limit, server_id=server_id)
    return {
        "status": "ok",
        "data": {
            "title": "Top kills semanales por servidor",
            "context": "historical-top-kills",
            "metric": "kills",
            "window_days": 7,
            "window_start": result["window_start"],
            "window_end": result["window_end"],
            "limit": limit,
            "items": result["items"],
        },
    }


def _enrich_server_items(items: list[dict[str, object]]) -> list[dict[str, object]]:
    target_index = {
        target.external_server_id: target
        for target in load_a2s_targets()
        if target.external_server_id
    }
    enriched_items: list[dict[str, object]] = []
    for item in items:
        enriched_items.append(_enrich_server_item(item, target_index))
    return enriched_items


def _select_primary_snapshot_items(items: list[dict[str, object]]) -> list[dict[str, object]]:
    real_items = [
        item
        for item in items
        if item.get("snapshot_origin") == "real-a2s"
    ]
    return real_items or items


def _enrich_server_item(
    item: dict[str, object],
    target_index: dict[str, object],
) -> dict[str, object]:
    enriched = dict(item)
    enriched["current_map"] = normalize_map_name(enriched.get("current_map"))
    external_server_id = enriched.get("external_server_id")
    snapshot_origin = enriched.get("snapshot_origin")
    target = target_index.get(external_server_id)

    if not target or snapshot_origin != "real-a2s":
        enriched["host"] = None
        enriched["query_port"] = None
        enriched["game_port"] = None
        return enriched

    enriched["host"] = target.host
    enriched["query_port"] = target.query_port
    enriched["game_port"] = target.game_port
    return enriched


def _resolve_last_snapshot_at(items: list[dict[str, object]]) -> str | None:
    timestamps = [
        str(item["captured_at"])
        for item in items
        if item.get("captured_at")
    ]
    if not timestamps:
        return None

    return max(timestamps)


def _should_refresh_snapshot(
    items: list[dict[str, object]],
    snapshot_age_seconds: int | None,
    max_snapshot_age_seconds: int,
) -> bool:
    if not items:
        return True

    if snapshot_age_seconds is None:
        return True

    return snapshot_age_seconds > max_snapshot_age_seconds


def _try_collect_real_time_snapshot() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    payload = collect_server_snapshots(
        source_mode="a2s",
        allow_controlled_fallback=False,
        persist=True,
    )
    snapshots = payload.get("snapshots")
    items = _select_primary_snapshot_items(_enrich_server_items(list(snapshots or [])))
    errors = payload.get("errors")
    return items, list(errors or [])


def _build_servers_response(
    *,
    items: list[dict[str, object]],
    response_source: str,
    last_snapshot_at: str | None,
    snapshot_age_seconds: int | None,
    max_snapshot_age_seconds: int,
    refresh_attempted: bool,
    refresh_status: str,
    refresh_errors: list[dict[str, object]],
) -> dict[str, object]:
    freshness = (
        "fresh"
        if snapshot_age_seconds is not None and snapshot_age_seconds <= max_snapshot_age_seconds
        else "stale"
    )
    return {
        "status": "ok",
        "data": {
            "title": "Estado actual de servidores",
            "context": "current-hll-status",
            "source": response_source,
            "last_snapshot_at": last_snapshot_at,
            "snapshot_age_seconds": snapshot_age_seconds,
            "snapshot_age_minutes": _to_snapshot_age_minutes(snapshot_age_seconds),
            "max_snapshot_age_seconds": max_snapshot_age_seconds,
            "is_stale": freshness == "stale",
            "freshness": freshness,
            "refresh_attempted": refresh_attempted,
            "refresh_status": refresh_status,
            "refresh_errors": refresh_errors,
            "items": items,
        },
    }


def _calculate_snapshot_age_seconds(timestamp: str | None) -> int | None:
    if not timestamp:
        return None

    normalized = timestamp.replace("Z", "+00:00")
    captured_at = datetime.fromisoformat(normalized)
    if captured_at.tzinfo is None:
        captured_at = captured_at.replace(tzinfo=timezone.utc)

    age = datetime.now(timezone.utc) - captured_at.astimezone(timezone.utc)
    return max(0, int(age.total_seconds()))


def _to_snapshot_age_minutes(snapshot_age_seconds: int | None) -> int | None:
    if snapshot_age_seconds is None:
        return None

    return snapshot_age_seconds // 60
