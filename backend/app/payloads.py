"""Placeholder payload builders for the HLL Vietnam backend."""

from __future__ import annotations

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
    """Return a controlled placeholder for current Hell Let Loose servers."""
    return {
        "status": "ok",
        "data": {
            "title": "Servidores actuales de Hell Let Loose",
            "context": "current-hll-reference",
            "source": "controlled-placeholder",
            "items": [
                {
                    "server_name": "HLL ESP Tactical Rotation",
                    "status": "online",
                    "players": 74,
                    "max_players": 100,
                    "current_map": "Sainte-Marie-du-Mont",
                    "region": "EU",
                },
                {
                    "server_name": "HLL LATAM Night Offensive",
                    "status": "online",
                    "players": 51,
                    "max_players": 100,
                    "current_map": "Carentan",
                    "region": "LATAM",
                },
                {
                    "server_name": "HLL Community Reserve",
                    "status": "offline",
                    "players": 0,
                    "max_players": 100,
                    "current_map": None,
                    "region": "EU",
                },
            ],
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


def _enrich_server_item(
    item: dict[str, object],
    target_index: dict[str, object],
) -> dict[str, object]:
    enriched = dict(item)
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
