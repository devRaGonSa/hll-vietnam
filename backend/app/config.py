"""Local development configuration for the HLL Vietnam backend bootstrap."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote_plus


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_STORAGE_FILENAME = "hll_vietnam_dev.sqlite3"
DEFAULT_POSTGRES_HOST = "127.0.0.1"
DEFAULT_POSTGRES_PORT = 5432
DEFAULT_POSTGRES_DB = "hll_vietnam"
DEFAULT_POSTGRES_USER = "hll_vietnam"
DEFAULT_POSTGRES_PASSWORD = "hll_vietnam_dev"
DEFAULT_POSTGRES_SSLMODE = "disable"
DEFAULT_POSTGRES_CONNECT_TIMEOUT_SECONDS = 5
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
DEFAULT_SQLITE_WRITER_TIMEOUT_SECONDS = 30.0
DEFAULT_SQLITE_BUSY_TIMEOUT_MS = 30000
DEFAULT_WRITER_LOCK_TIMEOUT_SECONDS = 120.0
DEFAULT_WRITER_LOCK_POLL_INTERVAL_SECONDS = 1.0
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
    """Return the transitional SQLite path used during the staged migration."""
    default_path = Path(__file__).resolve().parent.parent / "data" / DEFAULT_STORAGE_FILENAME
    configured_path = os.getenv("HLL_BACKEND_STORAGE_PATH")
    return Path(configured_path) if configured_path else default_path


def get_postgres_host() -> str:
    """Return the PostgreSQL host used by the staged runtime foundation."""
    return os.getenv("HLL_BACKEND_POSTGRES_HOST", DEFAULT_POSTGRES_HOST).strip()


def get_postgres_port() -> int:
    """Return the PostgreSQL port used by the staged runtime foundation."""
    configured_value = os.getenv(
        "HLL_BACKEND_POSTGRES_PORT",
        str(DEFAULT_POSTGRES_PORT),
    )
    port = int(configured_value)
    if port <= 0:
        raise ValueError("HLL_BACKEND_POSTGRES_PORT must be positive.")
    return port


def get_postgres_database() -> str:
    """Return the PostgreSQL database name used by the staged runtime foundation."""
    database = os.getenv("HLL_BACKEND_POSTGRES_DB", DEFAULT_POSTGRES_DB).strip()
    if not database:
        raise ValueError("HLL_BACKEND_POSTGRES_DB must not be empty.")
    return database


def get_postgres_user() -> str:
    """Return the PostgreSQL user used by the staged runtime foundation."""
    user = os.getenv("HLL_BACKEND_POSTGRES_USER", DEFAULT_POSTGRES_USER).strip()
    if not user:
        raise ValueError("HLL_BACKEND_POSTGRES_USER must not be empty.")
    return user


def get_postgres_password() -> str:
    """Return the PostgreSQL password used by the staged runtime foundation."""
    return os.getenv("HLL_BACKEND_POSTGRES_PASSWORD", DEFAULT_POSTGRES_PASSWORD)


def get_postgres_sslmode() -> str:
    """Return the PostgreSQL sslmode used by the staged runtime foundation."""
    sslmode = os.getenv("HLL_BACKEND_POSTGRES_SSLMODE", DEFAULT_POSTGRES_SSLMODE).strip()
    if not sslmode:
        raise ValueError("HLL_BACKEND_POSTGRES_SSLMODE must not be empty.")
    return sslmode


def get_postgres_connect_timeout_seconds() -> int:
    """Return the PostgreSQL connect timeout used by the staged runtime foundation."""
    configured_value = os.getenv(
        "HLL_BACKEND_POSTGRES_CONNECT_TIMEOUT_SECONDS",
        str(DEFAULT_POSTGRES_CONNECT_TIMEOUT_SECONDS),
    )
    timeout_seconds = int(configured_value)
    if timeout_seconds <= 0:
        raise ValueError("HLL_BACKEND_POSTGRES_CONNECT_TIMEOUT_SECONDS must be positive.")
    return timeout_seconds


def get_postgres_dsn() -> str:
    """Return the PostgreSQL DSN, preferring the explicit override when provided."""
    configured_dsn = os.getenv("HLL_BACKEND_POSTGRES_DSN")
    if configured_dsn and configured_dsn.strip():
        return configured_dsn.strip()

    user = quote_plus(get_postgres_user())
    password = quote_plus(get_postgres_password())
    host = get_postgres_host()
    port = get_postgres_port()
    database = quote_plus(get_postgres_database())
    sslmode = quote_plus(get_postgres_sslmode())
    connect_timeout = get_postgres_connect_timeout_seconds()
    return (
        f"postgresql://{user}:{password}@{host}:{port}/{database}"
        f"?sslmode={sslmode}&connect_timeout={connect_timeout}"
    )


def get_postgres_connection_settings() -> dict[str, object]:
    """Return the PostgreSQL runtime contract used by the shared connection layer."""
    return {
        "dsn": get_postgres_dsn(),
        "host": get_postgres_host(),
        "port": get_postgres_port(),
        "database": get_postgres_database(),
        "user": get_postgres_user(),
        "password": get_postgres_password(),
        "sslmode": get_postgres_sslmode(),
        "connect_timeout_seconds": get_postgres_connect_timeout_seconds(),
        "sqlite_storage_path": str(get_storage_path()),
        "sqlite_runtime_status": "transitional",
        "sqlite_env_status": {
            "HLL_BACKEND_STORAGE_PATH": "transitional",
            "HLL_BACKEND_SQLITE_WRITER_TIMEOUT_SECONDS": "deprecated-but-tolerated",
            "HLL_BACKEND_SQLITE_BUSY_TIMEOUT_MS": "deprecated-but-tolerated",
            "HLL_BACKEND_WRITER_LOCK_TIMEOUT_SECONDS": "deprecated-but-tolerated",
            "HLL_BACKEND_WRITER_LOCK_POLL_INTERVAL_SECONDS": "deprecated-but-tolerated",
        },
        "migration_runner_status": "deferred-to-task-133",
    }


def get_postgres_migrations_path() -> Path:
    """Return the stable repository location for PostgreSQL SQL-first migrations."""
    return Path(__file__).resolve().parent.parent / "db" / "migrations"


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
