"""File-based persistence for precomputed historical snapshots."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .config import get_storage_path
from .historical_models import HistoricalSnapshotRecord
from .historical_snapshots import validate_snapshot_identity
from .historical_storage import initialize_historical_storage


SNAPSHOT_DIRECTORY_NAME = "snapshots"


def initialize_historical_snapshot_storage(*, db_path: Path | None = None) -> Path:
    """Create the snapshot directory used by precomputed historical payloads."""
    resolved_db_path = initialize_historical_storage(db_path=db_path or get_storage_path())
    snapshots_root = resolved_db_path.parent / SNAPSHOT_DIRECTORY_NAME
    snapshots_root.mkdir(parents=True, exist_ok=True)
    return snapshots_root


def persist_historical_snapshot(
    *,
    server_key: str,
    snapshot_type: str,
    payload: dict[str, object] | list[object],
    metric: str | None = None,
    window: str | None = None,
    generated_at: datetime | None = None,
    source_range_start: datetime | None = None,
    source_range_end: datetime | None = None,
    is_stale: bool = False,
    db_path: Path | None = None,
) -> HistoricalSnapshotRecord:
    """Insert or replace one persisted historical snapshot JSON file."""
    normalized_server_key = server_key.strip()
    if not normalized_server_key:
        raise ValueError("server_key is required for historical snapshots.")

    validate_snapshot_identity(snapshot_type=snapshot_type, metric=metric)
    snapshots_root = initialize_historical_snapshot_storage(db_path=db_path)
    generated_at_value = _as_utc(generated_at or datetime.now(timezone.utc))
    payload_json = json.dumps(payload, ensure_ascii=True)
    snapshot_path = _build_snapshot_path(
        snapshots_root=snapshots_root,
        server_key=normalized_server_key,
        snapshot_type=snapshot_type,
        metric=metric,
    )
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)

    snapshot_document = {
        "server_key": normalized_server_key,
        "snapshot_type": snapshot_type,
        "metric": metric,
        "window": window,
        "generated_at": _to_iso(generated_at_value),
        "source_range_start": _to_iso(source_range_start),
        "source_range_end": _to_iso(source_range_end),
        "is_stale": is_stale,
        "payload": payload,
    }
    snapshot_path.write_text(
        json.dumps(snapshot_document, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )

    return HistoricalSnapshotRecord(
        server_key=normalized_server_key,
        snapshot_type=snapshot_type,
        metric=metric,
        window=window,
        payload_json=payload_json,
        generated_at=generated_at_value,
        source_range_start=_as_utc(source_range_start),
        source_range_end=_as_utc(source_range_end),
        is_stale=is_stale,
    )


def persist_historical_snapshot_batch(
    snapshots: list[dict[str, object]],
    *,
    db_path: Path | None = None,
) -> list[HistoricalSnapshotRecord]:
    """Persist a batch of snapshots generated in one runner cycle."""
    records: list[HistoricalSnapshotRecord] = []
    for snapshot in snapshots:
        records.append(
            persist_historical_snapshot(
                server_key=str(snapshot["server_key"]),
                snapshot_type=str(snapshot["snapshot_type"]),
                payload=snapshot["payload"],
                metric=snapshot.get("metric"),
                window=snapshot.get("window"),
                generated_at=snapshot.get("generated_at"),
                source_range_start=snapshot.get("source_range_start"),
                source_range_end=snapshot.get("source_range_end"),
                is_stale=bool(snapshot.get("is_stale", False)),
                db_path=db_path,
            )
        )
    return records


def get_historical_snapshot(
    *,
    server_key: str,
    snapshot_type: str,
    metric: str | None = None,
    window: str | None = None,
    db_path: Path | None = None,
) -> dict[str, object] | None:
    """Return one persisted snapshot and decoded payload, if present."""
    validate_snapshot_identity(snapshot_type=snapshot_type, metric=metric)
    snapshots_root = initialize_historical_snapshot_storage(db_path=db_path)
    snapshot_path = _build_snapshot_path(
        snapshots_root=snapshots_root,
        server_key=server_key,
        snapshot_type=snapshot_type,
        metric=metric,
    )
    if not snapshot_path.exists():
        return None

    document = json.loads(snapshot_path.read_text(encoding="utf-8"))
    return {
        "server_key": document.get("server_key"),
        "snapshot_type": document.get("snapshot_type"),
        "metric": document.get("metric"),
        "window": document.get("window"),
        "generated_at": document.get("generated_at"),
        "source_range_start": document.get("source_range_start"),
        "source_range_end": document.get("source_range_end"),
        "is_stale": bool(document.get("is_stale", False)),
        "payload": document.get("payload"),
    }


def list_historical_snapshots(
    *,
    server_key: str | None = None,
    snapshot_type: str | None = None,
    db_path: Path | None = None,
) -> list[dict[str, object]]:
    """List persisted snapshots for validation and operational inspection."""
    snapshots_root = initialize_historical_snapshot_storage(db_path=db_path)
    if snapshot_type:
        validate_snapshot_identity(snapshot_type=snapshot_type)

    rows: list[dict[str, object]] = []
    for snapshot_path in snapshots_root.glob("*/*.json"):
        try:
            document = json.loads(snapshot_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        if server_key and document.get("server_key") != server_key:
            continue
        if snapshot_type and document.get("snapshot_type") != snapshot_type:
            continue

        rows.append(
            {
                "server_key": document.get("server_key"),
                "snapshot_type": document.get("snapshot_type"),
                "metric": document.get("metric"),
                "window": document.get("window"),
                "generated_at": document.get("generated_at"),
                "source_range_start": document.get("source_range_start"),
                "source_range_end": document.get("source_range_end"),
                "is_stale": bool(document.get("is_stale", False)),
            }
        )

    return sorted(
        rows,
        key=lambda item: (
            str(item.get("server_key") or ""),
            str(item.get("snapshot_type") or ""),
            str(item.get("metric") or ""),
            str(item.get("generated_at") or ""),
        ),
    )


def _build_snapshot_path(
    *,
    snapshots_root: Path,
    server_key: str,
    snapshot_type: str,
    metric: str | None,
) -> Path:
    return snapshots_root / server_key / _build_snapshot_filename(
        snapshot_type=snapshot_type,
        metric=metric,
    )


def _build_snapshot_filename(*, snapshot_type: str, metric: str | None) -> str:
    if snapshot_type == "server-summary":
        return "server-summary.json"
    if snapshot_type == "recent-matches":
        return "recent-matches.json"
    if snapshot_type == "weekly-leaderboard":
        metric_suffix = "matches-over-100-kills" if metric == "matches_over_100_kills" else _slugify(metric or "unknown")
        return f"weekly-{metric_suffix}.json"
    metric_suffix = _slugify(metric or "")
    base_name = _slugify(snapshot_type)
    return f"{base_name}-{metric_suffix}.json" if metric_suffix else f"{base_name}.json"


def _slugify(value: str) -> str:
    return value.strip().replace("_", "-").replace(" ", "-").lower()


def _to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _as_utc(value).isoformat().replace("+00:00", "Z")


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
