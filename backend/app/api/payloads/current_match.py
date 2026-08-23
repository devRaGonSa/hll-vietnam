"""Current-match public contracts with explicit CRCON/legacy selection."""

from __future__ import annotations

import re

from ...config import get_current_match_source
from ...data_sources import (
    SOURCE_KIND_RCON,
    build_source_attempt,
    build_source_policy,
)
from ...normalizers import normalize_map_name
from ...rcon_admin_log_storage import (
    list_current_match_kill_feed,
    list_current_match_player_stats,
)
from ...rcon_client import load_rcon_targets, query_live_server_sample
from ...scoreboard_origins import get_trusted_public_scoreboard_origin
from ...services.current_match import (
    CurrentMatchUnavailableError,
    get_current_match_snapshot_service,
    legacy_kills_projection,
    legacy_players_projection,
    legacy_summary_projection,
    snapshot_payload,
)
from ...services.current_match_shadow import (
    compare_current_match,
    get_final_match_verifier,
    store_current_match_parity,
)
from ..serializers import (
    snapshot_player_count_quality as _snapshot_player_count_quality,
    snapshot_player_count_source as _snapshot_player_count_source,
    source_when_present as _source_when_present,
    utc_timestamp_now as _utc_timestamp_now,
)
from .servers import _build_legacy_servers_payload

def build_current_match_payload(*, server_slug: str) -> dict[str, object]:
    """Return the live page projection for one trusted active server."""
    mode = get_current_match_source()
    if mode == "crcon":
        snapshot = get_current_match_snapshot_service().get_snapshot(server_slug)
        get_final_match_verifier().record_live(snapshot)
        return legacy_summary_projection(snapshot)
    legacy = _build_legacy_current_match_payload(server_slug=server_slug)
    if mode == "shadow":
        legacy_players = _build_legacy_current_match_player_stats_payload(
            server_slug=server_slug
        )
        _run_current_match_shadow(
            server_slug=server_slug,
            legacy_summary=legacy,
            legacy_players=legacy_players,
        )
    return legacy


def _build_legacy_current_match_payload(*, server_slug: str) -> dict[str, object]:
    """Build the canonical legacy summary without consulting CRCON selectors."""
    origin = get_trusted_public_scoreboard_origin(server_slug)
    if origin is None:
        raise ValueError("Unsupported current match server.")

    sample = _query_current_match_rcon_sample(origin.slug)
    if sample is not None:
        normalized = sample["normalized"]
        raw_session = sample["raw_session"]
        captured_at = _utc_timestamp_now()
        map_id = raw_session.get("mapId") or normalized.get("current_map")
        map_name = raw_session.get("mapName") or map_id
        map_pretty_name = normalize_map_name(map_name)
        return {
            "status": "ok",
            "data": {
                "found": True,
                "server_slug": origin.slug,
                "server_name": normalized.get("server_name") or origin.display_name,
                "status": normalized.get("status") or "unavailable",
                "map": map_pretty_name,
                "map_id": map_id,
                "map_pretty_name": map_pretty_name,
                "game_mode": normalized.get("game_mode"),
                "started_at": None,
                "allied_score": normalized.get("allied_score"),
                "axis_score": normalized.get("axis_score"),
                "allied_players": normalized.get("allied_players"),
                "axis_players": normalized.get("axis_players"),
                "players": normalized.get("players"),
                "max_players": normalized.get("max_players"),
                # RCA: getSession currently reports 0 while the public scoreboard
                # can show players, so session population is exposed but unverified.
                "player_count_quality": (
                    "rcon-session-unverified"
                    if normalized.get("players") is not None
                    else None
                ),
                "player_count_source": _source_when_present(
                    normalized.get("players"),
                    source="rcon-session",
                ),
                "score_source": _source_when_present(
                    normalized.get("allied_score"),
                    normalized.get("axis_score"),
                    source="rcon-session",
                ),
                "map_source": _source_when_present(map_id, map_name, source="rcon-session"),
                "match_time_seconds": normalized.get("match_time_seconds"),
                "remaining_match_time_seconds": normalized.get(
                    "remaining_match_time_seconds"
                ),
                "captured_at": captured_at,
                "updated_at": captured_at,
                "public_scoreboard_url": origin.base_url,
            },
        }

    # The generic live server snapshot is a fallback only. It intentionally
    # drops richer RCON session fields such as game mode and current scores.
    server_payload = _build_legacy_servers_payload()
    server_data = server_payload["data"]
    item = _find_current_match_snapshot_item(server_data.get("items", []), origin)
    return {
        "status": "ok",
        "data": {
            "found": item is not None,
            "server_slug": origin.slug,
            "server_name": item.get("server_name") if item else origin.display_name,
            "status": item.get("status") if item else "unavailable",
            "map": item.get("current_map") if item else None,
            "map_id": None,
            "map_pretty_name": item.get("current_map") if item else None,
            "game_mode": item.get("game_mode") if item else None,
            "started_at": item.get("started_at") if item else None,
            "allied_score": item.get("allied_score") if item else None,
            "axis_score": item.get("axis_score") if item else None,
            "allied_players": item.get("allied_players") if item else None,
            "axis_players": item.get("axis_players") if item else None,
            "players": item.get("players") if item else None,
            "max_players": item.get("max_players") if item else None,
            "player_count_quality": _snapshot_player_count_quality(item),
            "player_count_source": _snapshot_player_count_source(item),
            "score_source": _source_when_present(
                item.get("allied_score") if item else None,
                item.get("axis_score") if item else None,
                source="live-server-snapshot",
            ),
            "map_source": _source_when_present(
                item.get("current_map") if item else None,
                source="live-server-snapshot",
            ),
            "match_time_seconds": item.get("match_time_seconds") if item else None,
            "remaining_match_time_seconds": (
                item.get("remaining_match_time_seconds") if item else None
            ),
            "captured_at": item.get("captured_at") if item else None,
            "updated_at": server_data.get("last_snapshot_at"),
            "public_scoreboard_url": origin.base_url,
        },
    }


