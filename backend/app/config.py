"""Local development configuration for the HLL Vietnam backend bootstrap."""

from __future__ import annotations

import os
from pathlib import Path


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_STORAGE_FILENAME = "hll_vietnam_dev.sqlite3"
DEFAULT_REFRESH_INTERVAL_SECONDS = 300
DEFAULT_LIVE_DATA_SOURCE = "rcon"
DEFAULT_HISTORICAL_DATA_SOURCE = "rcon"
DEFAULT_RCON_TIMEOUT_SECONDS = 20.0
DEFAULT_HISTORICAL_CRCON_PAGE_SIZE = 50
DEFAULT_HISTORICAL_CRCON_TIMEOUT_SECONDS = 15.0
DEFAULT_HISTORICAL_CRCON_DETAIL_WORKERS = 8
DEFAULT_HISTORICAL_CRCON_REQUEST_RETRIES = 3
DEFAULT_HISTORICAL_CRCON_RETRY_DELAY_SECONDS = 0.5
DEFAULT_HISTORICAL_REFRESH_INTERVAL_SECONDS = 1800
DEFAULT_HISTORICAL_REFRESH_OVERLAP_HOURS = 12
DEFAULT_HISTORICAL_SNAPSHOT_REFRESH_INTERVAL_SECONDS = 900
DEFAULT_HISTORICAL_REFRESH_MAX_RETRIES = 2
DEFAULT_HISTORICAL_REFRESH_RETRY_DELAY_SECONDS = 30
DEFAULT_HISTORICAL_FULL_SNAPSHOT_EVERY_RUNS = 4
DEFAULT_HISTORICAL_ELO_MMR_REBUILD_INTERVAL_MINUTES = 180
DEFAULT_HISTORICAL_ELO_MMR_MIN_NEW_SAMPLES = 12
DEFAULT_HISTORICAL_WEEKLY_FALLBACK_MIN_MATCHES = 3
DEFAULT_HISTORICAL_WEEKLY_FALLBACK_MAX_WEEKDAY = 2
DEFAULT_PLAYER_EVENT_REFRESH_INTERVAL_SECONDS = 1800
DEFAULT_PLAYER_EVENT_REFRESH_OVERLAP_HOURS = 12
DEFAULT_PLAYER_EVENT_REFRESH_MAX_RETRIES = 2
DEFAULT_PLAYER_EVENT_REFRESH_RETRY_DELAY_SECONDS = 30
DEFAULT_RCON_HISTORICAL_CAPTURE_INTERVAL_SECONDS = 600
DEFAULT_RCON_HISTORICAL_CAPTURE_MAX_RETRIES = 2
DEFAULT_RCON_HISTORICAL_CAPTURE_RETRY_DELAY_SECONDS = 15
DEFAULT_RCON_BACKFILL_CHUNK_HOURS = 6
DEFAULT_RCON_BACKFILL_SLEEP_SECONDS = 1.0
DEFAULT_RCON_BACKFILL_MAX_DAYS_BACK = 45
DEFAULT_RECENT_MATCHES_KEEP = 100
DEFAULT_ADMIN_LOG_NONCRITICAL_RETENTION_DAYS = 30
DEFAULT_ADMIN_LOG_CRITICAL_RETENTION_DAYS = 90
DEFAULT_SERVER_SNAPSHOT_RETENTION_DAYS = 14
DEFAULT_DB_MAINTENANCE_BATCH_SIZE = 5000
DEFAULT_DB_MAINTENANCE_ENABLED = False
DEFAULT_DB_MAINTENANCE_INTERVAL_SECONDS = 43200
DEFAULT_SQLITE_WRITER_TIMEOUT_SECONDS = 30.0
DEFAULT_SQLITE_BUSY_TIMEOUT_MS = 30000
DEFAULT_WRITER_LOCK_TIMEOUT_SECONDS = 120.0
DEFAULT_WRITER_LOCK_POLL_INTERVAL_SECONDS = 1.0
DEFAULT_ALLOWED_ORIGINS = (
    "null",
    "http://127.0.0.1",
    "http://127.0.0.1:5500",
    "http://127.0.0.1:8080",
    "http://localhost",
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


def get_database_url() -> str | None:
    """Return the optional PostgreSQL URL for migrated backend storage domains."""
    configured_url = os.getenv("HLL_BACKEND_DATABASE_URL")
    if configured_url is None:
        return None
    normalized_url = configured_url.strip()
    return normalized_url or None


def use_postgres_rcon_storage(*, explicit_sqlite_path: Path | None = None) -> bool:
    """Return whether phase-1 RCON storage should use PostgreSQL."""
    return explicit_sqlite_path is None and get_database_url() is not None


def get_sqlite_writer_timeout_seconds() -> float:
    """Return the SQLite connection timeout shared by writer-capable storage layers."""
    configured_value = os.getenv(
        "HLL_BACKEND_SQLITE_WRITER_TIMEOUT_SECONDS",
        str(DEFAULT_SQLITE_WRITER_TIMEOUT_SECONDS),
    )
    timeout_seconds = float(configured_value)
    if timeout_seconds <= 0:
        raise ValueError("HLL_BACKEND_SQLITE_WRITER_TIMEOUT_SECONDS must be positive.")
    return timeout_seconds


def get_sqlite_busy_timeout_ms() -> int:
    """Return the SQLite busy_timeout shared by writer-capable storage layers."""
    configured_value = os.getenv(
        "HLL_BACKEND_SQLITE_BUSY_TIMEOUT_MS",
        str(DEFAULT_SQLITE_BUSY_TIMEOUT_MS),
    )
    busy_timeout_ms = int(configured_value)
    if busy_timeout_ms <= 0:
        raise ValueError("HLL_BACKEND_SQLITE_BUSY_TIMEOUT_MS must be positive.")
    return busy_timeout_ms


def get_writer_lock_timeout_seconds() -> float:
    """Return how long writer jobs should wait for the shared backend writer lock."""
    configured_value = os.getenv(
        "HLL_BACKEND_WRITER_LOCK_TIMEOUT_SECONDS",
        str(DEFAULT_WRITER_LOCK_TIMEOUT_SECONDS),
    )
    timeout_seconds = float(configured_value)
    if timeout_seconds < 0:
        raise ValueError("HLL_BACKEND_WRITER_LOCK_TIMEOUT_SECONDS must be zero or positive.")
    return timeout_seconds


def get_writer_lock_poll_interval_seconds() -> float:
    """Return how often writer jobs should poll the shared backend writer lock."""
    configured_value = os.getenv(
        "HLL_BACKEND_WRITER_LOCK_POLL_INTERVAL_SECONDS",
        str(DEFAULT_WRITER_LOCK_POLL_INTERVAL_SECONDS),
    )
    poll_interval_seconds = float(configured_value)
    if poll_interval_seconds <= 0:
        raise ValueError(
            "HLL_BACKEND_WRITER_LOCK_POLL_INTERVAL_SECONDS must be positive."
        )
    return poll_interval_seconds


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
    return _read_int_env(
        "HLL_HISTORICAL_SNAPSHOT_REFRESH_INTERVAL_SECONDS",
        os.getenv(
            "HLL_HISTORICAL_REFRESH_INTERVAL_SECONDS",
            str(DEFAULT_HISTORICAL_SNAPSHOT_REFRESH_INTERVAL_SECONDS),
        ),
        minimum=1,
    )


def _read_int_env(name: str, default_value: str, *, minimum: int) -> int:
    """Read one integer env var and keep validation errors actionable."""
    configured_value = os.getenv(name, default_value)
    try:
        value = int(configured_value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be an integer.") from error
    if value < minimum:
        qualifier = "positive" if minimum == 1 else f"at least {minimum}"
        raise ValueError(f"{name} must be {qualifier}.")
    return value


def _read_float_env(name: str, default_value: str, *, minimum: float) -> float:
    """Read one float env var and keep validation errors actionable."""
    configured_value = os.getenv(name, default_value)
    try:
        value = float(configured_value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be a number.") from error
    if value < minimum:
        qualifier = "zero or positive" if minimum == 0 else f"at least {minimum}"
        raise ValueError(f"{name} must be {qualifier}.")
    return value


def get_historical_refresh_overlap_hours() -> int:
    """Return the overlap window used by incremental historical refreshes."""
    configured_value = os.getenv(
        "HLL_HISTORICAL_REFRESH_OVERLAP_HOURS",
        str(DEFAULT_HISTORICAL_REFRESH_OVERLAP_HOURS),
    )
    overlap_hours = int(configured_value)
    if overlap_hours < 0:
        raise ValueError("HLL_HISTORICAL_REFRESH_OVERLAP_HOURS must be zero or positive.")

    return overlap_hours


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
    return _read_int_env(
        "HLL_HISTORICAL_REFRESH_MAX_RETRIES",
        str(DEFAULT_HISTORICAL_REFRESH_MAX_RETRIES),
        minimum=0,
    )


def get_historical_refresh_retry_delay_seconds() -> float:
    """Return the wait time between historical refresh retries."""
    return _read_float_env(
        "HLL_HISTORICAL_REFRESH_RETRY_DELAY_SECONDS",
        str(DEFAULT_HISTORICAL_REFRESH_RETRY_DELAY_SECONDS),
        minimum=0,
    )


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


def get_historical_elo_mmr_rebuild_interval_minutes() -> int:
    """Return the minimum minutes between automatic Elo/MMR rebuilds."""
    configured_value = os.getenv(
        "HLL_HISTORICAL_ELO_MMR_REBUILD_INTERVAL_MINUTES",
        str(DEFAULT_HISTORICAL_ELO_MMR_REBUILD_INTERVAL_MINUTES),
    )
    interval_minutes = int(configured_value)
    if interval_minutes <= 0:
        raise ValueError("HLL_HISTORICAL_ELO_MMR_REBUILD_INTERVAL_MINUTES must be positive.")
    return interval_minutes


def get_historical_elo_mmr_min_new_samples() -> int:
    """Return the minimum new RCON samples required for an automatic Elo/MMR rebuild."""
    configured_value = os.getenv(
        "HLL_HISTORICAL_ELO_MMR_MIN_NEW_SAMPLES",
        str(DEFAULT_HISTORICAL_ELO_MMR_MIN_NEW_SAMPLES),
    )
    min_samples = int(configured_value)
    if min_samples <= 0:
        raise ValueError("HLL_HISTORICAL_ELO_MMR_MIN_NEW_SAMPLES must be positive.")
    return min_samples


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


def get_player_event_refresh_overlap_hours() -> int:
    """Return the overlap window used by player event refresh runs."""
    configured_value = os.getenv(
        "HLL_PLAYER_EVENT_REFRESH_OVERLAP_HOURS",
        str(DEFAULT_PLAYER_EVENT_REFRESH_OVERLAP_HOURS),
    )
    overlap_hours = int(configured_value)
    if overlap_hours < 0:
        raise ValueError("HLL_PLAYER_EVENT_REFRESH_OVERLAP_HOURS must be zero or positive.")
    return overlap_hours


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


def get_rcon_historical_capture_interval_seconds() -> int:
    """Return the default interval used by the prospective RCON capture loop."""
    configured_value = os.getenv(
        "HLL_RCON_HISTORICAL_CAPTURE_INTERVAL_SECONDS",
        str(DEFAULT_RCON_HISTORICAL_CAPTURE_INTERVAL_SECONDS),
    )
    interval_seconds = int(configured_value)
    if interval_seconds <= 0:
        raise ValueError("HLL_RCON_HISTORICAL_CAPTURE_INTERVAL_SECONDS must be positive.")
    return interval_seconds


def get_rcon_historical_capture_max_retries() -> int:
    """Return the retry count used by the prospective RCON capture loop."""
    configured_value = os.getenv(
        "HLL_RCON_HISTORICAL_CAPTURE_MAX_RETRIES",
        str(DEFAULT_RCON_HISTORICAL_CAPTURE_MAX_RETRIES),
    )
    max_retries = int(configured_value)
    if max_retries < 0:
        raise ValueError("HLL_RCON_HISTORICAL_CAPTURE_MAX_RETRIES must be zero or positive.")
    return max_retries


def get_rcon_historical_capture_retry_delay_seconds() -> int:
    """Return the wait time between failed prospective RCON capture attempts."""
    configured_value = os.getenv(
        "HLL_RCON_HISTORICAL_CAPTURE_RETRY_DELAY_SECONDS",
        str(DEFAULT_RCON_HISTORICAL_CAPTURE_RETRY_DELAY_SECONDS),
    )
    retry_delay_seconds = int(configured_value)
    if retry_delay_seconds < 0:
        raise ValueError(
            "HLL_RCON_HISTORICAL_CAPTURE_RETRY_DELAY_SECONDS must be zero or positive."
        )
    return retry_delay_seconds


def get_rcon_backfill_chunk_hours() -> int:
    """Return the AdminLog backfill chunk size in hours."""
    return _read_int_env(
        "HLL_RCON_BACKFILL_CHUNK_HOURS",
        str(DEFAULT_RCON_BACKFILL_CHUNK_HOURS),
        minimum=1,
    )


def get_rcon_backfill_sleep_seconds() -> float:
    """Return the delay between AdminLog backfill RCON requests."""
    return _read_float_env(
        "HLL_RCON_BACKFILL_SLEEP_SECONDS",
        str(DEFAULT_RCON_BACKFILL_SLEEP_SECONDS),
        minimum=0,
    )


def get_rcon_backfill_max_days_back() -> int:
    """Return the maximum AdminLog backfill lookback horizon in days."""
    return _read_int_env(
        "HLL_RCON_BACKFILL_MAX_DAYS_BACK",
        str(DEFAULT_RCON_BACKFILL_MAX_DAYS_BACK),
        minimum=1,
    )


def get_recent_matches_keep() -> int:
    """Return how many recent closed materialized matches maintenance must protect."""
    return _read_int_env(
        "HLL_RECENT_MATCHES_KEEP",
        str(DEFAULT_RECENT_MATCHES_KEEP),
        minimum=1,
    )


def get_admin_log_noncritical_retention_days() -> int:
    """Return retention days for non-critical AdminLog events."""
    return _read_int_env(
        "HLL_ADMIN_LOG_NONCRITICAL_RETENTION_DAYS",
        str(DEFAULT_ADMIN_LOG_NONCRITICAL_RETENTION_DAYS),
        minimum=1,
    )


def get_admin_log_critical_retention_days() -> int:
    """Return retention days for critical AdminLog events."""
    return _read_int_env(
        "HLL_ADMIN_LOG_CRITICAL_RETENTION_DAYS",
        str(DEFAULT_ADMIN_LOG_CRITICAL_RETENTION_DAYS),
        minimum=1,
    )


def get_server_snapshot_retention_days() -> int:
    """Return retention days for live server snapshots."""
    return _read_int_env(
        "HLL_SERVER_SNAPSHOT_RETENTION_DAYS",
        str(DEFAULT_SERVER_SNAPSHOT_RETENTION_DAYS),
        minimum=1,
    )


def get_db_maintenance_batch_size() -> int:
    """Return the delete batch size used by database maintenance."""
    return _read_int_env(
        "HLL_DB_MAINTENANCE_BATCH_SIZE",
        str(DEFAULT_DB_MAINTENANCE_BATCH_SIZE),
        minimum=1,
    )


def get_db_maintenance_enabled() -> bool:
    """Return whether scheduled database maintenance is enabled."""
    normalized = os.getenv(
        "HLL_DB_MAINTENANCE_ENABLED",
        "true" if DEFAULT_DB_MAINTENANCE_ENABLED else "false",
    ).strip().lower()
    return normalized in {"1", "true", "yes", "on"}


def get_db_maintenance_interval_seconds() -> int:
    """Return the scheduled database maintenance interval in seconds."""
    return _read_int_env(
        "HLL_DB_MAINTENANCE_INTERVAL_SECONDS",
        str(DEFAULT_DB_MAINTENANCE_INTERVAL_SECONDS),
        minimum=1,
    )


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
