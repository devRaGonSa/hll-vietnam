"""PostgreSQL-backed persistence for provisional server snapshots."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping

from .config import get_primary_storage_label
from .postgres_utils import connect_postgres_compat, ensure_postgres_migrations_applied


DEFAULT_GAME_SOURCE = {
    "slug": "current-hll",
    "display_name": "Current Hell Let Loose",
    "provider_kind": "development",
}
SUMMARY_SNAPSHOT_LIMIT = 6


def resolve_storage_path(*, db_path: Path | None = None) -> Path:
    """Resolve the logical storage target used by live snapshot persistence."""
    return db_path or Path(get_primary_storage_label())


def initialize_storage(*, db_path: Path | None = None) -> Path:
    """Ensure PostgreSQL schema bootstrap exists for live snapshot persistence."""
    resolved_path = resolve_storage_path(db_path=db_path)
    ensure_postgres_migrations_applied()
    with _connect(resolved_path) as connection:
        _ensure_server_snapshot_columns(connection)

    return resolved_path


def persist_snapshot_batch(
    snapshots: Iterable[Mapping[str, object]],
    *,
    source_name: str,
    captured_at: str,
    game_source: Mapping[str, str] | None = None,
    db_path: Path | None = None,
) -> dict[str, object]:
    """Persist a batch of normalized snapshots into local SQLite storage."""
    resolved_path = initialize_storage(db_path=db_path)
    source_definition = dict(DEFAULT_GAME_SOURCE)
    if game_source is not None:
        source_definition.update(game_source)

    persisted = 0
    with _connect(resolved_path) as connection:
        game_source_id = _upsert_game_source(connection, source_definition)
        for snapshot in snapshots:
            server_id = _upsert_server(
                connection,
                game_source_id=game_source_id,
                snapshot=snapshot,
                captured_at=captured_at,
            )
            connection.execute(
                """
                INSERT INTO server_snapshots (
                    server_id,
                    captured_at,
                    status,
                    players,
                    max_players,
                    current_map,
                    source_name,
                    snapshot_origin,
                    source_ref,
                    raw_payload_ref
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    server_id,
                    captured_at,
                    snapshot.get("status"),
                    snapshot.get("players"),
                    snapshot.get("max_players"),
                    snapshot.get("current_map"),
                    snapshot.get("source_name") or source_name,
                    snapshot.get("snapshot_origin"),
                    snapshot.get("source_ref"),
                    None,
                ),
            )
            persisted += 1

    return {
        "db_path": str(resolved_path),
        "captured_at": captured_at,
        "persisted_snapshots": persisted,
        "game_source_slug": source_definition["slug"],
    }


def list_latest_snapshots(*, db_path: Path | None = None) -> list[dict[str, object]]:
    """Return the latest persisted snapshot for each known server."""
    resolved_path = resolve_storage_path(db_path=db_path)
    with _connect_readonly(resolved_path) as connection:
        rows = connection.execute(
            """
            SELECT
                servers.id AS server_id,
                servers.external_server_id,
                servers.server_name,
                servers.region,
                game_sources.slug AS context,
                server_snapshots.source_name,
                server_snapshots.snapshot_origin,
                server_snapshots.source_ref,
                server_snapshots.captured_at,
                server_snapshots.status,
                server_snapshots.players,
                server_snapshots.max_players,
                server_snapshots.current_map
            FROM servers
            INNER JOIN game_sources
                ON game_sources.id = servers.game_source_id
            INNER JOIN server_snapshots
                ON server_snapshots.server_id = servers.id
            INNER JOIN (
                SELECT server_id, MAX(captured_at) AS latest_captured_at
                FROM server_snapshots
                GROUP BY server_id
            ) AS latest
                ON latest.server_id = server_snapshots.server_id
                AND latest.latest_captured_at = server_snapshots.captured_at
            ORDER BY servers.server_name ASC
            """
        ).fetchall()
        items = [_serialize_snapshot_row(row) for row in rows]
        return _attach_history_summaries(connection, items)


