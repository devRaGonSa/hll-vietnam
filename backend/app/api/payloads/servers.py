"""Server-list and legacy server-snapshot compatibility payloads."""

from __future__ import annotations

from datetime import datetime, timezone

from ...config import (
    get_live_data_source_kind,
    get_refresh_interval_seconds,
    get_server_list_source,
)
from ...data_sources import (
    LIVE_SOURCE_A2S,
    SOURCE_KIND_RCON,
    build_source_attempt,
    build_source_policy,
    get_live_data_source,
)
from ...normalizers import normalize_map_name
from ...scoreboard_origins import get_trusted_public_scoreboard_origin
from ...services.servers import (
    build_crcon_server_list_payload,
    get_crcon_server_list_service,
)
from ...storage import list_latest_snapshots, list_server_history, list_snapshot_history

PUBLIC_SERVER_STATUS_TIMEOUT_SECONDS = 2.5

def build_servers_payload() -> dict[str, object]:
    """Return current server status, refreshing stale snapshots before responding."""
    if get_server_list_source() == "crcon":
        return build_crcon_server_list_payload(get_crcon_server_list_service())
    return _build_legacy_servers_payload()


def _build_legacy_servers_payload() -> dict[str, object]:
    """Preserve the persisted/A2S/RCON server-list path as explicit rollback."""

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
    refresh_source_policy = build_source_policy(
        primary_source=get_live_data_source_kind(),
        selected_source="none",
        fallback_reason=None,
        source_attempts=[],
    )

    if refresh_attempted:
        refreshed_items, refresh_errors, refresh_source_policy = _try_collect_real_time_snapshot()
        if refreshed_items:
            refreshed_snapshot_at = _resolve_last_snapshot_at(refreshed_items)
            refreshed_snapshot_age_seconds = _calculate_snapshot_age_seconds(refreshed_snapshot_at)
            return _build_servers_response(
                items=refreshed_items,
                response_source=_build_live_response_source(refresh_source_policy),
                last_snapshot_at=refreshed_snapshot_at,
                snapshot_age_seconds=refreshed_snapshot_age_seconds,
                max_snapshot_age_seconds=max_snapshot_age_seconds,
                refresh_attempted=True,
                refresh_status="success",
                refresh_errors=refresh_errors,
                source_policy=refresh_source_policy,
            )

    if persisted_items:
        refresh_status = "failed" if refresh_attempted else "not-needed"
        response_source = (
            "persisted-stale-snapshot"
            if refresh_attempted
            else "persisted-fresh-snapshot"
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
            source_policy=_infer_live_source_policy_from_items(
                persisted_items,
                refresh_attempted=refresh_attempted,
                refresh_errors=refresh_errors,
            ),
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
            **refresh_source_policy,
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


def _enrich_server_items(items: list[dict[str, object]]) -> list[dict[str, object]]:
    target_index = get_live_data_source().build_target_index()
    enriched_items: list[dict[str, object]] = []
    for item in items:
        enriched_items.append(_enrich_server_item(item, target_index))
    return enriched_items


def _select_primary_snapshot_items(items: list[dict[str, object]]) -> list[dict[str, object]]:
    preferred_origin = (
        "real-rcon"
        if get_live_data_source_kind() == "rcon"
        else "real-a2s"
    )
    preferred_items = [
        item
        for item in items
        if item.get("snapshot_origin") == preferred_origin
    ]
    return preferred_items or items


def _enrich_server_item(
    item: dict[str, object],
    target_index: dict[str, object],
) -> dict[str, object]:
    enriched = dict(item)
    enriched["current_map"] = normalize_map_name(enriched.get("current_map"))
    history_url = _resolve_community_history_url(enriched.get("external_server_id"))
    enriched["community_history_url"] = history_url
    enriched["community_history_available"] = bool(history_url)
    external_server_id = enriched.get("external_server_id")
    snapshot_origin = enriched.get("snapshot_origin")
    target = target_index.get(external_server_id)

    if not target or snapshot_origin not in {"real-a2s", "real-rcon"}:
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


def _try_collect_real_time_snapshot() -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
    dict[str, object],
]:
    try:
        payload = get_live_data_source().collect_snapshots(
            persist=False,
            timeout_seconds=PUBLIC_SERVER_STATUS_TIMEOUT_SECONDS,
        )
    except Exception as error:  # noqa: BLE001 - public server status must degrade cleanly
        reason = _public_server_refresh_error_reason(error)
        return (
            [],
            [
                {
                    "source": get_live_data_source_kind(),
                    "reason": reason,
                    "error_type": type(error).__name__,
                    "message": str(error),
                }
            ],
            build_source_policy(
                primary_source=get_live_data_source_kind(),
                selected_source="none",
                fallback_used=True,
                fallback_reason=reason,
                source_attempts=[
                    build_source_attempt(
                        source=get_live_data_source_kind(),
                        role="primary",
                        status="error",
                        reason=reason,
                        message=str(error),
                    )
                ],
            ),
        )
    snapshots = payload.get("snapshots")
    items = _select_primary_snapshot_items(_enrich_server_items(list(snapshots or [])))
    errors = payload.get("errors")
    return (
        items,
        list(errors or []),
        {
            "primary_source": payload.get("primary_source"),
            "selected_source": payload.get("selected_source"),
            "fallback_used": bool(payload.get("fallback_used")),
            "fallback_reason": payload.get("fallback_reason"),
            "source_attempts": list(payload.get("source_attempts") or []),
        },
    )


