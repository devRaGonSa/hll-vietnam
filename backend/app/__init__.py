"""Minimal bootstrap package for the HLL Vietnam Python backend."""

from .config import get_allowed_origins, get_bind_address
from .main import create_server, run
from .normalizers import normalize_a2s_server_info, normalize_server_record
from .payloads import build_health_payload
from .routes import resolve_get_payload
from .snapshots import build_server_snapshot, build_snapshot_batch, utc_now
from .storage import initialize_storage, persist_snapshot_batch


def collect_server_snapshots(*args: object, **kwargs: object) -> dict[str, object]:
    """Proxy collector access without importing the module during package init."""
    from .collector import collect_server_snapshots as _collect_server_snapshots

    return _collect_server_snapshots(*args, **kwargs)


def fetch_a2s_probe(*args: object, **kwargs: object) -> dict[str, object]:
    """Proxy A2S probe access without importing the collector during package init."""
    from .collector import fetch_a2s_probe as _fetch_a2s_probe

    return _fetch_a2s_probe(*args, **kwargs)


def query_server_info(*args: object, **kwargs: object) -> object:
    """Proxy A2S info queries without importing the module during package init."""
    from .a2s_client import query_server_info as _query_server_info

    return _query_server_info(*args, **kwargs)


def fetch_controlled_server_source() -> tuple[dict[str, object], ...]:
    """Proxy the controlled source without importing the module during package init."""
    from .collector import (
        fetch_controlled_server_source as _fetch_controlled_server_source,
    )

    return tuple(_fetch_controlled_server_source())

__all__ = [
    "build_health_payload",
    "build_server_snapshot",
    "build_snapshot_batch",
    "collect_server_snapshots",
    "create_server",
    "fetch_a2s_probe",
    "fetch_controlled_server_source",
    "get_allowed_origins",
    "get_bind_address",
    "initialize_storage",
    "normalize_a2s_server_info",
    "normalize_server_record",
    "persist_snapshot_batch",
    "query_server_info",
    "resolve_get_payload",
    "run",
    "utc_now",
]
