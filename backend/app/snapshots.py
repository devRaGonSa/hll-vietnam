"""Snapshot builders for normalized provisional server data."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Mapping


def build_server_snapshot(
    normalized_record: Mapping[str, object],
    *,
    captured_at: datetime,
) -> dict[str, object]:
    """Build a consistent snapshot payload for one normalized server."""
    timestamp = _as_utc_timestamp(captured_at)
    return {
        "external_server_id": normalized_record.get("external_server_id"),
        "server_name": normalized_record.get("server_name"),
        "status": normalized_record.get("status"),
        "players": normalized_record.get("players"),
        "max_players": normalized_record.get("max_players"),
        "current_map": normalized_record.get("current_map"),
        "region": normalized_record.get("region"),
        "source_name": normalized_record.get("source_name"),
        "snapshot_origin": normalized_record.get("snapshot_origin"),
        "source_ref": normalized_record.get("source_ref"),
        "captured_at": timestamp,
    }


def build_snapshot_batch(
    normalized_records: Iterable[Mapping[str, object]],
    *,
    captured_at: datetime,
) -> list[dict[str, object]]:
    """Build snapshots for a batch captured at the same timestamp."""
    return [
        build_server_snapshot(record, captured_at=captured_at)
        for record in normalized_records
    ]


def utc_now() -> datetime:
    """Return the current UTC timestamp for snapshot capture."""
    return datetime.now(timezone.utc)


def _as_utc_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)

    return value.isoformat().replace("+00:00", "Z")