def list_snapshot_history(
    *,
    db_path: Path | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    """Return recent persisted snapshots across all servers."""
    resolved_path = resolve_storage_path(db_path=db_path)
    with _connect_readonly(resolved_path) as connection:
        rows = connection.execute(
            """
            SELECT
                servers.id AS server_id,
                servers.external_server_id,
                servers.server_name,
                servers.region,
                game_sources.slug AS context,
                server_snapshots.source_name,
                server_snapshots.snapshot_origin,
                server_snapshots.source_ref,
                server_snapshots.captured_at,
                server_snapshots.status,
                server_snapshots.players,
                server_snapshots.max_players,
                server_snapshots.current_map
            FROM server_snapshots
            INNER JOIN servers
                ON servers.id = server_snapshots.server_id
            INNER JOIN game_sources
                ON game_sources.id = servers.game_source_id
            ORDER BY server_snapshots.captured_at DESC, servers.server_name ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [_serialize_snapshot_row(row) for row in rows]


def list_server_history(
    server_id: str,
    *,
    db_path: Path | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    """Return recent history for one server by numeric id or external id."""
    resolved_path = resolve_storage_path(db_path=db_path)
    server_filter, server_value = _build_server_filter(server_id)
    with _connect_readonly(resolved_path) as connection:
        rows = connection.execute(
            f"""
            SELECT
                servers.id AS server_id,
                servers.external_server_id,
                servers.server_name,
                servers.region,
                game_sources.slug AS context,
                server_snapshots.source_name,
                server_snapshots.snapshot_origin,
                server_snapshots.source_ref,
                server_snapshots.captured_at,
                server_snapshots.status,
                server_snapshots.players,
                server_snapshots.max_players,
                server_snapshots.current_map
            FROM server_snapshots
            INNER JOIN servers
                ON servers.id = server_snapshots.server_id
            INNER JOIN game_sources
                ON game_sources.id = servers.game_source_id
            WHERE {server_filter} = ?
            ORDER BY server_snapshots.captured_at DESC
            LIMIT ?
            """,
            (server_value, limit),
        ).fetchall()
    return [_serialize_snapshot_row(row) for row in rows]


def _connect(db_path: Path) -> object:
    return connect_postgres_compat()


def _connect_readonly(db_path: Path) -> object:
    return connect_postgres_compat()


def _upsert_game_source(
    connection: object,
    game_source: Mapping[str, str],
) -> int:
    connection.execute(
        """
        INSERT INTO game_sources (slug, display_name, provider_kind, is_active)
        VALUES (?, ?, ?, TRUE)
        ON CONFLICT(slug) DO UPDATE SET
            display_name = excluded.display_name,
            provider_kind = excluded.provider_kind,
            is_active = TRUE,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            game_source["slug"],
            game_source["display_name"],
            game_source["provider_kind"],
        ),
    )
    row = connection.execute(
        "SELECT id FROM game_sources WHERE slug = ?",
        (game_source["slug"],),
    ).fetchone()
    if row is None:
        raise RuntimeError("Failed to resolve game source during snapshot persistence.")

    return int(row["id"])


