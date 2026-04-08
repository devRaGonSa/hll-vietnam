"""Shared PostgreSQL connection helpers for the staged migration runtime."""

from __future__ import annotations

import hashlib
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from psycopg import Connection, connect
from psycopg.rows import dict_row

from .config import get_postgres_connection_settings, get_postgres_migrations_path


def connect_postgres(*, autocommit: bool = False) -> Connection:
    """Open one PostgreSQL connection using the shared staged runtime contract."""
    settings = get_postgres_connection_settings()
    connection = connect(
        conninfo=str(settings["dsn"]),
        row_factory=dict_row,
        autocommit=autocommit,
    )
    return connection


@contextmanager
def postgres_cursor(*, autocommit: bool = False) -> Iterator:
    """Yield one PostgreSQL cursor and close the connection afterwards."""
    with connect_postgres(autocommit=autocommit) as connection:
        with connection.cursor() as cursor:
            yield cursor


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
    return results


def _calculate_migration_checksum(migration_path: Path) -> str:
    return hashlib.sha256(migration_path.read_bytes()).hexdigest()