def _find_current_match_snapshot_item(
    items: list[dict[str, object]],
    origin: object,
) -> dict[str, object] | None:
    """Resolve one trusted live snapshot for the current-match fallback."""
    origin_slug = str(getattr(origin, "slug", "") or "").strip()
    source_markers = {
        "comunidad-hispana-01": ("152.114.195.174", ":7779"),
        "comunidad-hispana-02": ("152.114.195.150", ":7879"),
    }.get(origin_slug)
    server_number = getattr(origin, "server_number", None)

    for item in items:
        if any(
            str(item.get(field) or "").strip() == origin_slug
            for field in (
                "external_server_id",
                "server_slug",
                "target_key",
                "slug",
                "community_slug",
            )
        ):
            return item

        server_label = str(item.get("server_name") or item.get("name") or "")
        if _current_match_server_name_matches(server_label, server_number):
            return item

        source_identity = " ".join(
            str(item.get(field) or "") for field in ("external_server_id", "source_ref")
        )
        if source_markers and any(marker in source_identity for marker in source_markers):
            return item

    return None


def _current_match_server_name_matches(server_label: str, server_number: object) -> bool:
    if not isinstance(server_number, int):
        return False

    normalized_label = server_label.strip().casefold()
    if not normalized_label:
        return False

    numbered_marker = re.compile(rf"(?<!\d)#0*{server_number}(?!\d)")
    if numbered_marker.search(normalized_label):
        return True

    return f"comunidad hispana #{server_number:02d}" in normalized_label


def build_current_match_kill_feed_payload(
    *,
    server_slug: str,
    limit: int = 30,
    since_event_id: str | None = None,
) -> dict[str, object]:
    """Return normalized AdminLog kill rows for one trusted current-match page."""
    mode = get_current_match_source()
    if mode == "crcon":
        origin = get_trusted_public_scoreboard_origin(server_slug)
        if origin is None:
            raise ValueError("Unsupported current match server.")
        service = get_current_match_snapshot_service()
        snapshot = service.get_snapshot(origin.slug)
        get_final_match_verifier().record_live(snapshot)
        events = service.project_kills(
            snapshot,
            since_cursor=since_event_id,
            limit=limit,
        )
        return legacy_kills_projection(snapshot, events)
    legacy = _build_legacy_current_match_kill_feed_payload(
        server_slug=server_slug,
        limit=limit,
        since_event_id=since_event_id,
    )
    if mode == "shadow":
        _run_current_match_shadow(
            server_slug=server_slug,
            legacy_summary=_build_legacy_current_match_payload(server_slug=server_slug),
            legacy_players=_build_legacy_current_match_player_stats_payload(
                server_slug=server_slug
            ),
        )
    return legacy


def _build_legacy_current_match_kill_feed_payload(
    *,
    server_slug: str,
    limit: int = 30,
    since_event_id: str | None = None,
) -> dict[str, object]:
    origin = get_trusted_public_scoreboard_origin(server_slug)
    if origin is None:
        raise ValueError("Unsupported current match server.")
    try:
        feed = list_current_match_kill_feed(
            server_key=origin.slug,
            limit=limit,
            since_event_id=since_event_id,
            ensure_storage=False,
        )
        source_policy = _build_current_match_admin_log_source_policy(status="success")
    except Exception as error:  # noqa: BLE001 - public live read must degrade cleanly
        feed = _empty_current_match_kill_feed_payload()
        source_policy = _build_current_match_admin_log_source_policy(
            status="error",
            error_reason=_public_error_reason(error),
            message=str(error),
        )
    return {
        "status": "ok",
        "data": {
            "server_slug": origin.slug,
            "server_name": origin.display_name,
            **source_policy,
            **feed,
        },
    }


