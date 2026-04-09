"""PostgreSQL-backed persistence for precomputed historical snapshots."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from .config import get_primary_storage_label
from .historical_models import HistoricalSnapshotRecord
from .historical_snapshots import validate_snapshot_identity
from .postgres_utils import connect_postgres_compat, ensure_postgres_migrations_applied


def resolve_historical_snapshot_storage_path(*, db_path: Path | None = None) -> Path:
    """Resolve the logical storage target used by PostgreSQL snapshot persistence."""
    return db_path or Path(get_primary_storage_label())


def initialize_historical_snapshot_storage(*, db_path: Path | None = None) -> Path:
    """Ensure PostgreSQL schema bootstrap exists for historical snapshot storage."""
    resolved_path = resolve_historical_snapshot_storage_path(db_path=db_path)
    ensure_postgres_migrations_applied()
    return resolved_path


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
    """Insert or replace one persisted historical snapshot JSONB payload."""
    normalized_server_key = server_key.strip()
    if not normalized_server_key:
        raise ValueError("server_key is required for historical snapshots.")

    validate_snapshot_identity(snapshot_type=snapshot_type, metric=metric)
    resolved_path = initialize_historical_snapshot_storage(db_path=db_path)
    generated_at_value = _as_utc(generated_at or datetime.now(timezone.utc))
    payload_json = json.dumps(payload, ensure_ascii=True, default=_json_default)
    existing_document = _read_snapshot_document(
        server_key=normalized_server_key,
        snapshot_type=snapshot_type,
        metric=metric,
        window=window,
        db_path=resolved_path,
    )

    if _should_preserve_existing_snapshot(
        incoming_payload=payload,
        snapshot_type=snapshot_type,
        existing_document=existing_document,
    ):
        preserved_payload = existing_document.get("payload") if existing_document else payload
        return HistoricalSnapshotRecord(
            server_key=normalized_server_key,
            snapshot_type=snapshot_type,
            metric=metric,
            window=window,
            payload_json=json.dumps(
                preserved_payload,
                ensure_ascii=True,
                default=_json_default,
            ),
            generated_at=_parse_optional_datetime(existing_document.get("generated_at"))
            if existing_document
            else generated_at_value,
            source_range_start=_parse_optional_datetime(
                existing_document.get("source_range_start")
            )
            if existing_document
            else _as_utc(source_range_start),
            source_range_end=_parse_optional_datetime(existing_document.get("source_range_end"))
            if existing_document
            else _as_utc(source_range_end),
            is_stale=bool(existing_document.get("is_stale", False)) if existing_document else is_stale,
        )

    with _connect(resolved_path) as connection:
        row = connection.execute(
            """
            INSERT INTO historical_snapshot_payloads (
                server_key,
                snapshot_type,
                metric,
                snapshot_window,
                payload_json,
                generated_at,
                source_range_start,
                source_range_end,
                is_stale
            ) VALUES (?, ?, ?, ?, CAST(? AS JSONB), ?, ?, ?, ?)
            ON CONFLICT (server_key, snapshot_type, identity_metric, identity_window) DO UPDATE SET
                payload_json = excluded.payload_json,
                generated_at = excluded.generated_at,
                source_range_start = excluded.source_range_start,
                source_range_end = excluded.source_range_end,
                is_stale = excluded.is_stale,
                updated_at = NOW()
            RETURNING
                server_key,
                snapshot_type,
                metric,
                snapshot_window,
                payload_json,
                generated_at,
                source_range_start,
                source_range_end,
                is_stale
            """,
            (
                normalized_server_key,
                snapshot_type,
                metric,
                window,
                payload_json,
                generated_at_value,
                _as_utc(source_range_start),
                _as_utc(source_range_end),
                is_stale,
            ),
        ).fetchone()
    if row is None:
        raise RuntimeError("Failed to persist historical snapshot.")
    return _build_snapshot_record(row)


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
    resolved_path = resolve_historical_snapshot_storage_path(db_path=db_path)
    with _connect(resolved_path) as connection:
        row = connection.execute(
            """
            SELECT
                server_key,
                snapshot_type,
                metric,
                snapshot_window,
                payload_json,
                generated_at,
                source_range_start,
                source_range_end,
                is_stale
            FROM historical_snapshot_payloads
            WHERE server_key = ?
              AND snapshot_type = ?
              AND identity_metric = COALESCE(?, '')
              AND identity_window = COALESCE(?, '')
            """,
            (server_key, snapshot_type, metric, window),
        ).fetchone()
    if row is None:
        return None

    return _serialize_snapshot_document(row)


def list_historical_snapshots(
    *,
    server_key: str | None = None,
    snapshot_type: str | None = None,
    db_path: Path | None = None,
) -> list[dict[str, object]]:
    """List persisted snapshots for validation and operational inspection."""
    if snapshot_type:
        validate_snapshot_identity(snapshot_type=snapshot_type)

    where_clauses: list[str] = []
    params: list[object] = []
    if server_key:
        where_clauses.append("server_key = ?")
        params.append(server_key)
    if snapshot_type:
        where_clauses.append("snapshot_type = ?")
        params.append(snapshot_type)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    resolved_path = resolve_historical_snapshot_storage_path(db_path=db_path)
    with _connect(resolved_path) as connection:
        rows = connection.execute(
            f"""
            SELECT
                server_key,
                snapshot_type,
                metric,
                snapshot_window,
                generated_at,
                source_range_start,
                source_range_end,
                is_stale
            FROM historical_snapshot_payloads
            {where_sql}
            ORDER BY server_key ASC, snapshot_type ASC, identity_metric ASC, generated_at ASC
            """,
            params,
        ).fetchall()
    return [
        {
            "server_key": row.get("server_key"),
            "snapshot_type": row.get("snapshot_type"),
            "metric": row.get("metric"),
            "window": row.get("snapshot_window"),
            "generated_at": _to_iso_value(row.get("generated_at")),
            "source_range_start": _to_iso_value(row.get("source_range_start")),
            "source_range_end": _to_iso_value(row.get("source_range_end")),
            "is_stale": bool(row.get("is_stale", False)),
        }
        for row in rows
    ]


def _should_preserve_existing_snapshot(
    *,
    incoming_payload: dict[str, object] | list[object],
    snapshot_type: str,
    existing_document: dict[str, object] | None,
) -> bool:
    if not _is_effectively_empty_snapshot_payload(snapshot_type, incoming_payload):
        return False
    if existing_document and not _is_effectively_empty_snapshot_payload(
        snapshot_type,
        existing_document.get("payload"),
    ):
        return True
    return False


def _is_effectively_empty_snapshot_payload(
    snapshot_type: str,
    payload: object,
) -> bool:
    if not isinstance(payload, dict):
        return not payload

    if snapshot_type == "server-summary":
        item = payload.get("item")
        if not isinstance(item, dict):
            return True
        matches_count = item.get("imported_matches_count", item.get("matches_count", 0))
        return int(matches_count or 0) <= 0

    if snapshot_type == "recent-matches":
        items = payload.get("items")
        return not isinstance(items, list) or len(items) == 0

    if snapshot_type in {
        "weekly-leaderboard",
        "monthly-leaderboard",
        "monthly-mvp",
        "monthly-mvp-v2",
    }:
        items = payload.get("items")
        return not isinstance(items, list) or len(items) == 0

    return False


def _read_snapshot_document(
    *,
    server_key: str,
    snapshot_type: str,
    metric: str | None,
    window: str | None,
    db_path: Path,
) -> dict[str, object] | None:
    return get_historical_snapshot(
        server_key=server_key,
        snapshot_type=snapshot_type,
        metric=metric,
        window=window,
        db_path=db_path,
    )


def _connect(db_path: Path) -> object:
    return connect_postgres_compat()


def _build_snapshot_record(row: Mapping[str, object]) -> HistoricalSnapshotRecord:
    payload_json_value = row.get("payload_json")
    return HistoricalSnapshotRecord(
        server_key=str(row["server_key"]),
        snapshot_type=str(row["snapshot_type"]),
        metric=str(row["metric"]) if row.get("metric") is not None else None,
        window=(
            str(row["snapshot_window"])
            if row.get("snapshot_window") is not None
            else None
        ),
        payload_json=(
            payload_json_value
            if isinstance(payload_json_value, str)
            else json.dumps(payload_json_value, ensure_ascii=True, default=_json_default)
        ),
        generated_at=_coerce_datetime(row.get("generated_at")) or datetime.now(timezone.utc),
        source_range_start=_coerce_datetime(row.get("source_range_start")),
        source_range_end=_coerce_datetime(row.get("source_range_end")),
        is_stale=bool(row.get("is_stale", False)),
    )


def _serialize_snapshot_document(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "server_key": row.get("server_key"),
        "snapshot_type": row.get("snapshot_type"),
        "metric": row.get("metric"),
        "window": row.get("snapshot_window"),
        "generated_at": _to_iso_value(row.get("generated_at")),
        "source_range_start": _to_iso_value(row.get("source_range_start")),
        "source_range_end": _to_iso_value(row.get("source_range_end")),
        "is_stale": bool(row.get("is_stale", False)),
        "payload": _decode_payload_value(row.get("payload_json")),
    }


def _decode_payload_value(value: object) -> dict[str, object] | list[object] | None:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        return json.loads(value)
    raise TypeError("Unexpected payload_json value returned from PostgreSQL snapshot storage.")


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return _to_iso(value) or ""
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _as_utc(value).isoformat().replace("+00:00", "Z")


def _to_iso_value(value: object) -> str | None:
    return _to_iso(_coerce_datetime(value))


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _coerce_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return _as_utc(value)
    return _parse_optional_datetime(value)


def _parse_optional_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
