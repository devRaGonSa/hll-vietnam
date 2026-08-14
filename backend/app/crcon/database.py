"""Strictly read-only CRCON PostgreSQL capability adapter."""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from .capabilities import PROBED_TABLES, build_capability_report
from .models import CrconCapabilityReport, CrconDatabaseError, CrconUnavailableError


APPLICATION_NAME = "hll-vietnam-bff"
SCHEMA_COLUMNS_SQL = """
SELECT table_name, column_name
FROM information_schema.columns
WHERE table_schema = current_schema()
  AND table_name = ANY(%s)
ORDER BY table_name, ordinal_position
"""
CURRENT_MAP_MATCH_SQL = """
SELECT id, start, end, server_number, map_name, result
FROM map_history
WHERE server_number = %s
  AND end IS NULL
  AND lower(map_name) = lower(%s)
  AND start >= %s
  AND start <= %s
ORDER BY start DESC, id DESC
LIMIT 2
"""
CURRENT_OPEN_MAP_SQL = """
SELECT id, start, end, server_number, map_name, result
FROM map_history
WHERE server_number = %s
  AND end IS NULL
ORDER BY start DESC, id DESC
LIMIT 2
"""
MATCH_LOG_EVENTS_SQL = """
SELECT
    logs.id,
    logs.event_time,
    logs.type,
    logs.player1_name,
    player1.steam_id_64 AS player1_id,
    logs.player2_name,
    player2.steam_id_64 AS player2_id,
    logs.weapon
FROM log_lines AS logs
LEFT JOIN steam_id_64 AS player1 ON player1.id = logs.player1_steamid
LEFT JOIN steam_id_64 AS player2 ON player2.id = logs.player2_steamid
WHERE logs.server = %s
  AND logs.event_time >= %s
  AND logs.event_time <= %s
  AND logs.type = ANY(%s)
ORDER BY logs.event_time ASC, logs.id ASC
LIMIT %s
"""


@dataclass(frozen=True, slots=True)
class CrconCurrentMap:
    id: int
    start: datetime
    end: datetime | None
    server_number: int
    map_name: str
    result: dict[str, int] | None


@dataclass(frozen=True, slots=True)
class CrconMatchLogEvent:
    id: int
    event_time: datetime
    type: str
    player1_name: str | None
    player1_id: str | None
    player2_name: str | None
    player2_id: str | None
    weapon: str | None

Connector = Callable[..., Any]


class CrconDatabase:
    """Capability-only PostgreSQL boundary with fail-closed read-only sessions."""

    def __init__(
        self,
        *,
        dsn: str | None,
        connect_timeout_seconds: int,
        statement_timeout_ms: int,
        lock_timeout_ms: int,
        connector: Connector | None = None,
    ) -> None:
        if connect_timeout_seconds <= 0:
            raise ValueError("connect_timeout_seconds must be positive.")
        if statement_timeout_ms <= 0:
            raise ValueError("statement_timeout_ms must be positive.")
        if lock_timeout_ms < 0:
            raise ValueError("lock_timeout_ms must be zero or positive.")
        self._dsn = str(dsn or "").strip() or None
        self._connect_timeout_seconds = connect_timeout_seconds
        self._statement_timeout_ms = statement_timeout_ms
        self._lock_timeout_ms = lock_timeout_ms
        self._connector = connector

    @property
    def configured(self) -> bool:
        return self._dsn is not None

    def probe_capabilities(self, *, api_configured: bool = False) -> CrconCapabilityReport:
        """Inspect only allowlisted schema metadata and report each capability."""
        if not self.configured:
            return build_capability_report(
                schema_columns=None,
                database_configured=False,
                api_configured=api_configured,
            )

        schema_columns: dict[str, set[str]] = {}
        with self._read_only_connection() as connection:
            cursor = connection.execute(SCHEMA_COLUMNS_SQL, (sorted(PROBED_TABLES),))
            for row in cursor.fetchall():
                table_name, column_name = _schema_row(row)
                schema_columns.setdefault(table_name, set()).add(column_name)

        return build_capability_report(
            schema_columns=schema_columns,
            database_configured=True,
            api_configured=api_configured,
        )

    def find_current_map(
        self,
        *,
        server_number: int,
        map_name: str | None,
        started_at: datetime | None,
        tolerance_seconds: int = 180,
    ) -> CrconCurrentMap | None:
        """Return one unambiguous open map matching current API state."""
        self._require_configured()
        if server_number <= 0:
            raise ValueError("server_number must be positive.")
        if tolerance_seconds < 0 or tolerance_seconds > 900:
            raise ValueError("tolerance_seconds must be between zero and 900.")

        normalized_map = str(map_name or "").strip()
        with self._read_only_connection() as connection:
            if normalized_map and started_at is not None:
                tolerance = timedelta(seconds=tolerance_seconds)
                cursor = connection.execute(
                    CURRENT_MAP_MATCH_SQL,
                    (
                        server_number,
                        normalized_map,
                        started_at - tolerance,
                        started_at + tolerance,
                    ),
                )
            else:
                cursor = connection.execute(CURRENT_OPEN_MAP_SQL, (server_number,))
            rows = cursor.fetchall()

        if len(rows) != 1:
            return None
        return _current_map_row(rows[0])

    def list_match_log_events(
        self,
        *,
        server_number: int,
        started_at: datetime,
        ended_at: datetime,
        limit: int = 500,
    ) -> tuple[CrconMatchLogEvent, ...]:
        """Read a bounded, deterministically ordered current-match combat window."""
        self._require_configured()
        if server_number <= 0:
            raise ValueError("server_number must be positive.")
        if ended_at < started_at:
            raise ValueError("ended_at must not precede started_at.")
        if limit < 1 or limit > 500:
            raise ValueError("limit must be between one and 500.")

        with self._read_only_connection() as connection:
            cursor = connection.execute(
                MATCH_LOG_EVENTS_SQL,
                (
                    str(server_number),
                    started_at,
                    ended_at,
                    ["KILL", "TEAM KILL"],
                    limit,
                ),
            )
            rows = cursor.fetchall()
        return tuple(_match_log_event_row(row) for row in rows)

    def _require_configured(self) -> None:
        if not self.configured:
            raise CrconUnavailableError("CRCON database is not configured.")

    @contextmanager
    def _read_only_connection(self) -> Iterator[Any]:
        connector = self._connector or _load_connector()
        connection = None
        try:
            connection = connector(
                self._dsn,
                connect_timeout=self._connect_timeout_seconds,
                application_name=APPLICATION_NAME,
                options=(
                    "-c default_transaction_read_only=on "
                    f"-c statement_timeout={self._statement_timeout_ms} "
                    f"-c lock_timeout={self._lock_timeout_ms}"
                ),
            )
            connection.execute("BEGIN READ ONLY")
            status_row = connection.execute("SHOW transaction_read_only").fetchone()
            if _read_only_status(status_row) != "on":
                raise CrconDatabaseError("CRCON database did not establish read-only mode.")
            yield connection
        except CrconDatabaseError:
            raise
        except Exception:
            raise CrconDatabaseError("CRCON database operation failed.") from None
        finally:
            if connection is not None:
                had_active_error = sys.exc_info()[0] is not None
                cleanup_failed = False
                try:
                    connection.rollback()
                except Exception:
                    cleanup_failed = True
                try:
                    connection.close()
                except Exception:
                    cleanup_failed = True
                if cleanup_failed and not had_active_error:
                    raise CrconDatabaseError("CRCON database cleanup failed.") from None