def _public_server_refresh_error_reason(error: Exception) -> str:
    message = str(error).lower()
    if isinstance(error, TimeoutError) or "timeout" in message or "timed out" in message:
        return "live-refresh-timeout"
    if "no rcon targets" in message or "no live" in message or "configured" in message:
        return "live-refresh-unavailable"
    return "live-refresh-failed"


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
    source_policy: dict[str, object],
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
            **source_policy,
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


def _infer_live_source_policy_from_items(
    items: list[dict[str, object]],
    *,
    refresh_attempted: bool,
    refresh_errors: list[dict[str, object]],
) -> dict[str, object]:
    selected_source = "persisted-snapshot"
    fallback_used = False
    fallback_reason = None
    snapshot_origins = {
        str(item.get("snapshot_origin") or "").strip()
        for item in items
        if item.get("snapshot_origin")
    }
    if "real-rcon" in snapshot_origins:
        selected_source = SOURCE_KIND_RCON
    elif "real-a2s" in snapshot_origins:
        selected_source = LIVE_SOURCE_A2S
        if get_live_data_source_kind() == SOURCE_KIND_RCON:
            fallback_used = True
            fallback_reason = "persisted-live-snapshot-came-from-a2s"

    attempt_status = "success" if items else ("error" if refresh_attempted else "cached")
    attempt_reason = None if items else "no-live-snapshot-items"
    if refresh_errors and attempt_reason is None:
        attempt_reason = "live-refresh-errors-present"

    return build_source_policy(
        primary_source=get_live_data_source_kind(),
        selected_source=selected_source,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        source_attempts=[
            build_source_attempt(
                source=selected_source,
                role="served-response",
                status=attempt_status,
                reason=attempt_reason,
            )
        ],
    )


def _build_live_response_source(source_policy: dict[str, object]) -> str:
    selected_source = str(source_policy.get("selected_source") or "")
    if selected_source == SOURCE_KIND_RCON:
        return "real-time-rcon-refresh"
    if selected_source == LIVE_SOURCE_A2S:
        return "real-time-a2s-fallback"
    return "real-time-refresh"


def _resolve_community_history_url(external_server_id: object) -> str | None:
    normalized_server_id = str(external_server_id or "").strip()
    if not normalized_server_id:
        return None
    origin = get_trusted_public_scoreboard_origin(normalized_server_id)
    return f"{origin.base_url}/games" if origin else None
