"""Storage helpers for parsed RCON AdminLog events."""

from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter
from collections.abc import Mapping
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import get_storage_path, use_postgres_rcon_storage
from .rcon_admin_log_parser import parse_rcon_admin_log_entry
from .rcon_admin_log_parser import parse_rcon_player_profile_snapshot
from .rcon_historical_storage import initialize_rcon_historical_storage
from .sqlite_utils import connect_sqlite_writer

CURRENT_MATCH_FALLBACK_FRESHNESS = timedelta(minutes=15)
CURRENT_MATCH_PLAYER_EVENT_TYPES = (
    "kill",
    "team_switch",
    "connected",
    "disconnected",
    "chat",
    "message",
)


def initialize_rcon_admin_log_storage(*, db_path: Path | None = None) -> Path:
    """Create SQLite structures for parsed RCON AdminLog events."""
    if use_postgres_rcon_storage(explicit_sqlite_path=db_path):
        from .postgres_rcon_storage import initialize_postgres_rcon_storage

        initialize_postgres_rcon_storage()
        return get_storage_path()

    resolved_path = initialize_rcon_historical_storage(db_path=db_path)

    with closing(connect_sqlite_writer(resolved_path)) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS rcon_admin_log_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_key TEXT NOT NULL,
                external_server_id TEXT,
                event_timestamp TEXT,
                server_time INTEGER,
                relative_time TEXT,
                event_type TEXT NOT NULL,
                raw_message TEXT NOT NULL,
                canonical_message TEXT NOT NULL,
                parsed_payload_json TEXT NOT NULL,
                raw_entry_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_rcon_admin_log_events_dedupe
            ON rcon_admin_log_events(target_key, server_time, canonical_message);

            CREATE INDEX IF NOT EXISTS idx_rcon_admin_log_events_target_time
            ON rcon_admin_log_events(target_key, server_time DESC);

            CREATE INDEX IF NOT EXISTS idx_rcon_admin_log_events_type
            ON rcon_admin_log_events(event_type);

            CREATE TABLE IF NOT EXISTS rcon_player_profile_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_key TEXT NOT NULL,
                external_server_id TEXT,
                player_id TEXT NOT NULL,
                player_name TEXT NOT NULL,
                source_server_time INTEGER NOT NULL,
                event_timestamp TEXT,
                first_seen TEXT,
                sessions INTEGER,
                matches_played INTEGER,
                play_time TEXT,
                total_kills INTEGER,
                total_deaths INTEGER,
                teamkills_done INTEGER,
                teamkills_received INTEGER,
                kd_ratio REAL,
                favorite_weapons_json TEXT NOT NULL DEFAULT '{}',
                victims_json TEXT NOT NULL DEFAULT '{}',
                nemesis_json TEXT NOT NULL DEFAULT '{}',
                averages_json TEXT NOT NULL DEFAULT '{}',
                sanctions_json TEXT NOT NULL DEFAULT '{}',
                raw_content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(target_key, player_id, source_server_time)
            );

            CREATE INDEX IF NOT EXISTS idx_rcon_player_profile_snapshots_player
            ON rcon_player_profile_snapshots(target_key, player_id, source_server_time DESC);
            """
        )
        _ensure_canonical_message_column(connection)
        connection.commit()

    return resolved_path


def persist_rcon_admin_log_entries(
    *,
    target: Mapping[str, object],
    entries: list[dict[str, object]],
    db_path: Path | None = None,
) -> dict[str, int]:
    """Persist raw and parsed AdminLog entries idempotently."""
    if use_postgres_rcon_storage(explicit_sqlite_path=db_path):
        return _persist_rcon_admin_log_entries_postgres(target=target, entries=entries)

    resolved_path = initialize_rcon_admin_log_storage(db_path=db_path)
    target_key = str(target.get("target_key") or target.get("external_server_id") or "")
    if not target_key:
        raise ValueError("target must include target_key or external_server_id")

    external_server_id = target.get("external_server_id")
    inserted = 0
    duplicates = 0

    with closing(connect_sqlite_writer(resolved_path)) as connection:
        for entry in entries:
            parsed = parse_rcon_admin_log_entry(entry)
            raw_message = str(parsed.get("raw_message") or "")
            canonical_message = _canonicalize_admin_log_message(raw_message)
            cursor = connection.execute(
                """
                INSERT INTO rcon_admin_log_events (
                    target_key,
                    external_server_id,
                    event_timestamp,
                    server_time,
                    relative_time,
                    event_type,
                    raw_message,
                    canonical_message,
                    parsed_payload_json,
                    raw_entry_json
                )
                SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM rcon_admin_log_events
                    WHERE target_key = ?
                      AND server_time IS ?
                      AND canonical_message = ?
                )
                """,
                (
                    target_key,
                    external_server_id,
                    parsed.get("timestamp"),
                    parsed.get("server_time"),
                    parsed.get("relative_time"),
                    parsed.get("event_type") or "unknown",
                    raw_message,
                    canonical_message,
                    json.dumps(parsed, ensure_ascii=False, separators=(",", ":")),
                    json.dumps(entry, ensure_ascii=False, separators=(",", ":")),
                    target_key,
                    parsed.get("server_time"),
                    canonical_message,
                ),
            )
            if int(cursor.rowcount or 0):
                inserted += 1
            else:
                duplicates += 1
            _persist_profile_snapshot_if_present(
                connection,
                target_key=target_key,
                external_server_id=external_server_id,
                parsed=parsed,
            )
        connection.commit()

    return {
        "events_seen": len(entries),
        "events_inserted": inserted,
        "duplicate_events": duplicates,
    }


def _persist_profile_snapshot_if_present(
    connection: sqlite3.Connection,
    *,
    target_key: str,
    external_server_id: object,
    parsed: dict[str, object],
) -> None:
    snapshot = parse_rcon_player_profile_snapshot(parsed)
    if snapshot is None:
        return
    connection.execute(
        """
        INSERT INTO rcon_player_profile_snapshots (
            target_key,
            external_server_id,
            player_id,
            player_name,
            source_server_time,
            event_timestamp,
            first_seen,
            sessions,
            matches_played,
            play_time,
            total_kills,
            total_deaths,
            teamkills_done,
            teamkills_received,
            kd_ratio,
            favorite_weapons_json,
            victims_json,
            nemesis_json,
            averages_json,
            sanctions_json,
            raw_content
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(target_key, player_id, source_server_time) DO UPDATE SET
            external_server_id = excluded.external_server_id,
            player_name = excluded.player_name,
            event_timestamp = excluded.event_timestamp,
            first_seen = excluded.first_seen,
            sessions = excluded.sessions,
            matches_played = excluded.matches_played,
            play_time = excluded.play_time,
            total_kills = excluded.total_kills,
            total_deaths = excluded.total_deaths,
            teamkills_done = excluded.teamkills_done,
            teamkills_received = excluded.teamkills_received,
            kd_ratio = excluded.kd_ratio,
            favorite_weapons_json = excluded.favorite_weapons_json,
            victims_json = excluded.victims_json,
            nemesis_json = excluded.nemesis_json,
            averages_json = excluded.averages_json,
            sanctions_json = excluded.sanctions_json,
            raw_content = excluded.raw_content,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            target_key,
            external_server_id,
            snapshot.player_id,
            snapshot.player_name,
            snapshot.source_server_time,
            snapshot.event_timestamp,
            snapshot.first_seen,
            snapshot.sessions,
            snapshot.matches_played,
            snapshot.play_time,
            snapshot.total_kills,
            snapshot.total_deaths,
            snapshot.teamkills_done,
            snapshot.teamkills_received,
            snapshot.kd_ratio,
            json.dumps(snapshot.favorite_weapons, ensure_ascii=False, separators=(",", ":")),
            json.dumps(snapshot.victims, ensure_ascii=False, separators=(",", ":")),
            json.dumps(snapshot.nemesis, ensure_ascii=False, separators=(",", ":")),
            json.dumps(snapshot.averages, ensure_ascii=False, separators=(",", ":")),
            json.dumps(snapshot.sanctions, ensure_ascii=False, separators=(",", ":")),
            snapshot.raw_content,
        ),
    )