def _load_connector() -> Connector:
    try:
        import psycopg
    except ImportError:  # pragma: no cover - environment specific
        raise CrconDatabaseError("CRCON database driver is unavailable.") from None
    return psycopg.connect


def _read_only_status(row: object) -> str | None:
    if isinstance(row, dict):
        value = row.get("transaction_read_only")
    elif isinstance(row, (tuple, list)) and row:
        value = row[0]
    else:
        value = None
    return str(value).strip().lower() if value is not None else None


def _schema_row(row: object) -> tuple[str, str]:
    if isinstance(row, dict):
        return str(row["table_name"]), str(row["column_name"])
    if isinstance(row, (tuple, list)) and len(row) >= 2:
        return str(row[0]), str(row[1])
    raise CrconDatabaseError("CRCON schema probe returned an unexpected row.")


def _current_map_row(row: object) -> CrconCurrentMap:
    if isinstance(row, dict):
        values = (
            row.get("id"),
            row.get("start"),
            row.get("end"),
            row.get("server_number"),
            row.get("map_name"),
            row.get("result"),
        )
    elif isinstance(row, (tuple, list)) and len(row) >= 6:
        values = tuple(row[:6])
    else:
        raise CrconDatabaseError("CRCON current map query returned an unexpected row.")
    map_id, start, end, server_number, map_name, result = values
    if not isinstance(start, datetime):
        raise CrconDatabaseError("CRCON current map query returned an invalid timestamp.")
    normalized_result = dict(result) if isinstance(result, dict) else None
    return CrconCurrentMap(
        id=int(map_id),
        start=start,
        end=end if isinstance(end, datetime) else None,
        server_number=int(server_number),
        map_name=str(map_name),
        result=normalized_result,
    )


def _match_log_event_row(row: object) -> CrconMatchLogEvent:
    if isinstance(row, dict):
        values = (
            row.get("id"),
            row.get("event_time"),
            row.get("type"),
            row.get("player1_name"),
            row.get("player1_id"),
            row.get("player2_name"),
            row.get("player2_id"),
            row.get("weapon"),
        )
    elif isinstance(row, (tuple, list)) and len(row) >= 8:
        values = tuple(row[:8])
    else:
        raise CrconDatabaseError("CRCON event query returned an unexpected row.")
    event_id, event_time, event_type, p1_name, p1_id, p2_name, p2_id, weapon = values
    if not isinstance(event_time, datetime):
        raise CrconDatabaseError("CRCON event query returned an invalid timestamp.")
    return CrconMatchLogEvent(
        id=int(event_id),
        event_time=event_time,
        type=str(event_type),
        player1_name=str(p1_name) if p1_name is not None else None,
        player1_id=str(p1_id) if p1_id is not None else None,
        player2_name=str(p2_name) if p2_name is not None else None,
        player2_id=str(p2_id) if p2_id is not None else None,
        weapon=str(weapon) if weapon is not None else None,
    )
