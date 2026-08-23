"""Static, health and shared error response contracts."""

from __future__ import annotations

from ...config import get_historical_data_source_kind, get_live_data_source_kind
from ...data_sources import (
    SOURCE_KIND_RCON,
    describe_historical_runtime_policy,
)

def build_health_payload() -> dict[str, str]:
    """Return a small status payload without committing to business contracts."""
    return {
        "status": "ok",
        "service": "hll-vietnam-backend",
        "phase": "bootstrap",
        "live_data_source": get_live_data_source_kind(),
        "historical_data_source": get_historical_data_source_kind(),
        "historical_runtime_policy": describe_historical_runtime_policy()["mode"],
        "live_runtime_policy": (
            "rcon-first-with-a2s-fallback"
            if get_live_data_source_kind() == SOURCE_KIND_RCON
            else "a2s-primary"
        ),
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


def build_error_payload(message: str) -> dict[str, str]:
    """Return the shared error payload shape used by the backend bootstrap."""
    return {
        "status": "error",
        "message": message,
    }