_PREFIX_RE = re.compile(r"^\[.*?\(\d+\)\]\s+", re.DOTALL)


def _canonicalize_admin_log_message(raw_message: str) -> str:
    """Return a stable message body for deduplication across repeated AdminLog reads."""
    normalized = str(raw_message or "").strip()
    return _PREFIX_RE.sub("", normalized).strip()


def _ensure_canonical_message_column(connection: sqlite3.Connection) -> None:
    columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(rcon_admin_log_events)").fetchall()
    }
    if "canonical_message" not in columns:
        connection.execute(
            "ALTER TABLE rcon_admin_log_events ADD COLUMN canonical_message TEXT NOT NULL DEFAULT ''"
        )
        connection.execute(
            """
            UPDATE rcon_admin_log_events
            SET canonical_message = raw_message
            WHERE canonical_message = ''
            """
        )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_rcon_admin_log_events_dedupe
        ON rcon_admin_log_events(target_key, server_time, canonical_message)
        """
    )


def list_rcon_admin_log_event_counts(*, db_path: Path | None = None) -> list[dict[str, object]]:
    """Return event counts grouped by target and event type."""
    if use_postgres_rcon_storage(explicit_sqlite_path=db_path):
        from .postgres_rcon_storage import connect_postgres_compat

        with connect_postgres_compat() as connection:
            rows = connection.execute(
                """
                SELECT
                    target_key,
                    event_type,
                    COUNT(*) AS event_count,
                    MIN(server_time) AS first_server_time,
                    MAX(server_time) AS last_server_time
                FROM rcon_admin_log_events
                GROUP BY target_key, event_type
                ORDER BY target_key ASC, event_count DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    resolved_path = db_path or get_storage_path()
    initialize_rcon_admin_log_storage(db_path=resolved_path)

    with closing(sqlite3.connect(resolved_path)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT
                target_key,
                event_type,
                COUNT(*) AS event_count,
                MIN(server_time) AS first_server_time,
                MAX(server_time) AS last_server_time
            FROM rcon_admin_log_events
            GROUP BY target_key, event_type
            ORDER BY target_key ASC, event_count DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def list_current_match_kill_feed(
    *,
    server_key: str,
    limit: int = 30,
    since_event_id: str | None = None,
    db_path: Path | None = None,
    now: datetime | None = None,
    ensure_storage: bool = True,
) -> dict[str, object]:
    """Return safe recent kill rows for one AdminLog server window."""
    resolved_path = (
        initialize_rcon_admin_log_storage(db_path=db_path)
        if ensure_storage
        else db_path or get_storage_path()
    )
    since_row_id = _parse_current_match_event_row_id(since_event_id)
    if use_postgres_rcon_storage(explicit_sqlite_path=db_path):
        from .postgres_rcon_storage import connect_postgres_compat

        connection_scope = connect_postgres_compat(initialize=ensure_storage)
    else:
        connection_scope = closing(_connect_admin_log_sqlite_read(resolved_path))

    with connection_scope as connection:
        if isinstance(connection, sqlite3.Connection):
            connection.row_factory = sqlite3.Row
        boundary = connection.execute(
            """
            SELECT event_type, server_time
            FROM rcon_admin_log_events
            WHERE (target_key = ? OR external_server_id = ?)
              AND event_type IN ('match_start', 'match_end')
              AND server_time IS NOT NULL
            ORDER BY server_time DESC, id DESC
            LIMIT 1
            """,
            (server_key, server_key),
        ).fetchone()
        open_start_time = (
            boundary["server_time"]
            if boundary is not None and boundary["event_type"] == "match_start"
            else None
        )
        if open_start_time is None:
            if since_row_id is None:
                rows = connection.execute(
                    """
                    SELECT id, target_key, external_server_id, event_timestamp, server_time,
                           parsed_payload_json
                    FROM rcon_admin_log_events
                    WHERE (target_key = ? OR external_server_id = ?)
                      AND event_type = 'kill'
                    ORDER BY server_time DESC, id DESC
                    LIMIT ?
                    """,
                    (server_key, server_key, limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT id, target_key, external_server_id, event_timestamp, server_time,
                           parsed_payload_json
                    FROM rcon_admin_log_events
                    WHERE (target_key = ? OR external_server_id = ?)
                      AND event_type = 'kill'
                      AND id > ?
                    ORDER BY server_time DESC, id DESC
                    LIMIT ?
                    """,
                    (server_key, server_key, since_row_id, limit),
                ).fetchall()
            scope = "recent-admin-log-window"
            confidence = "partial"
        else:
            if since_row_id is None:
                rows = connection.execute(
                    """
                    SELECT id, target_key, external_server_id, event_timestamp, server_time,
                           parsed_payload_json
                    FROM rcon_admin_log_events
                    WHERE (target_key = ? OR external_server_id = ?)
                      AND event_type = 'kill'
                      AND server_time >= ?
                    ORDER BY server_time DESC, id DESC
                    LIMIT ?
                    """,
                    (server_key, server_key, open_start_time, limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT id, target_key, external_server_id, event_timestamp, server_time,
                           parsed_payload_json
                    FROM rcon_admin_log_events
                    WHERE (target_key = ? OR external_server_id = ?)
                      AND event_type = 'kill'
                      AND server_time >= ?
                      AND id > ?
                    ORDER BY server_time DESC, id DESC
                    LIMIT ?
                    """,
                    (server_key, server_key, open_start_time, since_row_id, limit),
                ).fetchall()
            scope = "open-admin-log-match-window"
            confidence = "admin-log-boundary"

    stale_events_filtered = 0
    if scope == "recent-admin-log-window":
        freshness_anchor = _as_utc_datetime(now) or datetime.now(timezone.utc)
        fresh_rows = [
            row
            for row in rows
            if _row_is_current_match_fallback_fresh(row, freshness_anchor)
        ]
        stale_events_filtered = len(rows) - len(fresh_rows)
        rows = fresh_rows
        if not rows:
            scope = "no-current-match-events"
            confidence = "stale-filtered" if stale_events_filtered else "none"

    return {
        "scope": scope,
        "confidence": confidence,
        "stale_events_filtered": stale_events_filtered,
        "items": [_serialize_kill_feed_row(row) for row in rows],
    }


def list_current_match_player_stats(
    *,
    server_key: str,
    db_path: Path | None = None,
    now: datetime | None = None,
    ensure_storage: bool = True,
) -> dict[str, object]:
    """Return current-match participants and partial stats from the safe AdminLog window."""
    resolved_path = (
        initialize_rcon_admin_log_storage(db_path=db_path)
        if ensure_storage
        else db_path or get_storage_path()
    )
    if use_postgres_rcon_storage(explicit_sqlite_path=db_path):
        from .postgres_rcon_storage import connect_postgres_compat

        connection_scope = connect_postgres_compat(initialize=ensure_storage)
    else:
        connection_scope = closing(_connect_admin_log_sqlite_read(resolved_path))

    with connection_scope as connection:
        if isinstance(connection, sqlite3.Connection):
            connection.row_factory = sqlite3.Row
        window = _resolve_current_match_window(
            connection,
            server_key=server_key,
            now=now,
        )
        rows = _list_current_match_participant_rows(
            connection,
            server_key=server_key,
            window=window,
        )

    players: dict[str, dict[str, object]] = {}
    for row in rows:
        payload = _json_mapping(row["parsed_payload_json"])
        event_timestamp = row["event_timestamp"]
        event_type = str(row["event_type"] or "")
        if event_type == "kill":
            event_key = _current_match_stat_event_key(row, payload)
            killer = _ensure_current_match_player(
                players,
                player_name=payload.get("killer_name"),
                player_id=payload.get("killer_id"),
                team=payload.get("killer_team"),
                event_timestamp=event_timestamp,
                is_connected=None,
                source=event_type,
            )
            victim = _ensure_current_match_player(
                players,
                player_name=payload.get("victim_name"),
                player_id=payload.get("victim_id"),
                team=payload.get("victim_team"),
                event_timestamp=event_timestamp,
                is_connected=None,
                source=event_type,
            )
            if killer is not None:
                weapon = _safe_event_field(payload.get("weapon")) or "UNKNOWN"
                _add_current_match_player_weapon(killer, weapon, event_key)
                if payload.get("killer_team") and payload.get("killer_team") == payload.get("victim_team"):
                    _add_current_match_player_stat(killer, "teamkills", event_key)
                else:
                    _add_current_match_player_stat(killer, "kills", event_key)
            if victim is not None:
                _add_current_match_player_stat(victim, "deaths", event_key)
                if payload.get("killer_team") and payload.get("killer_team") == payload.get("victim_team"):
                    _add_current_match_player_stat(victim, "deaths_by_teamkill", event_key)
            continue

        if event_type == "team_switch":
            _ensure_current_match_player(
                players,
                player_name=payload.get("player_name"),
                player_id=payload.get("player_id"),
                team=payload.get("to_team"),
                event_timestamp=event_timestamp,
                is_connected=None,
                source=event_type,
            )
            continue

        if event_type == "connected":
            _ensure_current_match_player(
                players,
                player_name=payload.get("player_name"),
                player_id=payload.get("player_id"),
                team=None,
                event_timestamp=event_timestamp,
                is_connected=True,
                source=event_type,
            )
            continue

        if event_type == "disconnected":
            _ensure_current_match_player(
                players,
                player_name=payload.get("player_name"),
                player_id=payload.get("player_id"),
                team=None,
                event_timestamp=event_timestamp,
                is_connected=False,
                source=event_type,
            )
            continue

        if event_type in {"chat", "message"}:
            _ensure_current_match_player(
                players,
                player_name=payload.get("player_name"),
                player_id=payload.get("player_id"),
                team=payload.get("chat_team"),
                event_timestamp=event_timestamp,
                is_connected=None,
                source=event_type,
            )

    items = [_serialize_current_match_player(player, window_confidence=window["confidence"]) for player in players.values()]
    items.sort(key=_current_match_player_sort_key)
    return {
        "scope": window["scope"],
        "confidence": window["confidence"] if items else window["confidence"],
        "source": "rcon-admin-log-current-match-summary",
        "updated_at": max(
            (str(item["last_seen_at"]) for item in items if item.get("last_seen_at")),
            default=None,
        ),
        "stale_events_filtered": int(window["stale_events_filtered"]),
        "items": items,
    }


def _connect_admin_log_sqlite_read(db_path: Path) -> sqlite3.Connection:
    """Open AdminLog storage for read without creating files during public GETs."""
    if not db_path.exists():
        raise FileNotFoundError(f"AdminLog storage is not available: {db_path}")
    uri = f"file:{db_path.as_posix()}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _resolve_current_match_window(
    connection: sqlite3.Connection | object,
    *,
    server_key: str,
    now: datetime | None,
) -> dict[str, object]:
    boundary = connection.execute(
        """
        SELECT event_type, server_time
        FROM rcon_admin_log_events
        WHERE (target_key = ? OR external_server_id = ?)
          AND event_type IN ('match_start', 'match_end')
          AND server_time IS NOT NULL
        ORDER BY server_time DESC, id DESC
        LIMIT 1
        """,
        (server_key, server_key),
    ).fetchone()
    open_start_time = (
        boundary["server_time"]
        if boundary is not None and boundary["event_type"] == "match_start"
        else None
    )
    if open_start_time is not None:
        return {
            "scope": "open-admin-log-match-window",
            "confidence": "admin-log-boundary",
            "open_start_time": int(open_start_time),
            "stale_events_filtered": 0,
            "freshness_anchor": None,
        }

    freshness_anchor = _as_utc_datetime(now) or datetime.now(timezone.utc)
    return {
        "scope": "recent-admin-log-window",
        "confidence": "partial",
        "open_start_time": None,
        "stale_events_filtered": 0,
        "freshness_anchor": freshness_anchor,
    }


def _list_current_match_participant_rows(
    connection: sqlite3.Connection | object,
    *,
    server_key: str,
    window: Mapping[str, object],
) -> list[Mapping[str, object]]:
    event_placeholders = ",".join("?" for _ in CURRENT_MATCH_PLAYER_EVENT_TYPES)
    params: list[object] = [server_key, server_key, *CURRENT_MATCH_PLAYER_EVENT_TYPES]
    if window.get("open_start_time") is not None:
        params.append(window["open_start_time"])
        rows = connection.execute(
            f"""
            SELECT id, target_key, external_server_id, event_timestamp, server_time, event_type,
                   parsed_payload_json
            FROM rcon_admin_log_events
            WHERE (target_key = ? OR external_server_id = ?)
              AND event_type IN ({event_placeholders})
              AND server_time >= ?
            ORDER BY server_time ASC, id ASC
            """,
            params,
        ).fetchall()
        return rows

    rows = connection.execute(
        f"""
        SELECT id, target_key, external_server_id, event_timestamp, server_time, event_type,
               parsed_payload_json
        FROM rcon_admin_log_events
        WHERE (target_key = ? OR external_server_id = ?)
          AND event_type IN ({event_placeholders})
        ORDER BY server_time DESC, id DESC
        LIMIT 500
        """,
        params,
    ).fetchall()
    freshness_anchor = window.get("freshness_anchor")
    fresh_rows = [
        row
        for row in rows
        if _row_is_current_match_fallback_fresh(row, freshness_anchor)
    ]
    window["stale_events_filtered"] = len(rows) - len(fresh_rows)
    if not fresh_rows:
        window["scope"] = "no-current-match-events"
        window["confidence"] = "stale-filtered" if window["stale_events_filtered"] else "none"
        return []
    return list(reversed(fresh_rows))


def get_latest_rcon_player_profile_summaries(
    *,
    target_key: str,
    player_ids: list[str],
    db_path: Path | None = None,
) -> dict[str, dict[str, object]]:
    """Return safe latest profile summaries keyed by player id."""
    requested_ids = [str(player_id).strip() for player_id in player_ids if str(player_id).strip()]
    if not target_key or not requested_ids:
        return {}
    if use_postgres_rcon_storage(explicit_sqlite_path=db_path):
        from .postgres_rcon_storage import connect_postgres_compat

        placeholders = ",".join("?" for _ in requested_ids)
        with connect_postgres_compat() as connection:
            rows = connection.execute(
                f"""
                SELECT snapshots.*
                FROM rcon_player_profile_snapshots AS snapshots
                INNER JOIN (
                    SELECT player_id, MAX(source_server_time) AS latest_source_server_time
                    FROM rcon_player_profile_snapshots
                    WHERE target_key = ?
                      AND player_id IN ({placeholders})
                    GROUP BY player_id
                ) AS latest
                  ON latest.player_id = snapshots.player_id
                 AND latest.latest_source_server_time = snapshots.source_server_time
                WHERE snapshots.target_key = ?
                """,
                [target_key, *requested_ids, target_key],
            ).fetchall()
        return {str(row["player_id"]): _build_safe_profile_summary(row) for row in rows}

    resolved_path = db_path or get_storage_path()
    initialize_rcon_admin_log_storage(db_path=resolved_path)
    placeholders = ",".join("?" for _ in requested_ids)
    with closing(sqlite3.connect(resolved_path)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            f"""
            SELECT snapshots.*
            FROM rcon_player_profile_snapshots AS snapshots
            INNER JOIN (
                SELECT player_id, MAX(source_server_time) AS latest_source_server_time
                FROM rcon_player_profile_snapshots
                WHERE target_key = ?
                  AND player_id IN ({placeholders})
                GROUP BY player_id
            ) AS latest
              ON latest.player_id = snapshots.player_id
             AND latest.latest_source_server_time = snapshots.source_server_time
            WHERE snapshots.target_key = ?
            """,
            [target_key, *requested_ids, target_key],
        ).fetchall()

    return {str(row["player_id"]): _build_safe_profile_summary(row) for row in rows}


def _build_safe_profile_summary(row: sqlite3.Row) -> dict[str, object]:
    return {
        "player_name": row["player_name"],
        "source_server_time": row["source_server_time"],
        "event_timestamp": row["event_timestamp"],
        "first_seen": row["first_seen"],
        "sessions": row["sessions"],
        "matches_played": row["matches_played"],
        "play_time": row["play_time"],
        "totals": {
            "kills": row["total_kills"],
            "deaths": row["total_deaths"],
            "teamkills_done": row["teamkills_done"],
            "teamkills_received": row["teamkills_received"],
            "kd_ratio": row["kd_ratio"],
        },
        "favorite_weapons": _json_mapping(row["favorite_weapons_json"]),
        "victims": _json_mapping(row["victims_json"]),
        "nemesis": _json_mapping(row["nemesis_json"]),
        "averages": _json_mapping(row["averages_json"]),
        "sanctions": _json_mapping(row["sanctions_json"]),
    }


def _json_mapping(raw_value: object) -> dict[str, object]:
    if not isinstance(raw_value, str) or not raw_value.strip():
        return {}
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _serialize_kill_feed_row(row: Mapping[str, object]) -> dict[str, object]:
    payload = _json_mapping(row["parsed_payload_json"])
    target_key = str(row["external_server_id"] or row["target_key"] or "unknown")
    killer_team = _safe_event_field(payload.get("killer_team"))
    victim_team = _safe_event_field(payload.get("victim_team"))
    return {
        "event_id": f"rcon-admin-log:{target_key}:{row['id']}",
        "event_timestamp": row["event_timestamp"],
        "server_time": row["server_time"],
        "killer_name": _safe_event_field(payload.get("killer_name")),
        "killer_team": killer_team,
        "victim_name": _safe_event_field(payload.get("victim_name")),
        "victim_team": victim_team,
        "weapon": _safe_event_field(payload.get("weapon")),
        "is_teamkill": bool(
            killer_team
            and killer_team != "None"
            and killer_team == victim_team
        ),
    }


def _parse_current_match_event_row_id(value: object) -> int | None:
    prefix, separator, row_id = str(value or "").rpartition(":")
    if separator != ":" or not prefix.startswith("rcon-admin-log:"):
        return None
    try:
        parsed = int(row_id)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _safe_event_field(value: object) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def _ensure_current_match_player(
    players: dict[str, dict[str, object]],
    *,
    player_name: object,
    player_id: object,
    team: object,
    event_timestamp: object,
    is_connected: bool | None,
    source: str,
) -> dict[str, object] | None:
    safe_name = _safe_event_field(player_name)
    safe_id = _safe_event_field(player_id)
    key = _resolve_current_match_player_key(players, player_id=safe_id, player_name=safe_name)
    if key is None:
        return None
    player = players.setdefault(
        key,
        {
            "player_id": safe_id,
            "player_name": safe_name,
            "team": None,
            "kills": 0,
            "deaths": 0,
            "teamkills": 0,
            "deaths_by_teamkill": 0,
            "is_connected": None,
            "last_seen_at": None,
            "_weapon_counts": Counter(),
            "_weapon_event_keys": {},
            "_stat_event_keys": {},
            "_sources": set(),
        },
    )
    if safe_id:
        player["player_id"] = safe_id
    if safe_name:
        current_name = _safe_event_field(player.get("player_name"))
        if current_name is None or len(safe_name) >= len(current_name):
            player["player_name"] = safe_name
    safe_team = _safe_event_field(team)
    if safe_team and (
        _is_known_current_match_team(safe_team)
        or not _is_known_current_match_team(player.get("team"))
    ):
        player["team"] = safe_team
    if is_connected is not None:
        player["is_connected"] = is_connected
    safe_timestamp = _safe_event_field(event_timestamp)
    if safe_timestamp and (
        player["last_seen_at"] is None or safe_timestamp > str(player["last_seen_at"])
    ):
        player["last_seen_at"] = safe_timestamp
    player["_sources"].add(source)
    return player


def _resolve_current_match_player_key(
    players: dict[str, dict[str, object]],
    *,
    player_id: str | None,
    player_name: str | None,
) -> str | None:
    id_key = f"id:{player_id}" if player_id else None
    name_key = _current_match_player_name_key(player_name)
    if id_key is not None:
        if name_key is not None and name_key in players:
            named_player = players.pop(name_key)
            if id_key in players:
                _merge_current_match_player(players[id_key], named_player)
            else:
                players[id_key] = named_player
        return id_key
    if name_key is None:
        return None

    normalized_name = _normalize_current_match_player_name(player_name)
    matching_id_keys = [
        key
        for key, player in players.items()
        if key.startswith("id:")
        and _normalize_current_match_player_name(player.get("player_name")) == normalized_name
    ]
    if len(matching_id_keys) == 1:
        return matching_id_keys[0]
    return name_key


def _current_match_player_key(
    player_id: str | None,
    player_name: str | None,
) -> str | None:
    if player_id:
        return f"id:{player_id}"
    return _current_match_player_name_key(player_name)


def _current_match_player_name_key(player_name: object) -> str | None:
    normalized = _normalize_current_match_player_name(player_name)
    return f"name:{normalized}" if normalized else None


def _normalize_current_match_player_name(player_name: object) -> str:
    return " ".join(str(player_name or "").strip().casefold().split())


def _merge_current_match_player(
    destination: dict[str, object],
    source: Mapping[str, object],
) -> None:
    if not destination.get("player_id") and source.get("player_id"):
        destination["player_id"] = source.get("player_id")

    source_name = _safe_event_field(source.get("player_name"))
    if source_name:
        destination_name = _safe_event_field(destination.get("player_name"))
        if destination_name is None or len(source_name) >= len(destination_name):
            destination["player_name"] = source_name

    source_team = source.get("team")
    if _is_known_current_match_team(source_team) or not _is_known_current_match_team(destination.get("team")):
        if _safe_event_field(source_team):
            destination["team"] = source_team

    _merge_current_match_stat_events(destination, source)
    _merge_current_match_weapon_events(destination, source)

    source_last_seen = _safe_event_field(source.get("last_seen_at"))
    destination_last_seen = _safe_event_field(destination.get("last_seen_at"))
    if source_last_seen and (destination_last_seen is None or source_last_seen > destination_last_seen):
        destination["last_seen_at"] = source_last_seen
        if source.get("is_connected") is not None:
            destination["is_connected"] = source.get("is_connected")
    elif destination.get("is_connected") is None and source.get("is_connected") is not None:
        destination["is_connected"] = source.get("is_connected")

    destination_sources = destination.setdefault("_sources", set())
    source_sources = source.get("_sources", set())
    if isinstance(destination_sources, set) and isinstance(source_sources, set):
        destination_sources.update(source_sources)


def _merge_current_match_stat_events(
    destination: dict[str, object],
    source: Mapping[str, object],
) -> None:
    destination_keys = _stat_event_keys(destination)
    source_keys = _stat_event_keys(source)
    for stat_name in ("kills", "deaths", "teamkills", "deaths_by_teamkill"):
        source_count = int(source.get(stat_name) or 0)
        if source_count == 0:
            continue
        source_stat_keys = source_keys.get(stat_name, set())
        destination_stat_keys = destination_keys.setdefault(stat_name, set())
        overlap = len(destination_stat_keys & source_stat_keys)
        destination[stat_name] = int(destination.get(stat_name) or 0) + max(0, source_count - overlap)
        destination_stat_keys.update(source_stat_keys)


def _merge_current_match_weapon_events(
    destination: dict[str, object],
    source: Mapping[str, object],
) -> None:
    destination_counts = _player_weapon_counts(destination)
    source_counts = _player_weapon_counts(source)
    destination_keys = _weapon_event_keys(destination)
    source_keys = _weapon_event_keys(source)
    for weapon, count in source_counts.items():
        source_weapon_keys = source_keys.get(weapon, set())
        destination_weapon_keys = destination_keys.setdefault(weapon, set())
        overlap = len(destination_weapon_keys & source_weapon_keys)
        destination_counts[weapon] += max(0, int(count) - overlap)
        destination_weapon_keys.update(source_weapon_keys)


def _is_known_current_match_team(value: object) -> bool:
    normalized = str(value or "").strip().casefold()
    return normalized in {"allies", "allied", "axis"}


def _current_match_stat_event_key(row: Mapping[str, object], payload: Mapping[str, object]) -> str:
    parts = [
        "kill",
        _row_value(row, "server_time"),
        _row_value(row, "event_timestamp"),
        payload.get("killer_name"),
        payload.get("killer_team"),
        payload.get("victim_name"),
        payload.get("victim_team"),
        payload.get("weapon"),
    ]
    normalized_parts = [_normalize_current_match_event_value(part) for part in parts]
    semantic_key = "|".join(normalized_parts)
    return semantic_key if any(normalized_parts[1:]) else f"row:{_row_value(row, 'id')}"


def _row_value(row: Mapping[str, object], key: str) -> object:
    if isinstance(row, Mapping):
        return row.get(key)
    try:
        return row[key]  # type: ignore[index]
    except (IndexError, KeyError, TypeError):
        return None


def _normalize_current_match_event_value(value: object) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _add_current_match_player_stat(
    player: dict[str, object],
    stat_name: str,
    event_key: str,
) -> None:
    event_keys = _stat_event_keys(player).setdefault(stat_name, set())
    if event_key in event_keys:
        return
    player[stat_name] = int(player.get(stat_name) or 0) + 1
    event_keys.add(event_key)


def _add_current_match_player_weapon(
    player: dict[str, object],
    weapon: str,
    event_key: str,
) -> None:
    weapon_keys = _weapon_event_keys(player).setdefault(weapon, set())
    if event_key in weapon_keys:
        return
    _player_weapon_counts(player)[weapon] += 1
    weapon_keys.add(event_key)


def _stat_event_keys(player: Mapping[str, object]) -> dict[str, set[str]]:
    event_keys = player.get("_stat_event_keys")
    if isinstance(event_keys, dict):
        return event_keys
    return {}


def _weapon_event_keys(player: Mapping[str, object]) -> dict[str, set[str]]:
    event_keys = player.get("_weapon_event_keys")
    if isinstance(event_keys, dict):
        return event_keys
    return {}


def _player_weapon_counts(player: Mapping[str, object]) -> Counter[str]:
    weapon_counts = player.get("_weapon_counts")
    if isinstance(weapon_counts, Counter):
        return weapon_counts
    return Counter()


def _serialize_current_match_player(
    player: Mapping[str, object],
    *,
    window_confidence: object,
) -> dict[str, object]:
    sources = sorted(str(value) for value in player.get("_sources", set()))
    return {
        "player_name": player.get("player_name"),
        "player_id": player.get("player_id"),
        "team": player.get("team"),
        "kills": int(player.get("kills") or 0),
        "deaths": int(player.get("deaths") or 0),
        "teamkills": int(player.get("teamkills") or 0),
        "deaths_by_teamkill": int(player.get("deaths_by_teamkill") or 0),
        "favorite_weapon": _favorite_weapon_for_player(_player_weapon_counts(player)),
        "last_seen_at": player.get("last_seen_at"),
        "is_connected": player.get("is_connected"),
        "connected": player.get("is_connected"),
        "source": ",".join(sources) if sources else "unknown",
        "confidence": str(window_confidence or "partial"),
    }


def _current_match_player_sort_key(player: Mapping[str, object]) -> tuple[int, int, int, str]:
    connected = player.get("is_connected")
    if connected is True:
        connected_rank = 0
    elif connected is None:
        connected_rank = 1
    else:
        connected_rank = 2
    return (
        -int(player.get("kills") or 0),
        int(player.get("deaths") or 0),
        connected_rank,
        str(player.get("player_name") or "").casefold(),
    )


def _favorite_weapon_for_player(weapons: Counter[str] | None) -> str | None:
    if not weapons:
        return None
    return min(weapons.items(), key=lambda item: (-item[1], item[0]))[0]


def _row_is_current_match_fallback_fresh(
    row: Mapping[str, object],
    freshness_anchor: datetime,
) -> bool:
    event_time = _as_utc_datetime(row["event_timestamp"])
    if event_time is None:
        return False
    age = freshness_anchor - event_time
    return timedelta(0) <= age <= CURRENT_MATCH_FALLBACK_FRESHNESS


def _as_utc_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _persist_rcon_admin_log_entries_postgres(
    *,
    target: Mapping[str, object],
    entries: list[dict[str, object]],
) -> dict[str, int]:
    from .postgres_rcon_storage import connect_postgres_compat

    target_key = str(target.get("target_key") or target.get("external_server_id") or "")
    if not target_key:
        raise ValueError("target must include target_key or external_server_id")

    external_server_id = target.get("external_server_id")
    inserted = 0
    duplicates = 0
    with connect_postgres_compat() as connection:
        for entry in entries:
            parsed = parse_rcon_admin_log_entry(entry)
            raw_message = str(parsed.get("raw_message") or "")
            canonical_message = _canonicalize_admin_log_message(raw_message)
            cursor = connection.execute(
                """
                INSERT INTO rcon_admin_log_events (
                    target_key,
                    external_server_id,
                    event_timestamp,
                    server_time,
                    relative_time,
                    event_type,
                    raw_message,
                    canonical_message,
                    parsed_payload_json,
                    raw_entry_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT DO NOTHING
                """,
                (
                    target_key,
                    external_server_id,
                    parsed.get("timestamp"),
                    parsed.get("server_time"),
                    parsed.get("relative_time"),
                    parsed.get("event_type") or "unknown",
                    raw_message,
                    canonical_message,
                    json.dumps(parsed, ensure_ascii=False, separators=(",", ":")),
                    json.dumps(entry, ensure_ascii=False, separators=(",", ":")),
                ),
            )
            if int(cursor.rowcount or 0):
                inserted += 1
            else:
                duplicates += 1
            _persist_profile_snapshot_if_present(
                connection,
                target_key=target_key,
                external_server_id=external_server_id,
                parsed=parsed,
            )
    return {
        "events_seen": len(entries),
        "events_inserted": inserted,
        "duplicate_events": duplicates,
    }
