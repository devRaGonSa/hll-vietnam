"""Shared PostgreSQL connection helpers for the staged migration runtime."""

from __future__ import annotations

import hashlib
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from psycopg import Connection, connect
from psycopg.rows import dict_row

from .config import get_postgres_connection_settings, get_postgres_migrations_path


_POSTGRES_MIGRATIONS_APPLIED = False


def connect_postgres(*, autocommit: bool = False) -> Connection:
    """Open one PostgreSQL connection using the shared staged runtime contract."""
    settings = get_postgres_connection_settings()
    connection = connect(
        conninfo=str(settings["dsn"]),
        row_factory=dict_row,
        autocommit=autocommit,
    )
    return connection


class PostgresCompatCursor:
    """Expose a small sqlite-like cursor surface backed by psycopg."""

    def __init__(self, cursor) -> None:
        self._cursor = cursor

    def execute(self, query: str, params: object | None = None) -> "PostgresCompatCursor":
        translated_query = _translate_sqlite_placeholders(query)
        if params is None:
            self._cursor.execute(translated_query)
        else:
            self._cursor.execute(translated_query, params)
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def executemany(
        self,
        query: str,
        params_seq: list[object] | tuple[object, ...],
    ) -> "PostgresCompatCursor":
        translated_query = _translate_sqlite_placeholders(query)
        self._cursor.executemany(translated_query, params_seq)
        return self

    def __iter__(self):
        return iter(self._cursor)

    def __getattr__(self, name: str):
        return getattr(self._cursor, name)


class PostgresCompatConnection:
    """Expose a small sqlite-like connection surface backed by psycopg."""

    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def __enter__(self) -> "PostgresCompatConnection":
        self._connection.__enter__()
        return self

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        self._connection.__exit__(exc_type, exc, exc_tb)

    def execute(self, query: str, params: object | None = None) -> PostgresCompatCursor:
        cursor = self.cursor()
        return cursor.execute(query, params)

    def cursor(self) -> PostgresCompatCursor:
        return PostgresCompatCursor(self._connection.cursor())

    def executescript(self, script: str) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(script)

    def executemany(
        self,
        query: str,
        params_seq: list[object] | tuple[object, ...],
    ) -> PostgresCompatCursor:
        cursor = self.cursor()
        return cursor.executemany(query, params_seq)

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        self._connection.close()

    def __getattr__(self, name: str):
        return getattr(self._connection, name)


@contextmanager
def postgres_cursor(*, autocommit: bool = False) -> Iterator:
    """Yield one PostgreSQL cursor and close the connection afterwards."""
    with connect_postgres(autocommit=autocommit) as connection:
        with connection.cursor() as cursor:
            yield cursor


def connect_postgres_compat(*, autocommit: bool = False) -> PostgresCompatConnection:
    """Open a sqlite-like compatibility wrapper over a PostgreSQL connection."""
    ensure_postgres_migrations_applied()
    return PostgresCompatConnection(connect_postgres(autocommit=autocommit))


def ensure_postgres_migrations_applied() -> list[dict[str, object]]:
    """Apply SQL-first migrations once per process before runtime storage access."""
    global _POSTGRES_MIGRATIONS_APPLIED
    results = apply_postgres_migrations()
    _POSTGRES_MIGRATIONS_APPLIED = True
    return results


def probe_postgres_connection() -> dict[str, object]:
    """Return one small diagnostic payload proving the PostgreSQL bootstrap works."""
    settings = get_postgres_connection_settings()
    with connect_postgres(autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database() AS database_name, current_user AS user_name")
            row = cursor.fetchone() or {}

    return {
        "status": "ok",
        "database_name": row.get("database_name"),
        "user_name": row.get("user_name"),
        "host": settings["host"],
        "port": settings["port"],
        "sslmode": settings["sslmode"],
        "migration_runner_status": settings["migration_runner_status"],
    }


def list_postgres_migration_files() -> list[Path]:
    """Return the ordered SQL migration files for PostgreSQL bootstrap."""
    migrations_root = get_postgres_migrations_path()
    if not migrations_root.exists():
        return []
    return sorted(path for path in migrations_root.glob("*.sql") if path.is_file())


def ensure_postgres_schema_migrations_table(connection: Connection) -> None:
    """Create the schema version tracking table used by the SQL-first runner."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                checksum_sha256 TEXT NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    connection.commit()


def apply_postgres_migrations() -> list[dict[str, object]]:
    """Apply unapplied SQL migration files and record each applied version."""
    global _POSTGRES_MIGRATIONS_APPLIED
    if _POSTGRES_MIGRATIONS_APPLIED:
        return []
    results: list[dict[str, object]] = []
    migration_files = list_postgres_migration_files()
    with connect_postgres() as connection:
        ensure_postgres_schema_migrations_table(connection)
        with connection.cursor() as cursor:
            for migration_path in migration_files:
                version = migration_path.name
                checksum = _calculate_migration_checksum(migration_path)
                cursor.execute(
                    """
                    SELECT checksum_sha256
                    FROM schema_migrations
                    WHERE version = %s
                    """,
                    (version,),
                )
                existing_row = cursor.fetchone()
                if existing_row:
                    existing_checksum = existing_row.get("checksum_sha256")
                    if existing_checksum != checksum:
                        raise RuntimeError(
                            f"Migration {version} was already applied with a different checksum."
                        )
                    results.append(
                        {
                            "version": version,
                            "status": "already-applied",
                            "checksum_sha256": checksum,
                        }
                    )
                    continue

                cursor.execute(migration_path.read_text(encoding="utf-8"))
                cursor.execute(
                    """
                    INSERT INTO schema_migrations (version, checksum_sha256)
                    VALUES (%s, %s)
                    """,
                    (version, checksum),
                )
                results.append(
                    {
                        "version": version,
                        "status": "applied",
                        "checksum_sha256": checksum,
                    }
                )
        connection.commit()
    _POSTGRES_MIGRATIONS_APPLIED = True
    return results


def _calculate_migration_checksum(migration_path: Path) -> str:
    return hashlib.sha256(migration_path.read_bytes()).hexdigest()


def _translate_sqlite_placeholders(query: str) -> str:
    """Convert SQLite qmark placeholders into psycopg positional placeholders."""
    translated: list[str] = []
    in_single_quote = False
    index = 0
    while index < len(query):
        character = query[index]
        if character == "'":
            translated.append(character)
            if in_single_quote and index + 1 < len(query) and query[index + 1] == "'":
                translated.append(query[index + 1])
                index += 2
                continue
            in_single_quote = not in_single_quote
            index += 1
            continue
        if character == "?" and not in_single_quote:
            translated.append("%s")
            index += 1
            continue
        translated.append(character)
        index += 1
    return "".join(translated)
