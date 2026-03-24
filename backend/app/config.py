"""Local development configuration for the HLL Vietnam backend bootstrap."""

from __future__ import annotations

import os
from pathlib import Path


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_STORAGE_FILENAME = "hll_vietnam_dev.sqlite3"
DEFAULT_REFRESH_INTERVAL_SECONDS = 300
DEFAULT_LIVE_DATA_SOURCE = "a2s"
DEFAULT_HISTORICAL_DATA_SOURCE = "public-scoreboard"
DEFAULT_RCON_TIMEOUT_SECONDS = 10.0
DEFAULT_HISTORICAL_CRCON_PAGE_SIZE = 50
DEFAULT_HISTORICAL_CRCON_TIMEOUT_SECONDS = 15.0
DEFAULT_HISTORICAL_CRCON_DETAIL_WORKERS = 8
DEFAULT_HISTORICAL_CRCON_REQUEST_RETRIES = 3
DEFAULT_HISTORICAL_CRCON_RETRY_DELAY_SECONDS = 0.5
DEFAULT_HISTORICAL_REFRESH_INTERVAL_SECONDS = 1800
DEFAULT_HISTORICAL_SNAPSHOT_REFRESH_INTERVAL_SECONDS = 900
DEFAULT_HISTORICAL_REFRESH_MAX_RETRIES = 2
DEFAULT_HISTORICAL_REFRESH_RETRY_DELAY_SECONDS = 30
DEFAULT_HISTORICAL_FULL_SNAPSHOT_EVERY_RUNS = 4
DEFAULT_HISTORICAL_WEEKLY_FALLBACK_MIN_MATCHES = 3
DEFAULT_HISTORICAL_WEEKLY_FALLBACK_MAX_WEEKDAY = 2
DEFAULT_PLAYER_EVENT_REFRESH_INTERVAL_SECONDS = 1800
DEFAULT_PLAYER_EVENT_REFRESH_MAX_RETRIES = 2
DEFAULT_PLAYER_EVENT_REFRESH_RETRY_DELAY_SECONDS = 30
DEFAULT_ALLOWED_ORIGINS = (
    "null",
    "http://127.0.0.1:5500",
    "http://127.0.0.1:8080",
    "http://localhost:5500",
    "http://localhost:8080",
)
DEFAULT_A2S_TARGETS_ENV_VAR = "HLL_BACKEND_A2S_TARGETS"
DEFAULT_A2S_SOURCE_NAME = "community-hispana-a2s"
DEFAULT_RCON_TARGETS_ENV_VAR = "HLL_BACKEND_RCON_TARGETS"
DEFAULT_RCON_SOURCE_NAME = "community-hispana-rcon"


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


def get_historical_crcon_page_size() -> int:
    """Return the default page size used for CRCON historical ingestion."""
    configured_value = os.getenv(
        "HLL_HISTORICAL_CRCON_PAGE_SIZE",
        str(DEFAULT_HISTORICAL_CRCON_PAGE_SIZE),
    )
    page_size = int(configured_value)
    if page_size <= 0:
        raise ValueError("HLL_HISTORICAL_CRCON_PAGE_SIZE must be positive.")

    return page_size


def get_historical_crcon_request_timeout_seconds() -> float:
    """Return the timeout used for CRCON historical JSON requests."""
    configured_value = os.getenv(
        "HLL_HISTORICAL_CRCON_TIMEOUT_SECONDS",
        str(DEFAULT_HISTORICAL_CRCON_TIMEOUT_SECONDS),
    )
    timeout_seconds = float(configured_value)
    if timeout_seconds <= 0:
        raise ValueError("HLL_HISTORICAL_CRCON_TIMEOUT_SECONDS must be positive.")

    return timeout_seconds


def get_historical_crcon_detail_workers() -> int:
    """Return the worker count used for CRCON historical detail requests."""
    configured_value = os.getenv(
        "HLL_HISTORICAL_CRCON_DETAIL_WORKERS",
        str(DEFAULT_HISTORICAL_CRCON_DETAIL_WORKERS),
    )
    worker_count = int(configured_value)
    if worker_count <= 0:
        raise ValueError("HLL_HISTORICAL_CRCON_DETAIL_WORKERS must be positive.")

    return worker_count


