"""Shared SQLite connection helpers for backend persistence layers."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .config import get_sqlite_busy_timeout_ms, get_sqlite_writer_timeout_seconds


def connect_sqlite_writer(
    db_path: Path,
    *,
    timeout_seconds: float | None = None,
    busy_timeout_ms: int | None = None,
) -> sqlite3.Connection:
    """Open one SQLite connection with the common writer policy."""
    resolved_timeout_seconds = (
        get_sqlite_writer_timeout_seconds()
        if timeout_seconds is None
        else timeout_seconds
    )
    resolved_busy_timeout_ms = (
        get_sqlite_busy_timeout_ms()
        if busy_timeout_ms is None
        else busy_timeout_ms
    )

    connection = sqlite3.connect(db_path, timeout=resolved_timeout_seconds)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute(f"PRAGMA busy_timeout = {resolved_busy_timeout_ms}")
    return connection


def connect_sqlite_readonly(db_path: Path) -> sqlite3.Connection:
    """Open one read-only SQLite connection with row access enabled."""
    connection = sqlite3.connect(
        f"file:{db_path.as_posix()}?mode=ro",
        uri=True,
        timeout=get_sqlite_writer_timeout_seconds(),
    )
    connection.row_factory = sqlite3.Row
    connection.execute(f"PRAGMA busy_timeout = {get_sqlite_busy_timeout_ms()}")
    return connection