def build_current_match_player_stats_payload(*, server_slug: str) -> dict[str, object]:
    """Return current player stats only when safe AdminLog evidence exists."""
    mode = get_current_match_source()
    if mode == "crcon":
        snapshot = get_current_match_snapshot_service().get_snapshot(server_slug)
        get_final_match_verifier().record_live(snapshot)
        return legacy_players_projection(snapshot)
    legacy = _build_legacy_current_match_player_stats_payload(server_slug=server_slug)
    if mode == "shadow":
        _run_current_match_shadow(
            server_slug=server_slug,
            legacy_summary=_build_legacy_current_match_payload(server_slug=server_slug),
            legacy_players=legacy,
        )
    return legacy


def _build_legacy_current_match_player_stats_payload(
    *,
    server_slug: str,
) -> dict[str, object]:
    origin = get_trusted_public_scoreboard_origin(server_slug)
    if origin is None:
        raise ValueError("Unsupported current match server.")
    try:
        stats = list_current_match_player_stats(
            server_key=origin.slug,
            ensure_storage=False,
        )
        source_policy = _build_current_match_admin_log_source_policy(status="success")
    except Exception as error:  # noqa: BLE001 - public live read must degrade cleanly
        stats = _empty_current_match_player_stats_payload()
        source_policy = _build_current_match_admin_log_source_policy(
            status="error",
            error_reason=_public_error_reason(error),
            message=str(error),
        )
    return {
        "status": "ok",
        "data": {
            "server_slug": origin.slug,
            "server_name": origin.display_name,
            **source_policy,
            **stats,
        },
    }


def build_current_match_snapshot_payload(*, server_slug: str) -> dict[str, object]:
    """Return the canonical coherent snapshot only in explicit CRCON mode."""
    origin = get_trusted_public_scoreboard_origin(server_slug)
    if origin is None:
        raise ValueError("Unsupported current match server.")
    if get_current_match_source() != "crcon":
        raise CurrentMatchUnavailableError(
            "CRCON current-match mode is not selected."
        )
    snapshot = get_current_match_snapshot_service().get_snapshot(origin.slug)
    get_final_match_verifier().record_live(snapshot)
    return snapshot_payload(snapshot)


def _run_current_match_shadow(
    *,
    server_slug: str,
    legacy_summary: dict[str, object],
    legacy_players: dict[str, object],
) -> None:
    """Run bounded CRCON diagnostics without changing or failing the legacy response."""
    crcon_snapshot = None
    try:
        crcon_snapshot = get_current_match_snapshot_service().get_snapshot(server_slug)
        get_final_match_verifier().record_live(crcon_snapshot)
    except Exception:  # noqa: BLE001 - shadow failures never alter the canonical response
        pass
    player_data = legacy_players.get("data")
    items = player_data.get("items") if isinstance(player_data, dict) else None
    report = compare_current_match(
        server_key=server_slug,
        legacy_summary=legacy_summary,
        legacy_players=(
            [item for item in items if isinstance(item, dict)]
            if isinstance(items, list)
            else []
        ),
        crcon_snapshot=crcon_snapshot,
    )
    store_current_match_parity(report)


def _empty_current_match_kill_feed_payload() -> dict[str, object]:
    return {
        "scope": "no-current-match-events",
        "confidence": "unavailable",
        "stale_events_filtered": 0,
        "items": [],
    }


def _empty_current_match_player_stats_payload() -> dict[str, object]:
    return {
        "scope": "no-current-match-events",
        "confidence": "unavailable",
        "source": "rcon-admin-log-current-match-summary",
        "updated_at": None,
        "stale_events_filtered": 0,
        "items": [],
    }


def _build_current_match_admin_log_source_policy(
    *,
    status: str,
    error_reason: str | None = None,
    message: str | None = None,
) -> dict[str, object]:
    return build_source_policy(
        primary_source=SOURCE_KIND_RCON,
        selected_source="rcon-admin-log",
        fallback_used=status != "success",
        fallback_reason=error_reason,
        source_attempts=[
            build_source_attempt(
                source="rcon-admin-log",
                role="read-model",
                status=status,
                reason=error_reason,
                message=message,
            )
        ],
    )


def _public_error_reason(error: Exception) -> str:
    if isinstance(error, FileNotFoundError):
        return "admin-log-read-model-unavailable"
    if isinstance(error, TimeoutError):
        return "admin-log-read-timeout"
    message = str(error).lower()
    if "timeout" in message or "timed out" in message:
        return "admin-log-read-timeout"
    if "does not exist" in message or "no such table" in message:
        return "admin-log-read-model-unavailable"
    return "admin-log-read-failed"


def _query_current_match_rcon_sample(server_slug: str) -> dict[str, object] | None:
    """Read one configured trusted RCON target for the current-match view."""
    try:
        targets = load_rcon_targets()
    except (RuntimeError, ValueError):
        return None
    target = next(
        (candidate for candidate in targets if candidate.external_server_id == server_slug),
        None,
    )
    if target is None:
        return None
    try:
        return query_live_server_sample(target)
    except Exception:  # noqa: BLE001 - fall back to the existing live snapshot read
        return None