def _upsert_server(
    connection: object,
    *,
    game_source_id: int,
    snapshot: Mapping[str, object],
    captured_at: str,
) -> int:
    external_server_id = snapshot.get("external_server_id")
    if not isinstance(external_server_id, str) or not external_server_id.strip():
        external_server_id = _build_fallback_external_id(snapshot)

    server_name = str(snapshot.get("server_name") or "Unknown server")
    region = snapshot.get("region")

    connection.execute(
        """
        INSERT INTO servers (
            game_source_id,
            external_server_id,
            server_name,
            region,
            first_seen_at,
            last_seen_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(game_source_id, external_server_id) DO UPDATE SET
            server_name = excluded.server_name,
            region = excluded.region,
            last_seen_at = excluded.last_seen_at,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            game_source_id,
            external_server_id,
            server_name,
            region,
            captured_at,
            captured_at,
        ),
    )
    row = connection.execute(
        """
        SELECT id
        FROM servers
        WHERE game_source_id = ? AND external_server_id = ?
        """,
        (game_source_id, external_server_id),
    ).fetchone()
    if row is None:
        raise RuntimeError("Failed to resolve server during snapshot persistence.")

    return int(row["id"])


def _build_fallback_external_id(snapshot: Mapping[str, object]) -> str:
    server_name = str(snapshot.get("server_name") or "unknown-server")
    normalized = "".join(
        character.lower() if character.isalnum() else "-"
        for character in server_name
    )
    compact = "-".join(part for part in normalized.split("-") if part)
    return compact or "unknown-server"


def _ensure_server_snapshot_columns(connection: object) -> None:
    connection.execute(
        """
        UPDATE server_snapshots
        SET snapshot_origin = CASE
            WHEN source_name = 'controlled-placeholder' THEN 'controlled-fallback'
            WHEN source_name LIKE '%a2s%' THEN 'real-a2s'
            ELSE 'unknown'
        END
        WHERE snapshot_origin IS NULL OR snapshot_origin = ''
        """
    )
    connection.execute(
        """
        UPDATE server_snapshots
        SET source_ref = source_name
        WHERE source_ref IS NULL OR source_ref = ''
        """
    )
    _backfill_registered_a2s_source_refs(connection)


def _backfill_registered_a2s_source_refs(connection: object) -> None:
    from .server_targets import load_a2s_targets

    for target in load_a2s_targets():
        if not target.external_server_id:
            continue

        connection.execute(
            """
            UPDATE server_snapshots
            SET source_ref = ?
            WHERE snapshot_origin = 'real-a2s'
              AND source_ref = source_name
              AND server_id IN (
                  SELECT id
                  FROM servers
                  WHERE external_server_id = ?
              )
            """,
            (
                f"a2s://{target.host}:{target.query_port}",
                target.external_server_id,
            ),
        )


def _serialize_snapshot_row(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "server_id": row["server_id"],
        "external_server_id": row["external_server_id"],
        "server_name": row["server_name"],
        "region": row["region"],
        "context": row["context"],
        "source_name": row["source_name"],
        "snapshot_origin": row["snapshot_origin"],
        "source_ref": row["source_ref"],
        "captured_at": row["captured_at"],
        "status": row["status"],
        "players": row["players"],
        "max_players": row["max_players"],
        "current_map": row["current_map"],
    }


def _attach_history_summaries(
    connection: object,
    items: list[dict[str, object]],
) -> list[dict[str, object]]:
    enriched_items: list[dict[str, object]] = []
    for item in items:
        enriched = dict(item)
        enriched["history_summary"] = _build_history_summary(
            connection,
            int(item["server_id"]),
        )
        enriched_items.append(enriched)

    return enriched_items


def _build_history_summary(
    connection: object,
    server_id: int,
) -> dict[str, object]:
    rows = connection.execute(
        """
        SELECT
            captured_at,
            status,
            players
        FROM server_snapshots
        WHERE server_id = ?
        ORDER BY captured_at DESC
        LIMIT ?
        """,
        (server_id, SUMMARY_SNAPSHOT_LIMIT),
    ).fetchall()
    return _summarize_history_rows(rows)


def _summarize_history_rows(rows: list[Mapping[str, object]]) -> dict[str, object]:
    capture_count = len(rows)
    player_values = [
        int(row["players"])
        for row in rows
        if row["players"] is not None
    ]
    online_rows = [row for row in rows if row["status"] == "online"]
    latest_captured_at = str(rows[0]["captured_at"]) if rows else None
    last_seen_online_at = str(online_rows[0]["captured_at"]) if online_rows else None

    return {
        "window_size": SUMMARY_SNAPSHOT_LIMIT,
        "recent_capture_count": capture_count,
        "recent_online_count": len(online_rows),
        "recent_average_players": _round_average(player_values),
        "recent_peak_players": max(player_values, default=None),
        "last_seen_online_at": last_seen_online_at,
        "minutes_since_last_capture": _minutes_since_timestamp(latest_captured_at),
    }


def _round_average(values: list[int]) -> float | None:
    if not values:
        return None

    return round(sum(values) / len(values), 1)


def _minutes_since_timestamp(timestamp: str | None) -> int | None:
    if not timestamp:
        return None

    normalized = timestamp.replace("Z", "+00:00")
    captured_at = datetime.fromisoformat(normalized)
    if captured_at.tzinfo is None:
        captured_at = captured_at.replace(tzinfo=timezone.utc)

    delta = datetime.now(timezone.utc) - captured_at.astimezone(timezone.utc)
    return max(0, int(delta.total_seconds() // 60))


def _build_server_filter(server_id: str) -> tuple[str, object]:
    normalized = server_id.strip()
    if normalized.isdigit():
        return "servers.id", int(normalized)

    return "servers.external_server_id", normalized
