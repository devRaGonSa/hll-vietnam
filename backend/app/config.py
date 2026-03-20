"""Local development configuration for the HLL Vietnam backend bootstrap."""

from __future__ import annotations

import os
from pathlib import Path


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_STORAGE_FILENAME = "hll_vietnam_dev.sqlite3"
DEFAULT_REFRESH_INTERVAL_SECONDS = 120
DEFAULT_ALLOWED_ORIGINS = (
    "null",
    "http://127.0.0.1:5500",
    "http://127.0.0.1:8080",
    "http://localhost:5500",
    "http://localhost:8080",
)
DEFAULT_A2S_TARGETS_ENV_VAR = "HLL_BACKEND_A2S_TARGETS"
DEFAULT_A2S_SOURCE_NAME = "community-hispana-a2s"
DEFAULT_HISTORICAL_SCOREBOARD_SOURCES = (
    {
        "external_server_id": "comunidad-hispana-01",
        "display_name": "Comunidad Hispana #01",
        "scoreboard_base_url": "https://scoreboard.comunidadhll.es",
    },
    {
        "external_server_id": "comunidad-hispana-02",
        "display_name": "Comunidad Hispana #02",
        "scoreboard_base_url": "https://scoreboard.comunidadhll.es:5443",
    },
)


def get_bind_address() -> tuple[str, int]:
    """Return the host and port used by the local backend bootstrap."""
    host = os.getenv("HLL_BACKEND_HOST", DEFAULT_HOST)
    port = int(os.getenv("HLL_BACKEND_PORT", str(DEFAULT_PORT)))
    return host, port


def get_allowed_origins() -> tuple[str, ...]:
    """Return the small allowlist used for local frontend development."""
    raw_origins = os.getenv(
        "HLL_BACKEND_ALLOWED_ORIGINS",
        ",".join(DEFAULT_ALLOWED_ORIGINS),
    )
    origins = []
    for origin in raw_origins.split(","):
        normalized_origin = _normalize_origin(origin)
        if normalized_origin:
            origins.append(normalized_origin)
    return tuple(origins) or DEFAULT_ALLOWED_ORIGINS


def _normalize_origin(origin: str) -> str:
    """Normalize configured origins so env overrides match browser Origin values."""
    return origin.strip().rstrip("/")


def get_storage_path() -> Path:
    """Return the local SQLite path used for development snapshot persistence."""
    default_path = Path(__file__).resolve().parent.parent / "data" / DEFAULT_STORAGE_FILENAME
    configured_path = os.getenv("HLL_BACKEND_STORAGE_PATH")
    return Path(configured_path) if configured_path else default_path


def get_refresh_interval_seconds() -> int:
    """Return the default interval used by the local refresh loop."""
    configured_value = os.getenv(
        "HLL_BACKEND_REFRESH_INTERVAL_SECONDS",
        str(DEFAULT_REFRESH_INTERVAL_SECONDS),
    )
    interval_seconds = int(configured_value)
    if interval_seconds <= 0:
        raise ValueError("HLL_BACKEND_REFRESH_INTERVAL_SECONDS must be positive.")

    return interval_seconds


def get_a2s_targets_payload() -> str | None:
    """Return the optional JSON payload that overrides local A2S targets."""
    raw_payload = os.getenv(DEFAULT_A2S_TARGETS_ENV_VAR)
    if raw_payload is None:
        return None

    normalized = raw_payload.strip()
    return normalized or None


def get_historical_scoreboard_sources() -> tuple[dict[str, str], ...]:
    """Return the real scoreboard sources used for historical player stats."""
    return tuple(dict(source) for source in DEFAULT_HISTORICAL_SCOREBOARD_SOURCES)
