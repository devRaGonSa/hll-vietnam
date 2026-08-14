"""Strictly read-only CRCON PostgreSQL capability adapter."""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from .capabilities import PROBED_TABLES, build_capability_report
from .models import CrconCapabilityReport, CrconDatabaseError


APPLICATION_NAME = "hll-vietnam-bff"
SCHEMA_COLUMNS_SQL = """
SELECT table_name, column_name
FROM information_schema.columns
WHERE table_schema = current_schema()
  AND table_name = ANY(%s)
ORDER BY table_name, ordinal_position
"""

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
