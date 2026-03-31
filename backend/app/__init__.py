"""Minimal bootstrap package for the HLL Vietnam Python backend."""

from __future__ import annotations

from importlib import import_module
from typing import Any


_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "build_health_payload": (".payloads", "build_health_payload"),
    "build_server_snapshot": (".snapshots", "build_server_snapshot"),
    "build_snapshot_batch": (".snapshots", "build_snapshot_batch"),
    "create_server": (".main", "create_server"),
    "get_allowed_origins": (".config", "get_allowed_origins"),
    "get_bind_address": (".config", "get_bind_address"),
    "initialize_storage": (".storage", "initialize_storage"),
    "normalize_a2s_server_info": (".normalizers", "normalize_a2s_server_info"),
    "normalize_server_record": (".normalizers", "normalize_server_record"),
    "persist_snapshot_batch": (".storage", "persist_snapshot_batch"),
    "resolve_get_payload": (".routes", "resolve_get_payload"),
    "run": (".main", "run"),
    "utc_now": (".snapshots", "utc_now"),
}


def __getattr__(name: str) -> Any:
    """Resolve public package exports lazily to avoid preloading entrypoint modules."""
    export = _LAZY_EXPORTS.get(name)
    if export is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attribute_name = export
    value = getattr(import_module(module_name, __name__), attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_LAZY_EXPORTS) | set(__all__))


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
