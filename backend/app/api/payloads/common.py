"""Shared historical snapshot and explicit fallback compatibility helpers."""

from __future__ import annotations

from ...data_sources import build_historical_runtime_source_policy
from ...historical_snapshot_storage import get_historical_snapshot

def _get_historical_snapshot_record(
    *,
    server_key: str | None,
    snapshot_type: str,
    metric: str | None = None,
    window: str | None = None,
) -> dict[str, object] | None:
    if not server_key:
        return None
    return get_historical_snapshot(
        server_key=server_key,
        snapshot_type=snapshot_type,
        metric=metric,
        window=window,
    )


def _build_historical_snapshot_metadata(snapshot: dict[str, object] | None) -> dict[str, object]:
    if snapshot is None:
        return {
            "snapshot_status": "missing",
            "missing_reason": "snapshot-not-generated",
            "request_path_policy": "read-only-fast-path",
            "generation_policy": "out-of-band-refresh-only",
            "generated_at": None,
            "source_range_start": None,
            "source_range_end": None,
            "is_stale": True,
            "freshness": "stale",
        }
    is_stale = bool(snapshot.get("is_stale", False))
    return {
        "snapshot_status": "ready",
        "missing_reason": None,
        "request_path_policy": "read-only-fast-path",
        "generation_policy": "out-of-band-refresh-only",
        "generated_at": snapshot.get("generated_at"),
        "source_range_start": snapshot.get("source_range_start"),
        "source_range_end": snapshot.get("source_range_end"),
        "is_stale": is_stale,
        "freshness": "stale" if is_stale else "fresh",
    }


def _resolve_historical_fallback_policy(
    *,
    fallback_reason: str,
    operation: str = "historical-read",
) -> dict[str, object]:
    return build_historical_runtime_source_policy(
        operation=operation,
        rcon_status="unsupported",
        fallback_reason=fallback_reason,
    )