def get_historical_crcon_request_retries() -> int:
    """Return the retry count used for CRCON historical JSON requests."""
    configured_value = os.getenv(
        "HLL_HISTORICAL_CRCON_REQUEST_RETRIES",
        str(DEFAULT_HISTORICAL_CRCON_REQUEST_RETRIES),
    )
    retry_count = int(configured_value)
    if retry_count <= 0:
        raise ValueError("HLL_HISTORICAL_CRCON_REQUEST_RETRIES must be positive.")

    return retry_count


def get_historical_crcon_retry_delay_seconds() -> float:
    """Return the base delay used between CRCON request retries."""
    configured_value = os.getenv(
        "HLL_HISTORICAL_CRCON_RETRY_DELAY_SECONDS",
        str(DEFAULT_HISTORICAL_CRCON_RETRY_DELAY_SECONDS),
    )
    retry_delay_seconds = float(configured_value)
    if retry_delay_seconds < 0:
        raise ValueError(
            "HLL_HISTORICAL_CRCON_RETRY_DELAY_SECONDS must be zero or positive."
        )

    return retry_delay_seconds


def get_historical_refresh_interval_seconds() -> int:
    """Return the default interval used by the historical refresh loop."""
    configured_value = os.getenv(
        "HLL_HISTORICAL_SNAPSHOT_REFRESH_INTERVAL_SECONDS",
        os.getenv(
            "HLL_HISTORICAL_REFRESH_INTERVAL_SECONDS",
            str(DEFAULT_HISTORICAL_SNAPSHOT_REFRESH_INTERVAL_SECONDS),
        ),
    )
    interval_seconds = int(configured_value)
    if interval_seconds <= 0:
        raise ValueError(
            "HLL_HISTORICAL_SNAPSHOT_REFRESH_INTERVAL_SECONDS must be positive."
        )

    return interval_seconds


def get_live_data_source_kind() -> str:
    """Return the live provider kind selected for the current environment."""
    source_kind = os.getenv("HLL_BACKEND_LIVE_DATA_SOURCE", DEFAULT_LIVE_DATA_SOURCE).strip()
    if source_kind not in {"a2s", "rcon"}:
        raise ValueError("HLL_BACKEND_LIVE_DATA_SOURCE must be 'a2s' or 'rcon'.")
    return source_kind


def get_historical_data_source_kind() -> str:
    """Return the historical provider kind selected for the current environment."""
    source_kind = os.getenv(
        "HLL_BACKEND_HISTORICAL_DATA_SOURCE",
        DEFAULT_HISTORICAL_DATA_SOURCE,
    ).strip()
    if source_kind not in {"public-scoreboard", "rcon"}:
        raise ValueError(
            "HLL_BACKEND_HISTORICAL_DATA_SOURCE must be 'public-scoreboard' or 'rcon'."
        )
    return source_kind


def get_rcon_request_timeout_seconds() -> float:
    """Return the timeout used for HLL RCON TCP requests."""
    configured_value = os.getenv(
        "HLL_BACKEND_RCON_TIMEOUT_SECONDS",
        str(DEFAULT_RCON_TIMEOUT_SECONDS),
    )
    timeout_seconds = float(configured_value)
    if timeout_seconds <= 0:
        raise ValueError("HLL_BACKEND_RCON_TIMEOUT_SECONDS must be positive.")
    return timeout_seconds


def get_historical_refresh_max_retries() -> int:
    """Return the retry count used by the historical refresh loop."""
    configured_value = os.getenv(
        "HLL_HISTORICAL_REFRESH_MAX_RETRIES",
        str(DEFAULT_HISTORICAL_REFRESH_MAX_RETRIES),
    )
    max_retries = int(configured_value)
    if max_retries < 0:
        raise ValueError("HLL_HISTORICAL_REFRESH_MAX_RETRIES must be zero or positive.")

    return max_retries


def get_historical_refresh_retry_delay_seconds() -> int:
    """Return the wait time between historical refresh retries."""
    configured_value = os.getenv(
        "HLL_HISTORICAL_REFRESH_RETRY_DELAY_SECONDS",
        str(DEFAULT_HISTORICAL_REFRESH_RETRY_DELAY_SECONDS),
    )
    retry_delay_seconds = int(configured_value)
    if retry_delay_seconds < 0:
        raise ValueError(
            "HLL_HISTORICAL_REFRESH_RETRY_DELAY_SECONDS must be zero or positive."
        )

    return retry_delay_seconds


def get_historical_full_snapshot_every_runs() -> int:
    """Return how often the runner should rebuild the full snapshot matrix."""
    configured_value = os.getenv(
        "HLL_HISTORICAL_FULL_SNAPSHOT_EVERY_RUNS",
        str(DEFAULT_HISTORICAL_FULL_SNAPSHOT_EVERY_RUNS),
    )
    run_count = int(configured_value)
    if run_count <= 0:
        raise ValueError("HLL_HISTORICAL_FULL_SNAPSHOT_EVERY_RUNS must be positive.")

    return run_count


def get_historical_weekly_fallback_min_matches() -> int:
    """Return the minimum closed matches required to trust the current week."""
    configured_value = os.getenv(
        "HLL_HISTORICAL_WEEKLY_FALLBACK_MIN_MATCHES",
        str(DEFAULT_HISTORICAL_WEEKLY_FALLBACK_MIN_MATCHES),
    )
    min_matches = int(configured_value)
    if min_matches <= 0:
        raise ValueError("HLL_HISTORICAL_WEEKLY_FALLBACK_MIN_MATCHES must be positive.")

    return min_matches


def get_historical_weekly_fallback_max_weekday() -> int:
    """Return the last weekday index where weekly fallback may still apply."""
    configured_value = os.getenv(
        "HLL_HISTORICAL_WEEKLY_FALLBACK_MAX_WEEKDAY",
        str(DEFAULT_HISTORICAL_WEEKLY_FALLBACK_MAX_WEEKDAY),
    )
    max_weekday = int(configured_value)
    if max_weekday < 0 or max_weekday > 6:
        raise ValueError("HLL_HISTORICAL_WEEKLY_FALLBACK_MAX_WEEKDAY must be between 0 and 6.")

    return max_weekday


def get_player_event_refresh_interval_seconds() -> int:
    """Return the default interval used by the player event refresh loop."""
    configured_value = os.getenv(
        "HLL_PLAYER_EVENT_REFRESH_INTERVAL_SECONDS",
        str(DEFAULT_PLAYER_EVENT_REFRESH_INTERVAL_SECONDS),
    )
    interval_seconds = int(configured_value)
    if interval_seconds <= 0:
        raise ValueError("HLL_PLAYER_EVENT_REFRESH_INTERVAL_SECONDS must be positive.")
    return interval_seconds


def get_player_event_refresh_max_retries() -> int:
    """Return the retry count used by the player event refresh loop."""
    configured_value = os.getenv(
        "HLL_PLAYER_EVENT_REFRESH_MAX_RETRIES",
        str(DEFAULT_PLAYER_EVENT_REFRESH_MAX_RETRIES),
    )
    max_retries = int(configured_value)
    if max_retries < 0:
        raise ValueError("HLL_PLAYER_EVENT_REFRESH_MAX_RETRIES must be zero or positive.")
    return max_retries


def get_player_event_refresh_retry_delay_seconds() -> int:
    """Return the wait time between player event refresh retries."""
    configured_value = os.getenv(
        "HLL_PLAYER_EVENT_REFRESH_RETRY_DELAY_SECONDS",
        str(DEFAULT_PLAYER_EVENT_REFRESH_RETRY_DELAY_SECONDS),
    )
    retry_delay_seconds = int(configured_value)
    if retry_delay_seconds < 0:
        raise ValueError(
            "HLL_PLAYER_EVENT_REFRESH_RETRY_DELAY_SECONDS must be zero or positive."
        )
    return retry_delay_seconds


def get_a2s_targets_payload() -> str | None:
    """Return the optional JSON payload that overrides local A2S targets."""
    raw_payload = os.getenv(DEFAULT_A2S_TARGETS_ENV_VAR)
    if raw_payload is None:
        return None

    normalized = raw_payload.strip()
    return normalized or None


def get_rcon_targets_payload() -> str | None:
    """Return the optional JSON payload that defines live RCON targets."""
    raw_payload = os.getenv(DEFAULT_RCON_TARGETS_ENV_VAR)
    if raw_payload is None:
        return None

    normalized = raw_payload.strip()
    return normalized or None
