"""Shared PostgreSQL advisory-lock coordination for backend automation jobs."""

from __future__ import annotations

import hashlib
import socket
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone

from .config import (
    get_postgres_advisory_lock_poll_interval_seconds,
    get_postgres_advisory_lock_timeout_seconds,
    get_postgres_connection_settings,
    get_sqlite_busy_timeout_ms,
    get_sqlite_writer_timeout_seconds,
)
from .postgres_utils import connect_postgres


class BackendWriterLockTimeoutError(RuntimeError):
    """Raised when the shared backend writer lock cannot be acquired in time."""


class BackendWriterLockConflictError(RuntimeError):
    """Raised when a manual command detects an active conflicting backend writer."""

    def __init__(self, message: str, *, payload: dict[str, object]):
        super().__init__(message)
        self.payload = payload

def _build_lock_key_pair(namespace: str) -> tuple[int, int]:
    digest = hashlib.sha256(namespace.encode("utf-8")).digest()
    return (
        int.from_bytes(digest[:4], byteorder="big", signed=True),
        int.from_bytes(digest[4:8], byteorder="big", signed=True),
    )


LOCK_NAMESPACE = "hll-vietnam:backend-single-writer"
_LOCK_KEY_CLASS_ID, _LOCK_KEY_OBJECT_ID = _build_lock_key_pair(LOCK_NAMESPACE)
_ACTIVE_LOCK_DEPTH = 0
_ACTIVE_LOCK_CONNECTION = None
_ACTIVE_LOCK_METADATA: dict[str, object] | None = None


@contextmanager
def backend_writer_lock(
    *,
    holder: str,
    storage_path=None,
    timeout_seconds: float | None = None,
    poll_interval_seconds: float | None = None,
):
    """Acquire the shared PostgreSQL advisory lock with reentrant safety per process."""
    del storage_path
    global _ACTIVE_LOCK_CONNECTION, _ACTIVE_LOCK_DEPTH, _ACTIVE_LOCK_METADATA

    if _ACTIVE_LOCK_CONNECTION is not None:
        _ACTIVE_LOCK_DEPTH += 1
        try:
            yield dict(_ACTIVE_LOCK_METADATA or {})
        finally:
            _ACTIVE_LOCK_DEPTH -= 1
            if _ACTIVE_LOCK_DEPTH <= 0:
                _ACTIVE_LOCK_DEPTH = 0
                _ACTIVE_LOCK_CONNECTION = None
                _ACTIVE_LOCK_METADATA = None
        return

    metadata = _acquire_backend_writer_lock(
        holder=holder,
        timeout_seconds=(
            get_postgres_advisory_lock_timeout_seconds()
            if timeout_seconds is None
            else timeout_seconds
        ),
        poll_interval_seconds=(
            get_postgres_advisory_lock_poll_interval_seconds()
            if poll_interval_seconds is None
            else poll_interval_seconds
        ),
    )
    _ACTIVE_LOCK_CONNECTION = metadata.pop("connection")
    _ACTIVE_LOCK_METADATA = metadata
    _ACTIVE_LOCK_DEPTH = 1
    try:
        yield dict(metadata)
    finally:
        _release_backend_writer_lock()
        _ACTIVE_LOCK_DEPTH = 0
        _ACTIVE_LOCK_CONNECTION = None
        _ACTIVE_LOCK_METADATA = None


def build_writer_lock_holder(label: str) -> str:
    """Build one readable holder label from the current command line."""
    argv = " ".join(sys.argv).strip()
    if argv:
        return f"{label} [{argv}]"
    return label


def check_manual_writer_lock_preflight(
    *,
    holder: str,
    storage_path=None,
) -> dict[str, object]:
    """Fail fast for manual commands when another backend writer is already active."""
    del storage_path
    existing_metadata = _fetch_active_writer_lock_metadata()
    if existing_metadata:
        payload = _build_writer_lock_payload(
            status="aborted-conflict-detected-before-wait",
            holder=holder,
            existing_metadata=existing_metadata,
            waited_seconds=0.0,
            message=(
                "Another backend writer already holds the PostgreSQL advisory lock. "
                "Stop the running backend worker, scheduled job, or containerized daemon "
                "before retrying this manual command."
            ),
            corrective_action=(
                "Retry after the active backend writer shown in active_holder releases the "
                "PostgreSQL advisory lock or its session exits."
            ),
        )
        raise BackendWriterLockConflictError(str(payload["message"]), payload=payload)

    return _build_writer_lock_payload(
        status="ready-no-conflict-detected",
        holder=holder,
        existing_metadata=None,
        waited_seconds=0.0,
        message=(
            "No active conflicting PostgreSQL advisory lock holder was detected before "
            "starting the manual command."
        ),
    )


def build_acquired_writer_lock_payload(
    *,
    holder: str,
    metadata: dict[str, object] | None,
    storage_path=None,
    waited_seconds: float = 0.0,
) -> dict[str, object]:
    """Return one structured payload for a successfully acquired writer lock."""
    del storage_path
    return _build_writer_lock_payload(
        status="acquired",
        holder=holder,
        existing_metadata=metadata,
        waited_seconds=waited_seconds,
        message="Manual command acquired the shared PostgreSQL advisory lock.",
    )


def build_writer_lock_timeout_payload(
    *,
    holder: str,
    storage_path=None,
    waited_seconds: float | None = None,
) -> dict[str, object]:
    """Return one structured payload for a writer-lock timeout."""
    del storage_path
    resolved_wait = (
        get_postgres_advisory_lock_timeout_seconds()
        if waited_seconds is None
        else waited_seconds
    )
    existing_metadata = _fetch_active_writer_lock_metadata()
    return _build_writer_lock_payload(
        status="timed-out",
        holder=holder,
        existing_metadata=existing_metadata,
        waited_seconds=resolved_wait,
        message="The manual command timed out while waiting for the PostgreSQL advisory lock.",
        corrective_action=(
            "Retry after the active backend writer shown in active_holder releases the "
            "PostgreSQL advisory lock or its database session exits."
        ),
    )


def _acquire_backend_writer_lock(
    *,
    holder: str,
    timeout_seconds: float,
    poll_interval_seconds: float,
) -> dict[str, object]:
    if timeout_seconds < 0:
        raise ValueError("Writer lock timeout must be zero or positive.")
    if poll_interval_seconds <= 0:
        raise ValueError("Writer lock poll interval must be positive.")

    deadline = time.monotonic() + timeout_seconds
    application_name = _normalize_postgres_application_name(holder)
    connection = connect_postgres(autocommit=True)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT set_config('application_name', %s, false)",
                (application_name,),
            )
        metadata = _build_lock_metadata(holder=holder, application_name=application_name)
        while True:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_try_advisory_lock(%s, %s) AS lock_acquired",
                    (_LOCK_KEY_CLASS_ID, _LOCK_KEY_OBJECT_ID),
                )
                row = cursor.fetchone() or {}
            if bool(row.get("lock_acquired")):
                metadata["connection"] = connection
                return metadata
            if time.monotonic() >= deadline:
                existing_metadata = _fetch_active_writer_lock_metadata()
                raise BackendWriterLockTimeoutError(
                    _build_lock_timeout_message(
                        holder=holder,
                        timeout_seconds=timeout_seconds,
                        existing_metadata=existing_metadata,
                    )
                )
            time.sleep(poll_interval_seconds)
    except Exception:
        connection.close()
        raise


def _release_backend_writer_lock() -> None:
    connection = _ACTIVE_LOCK_CONNECTION
    if connection is None:
        return
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_advisory_unlock(%s, %s)",
                (_LOCK_KEY_CLASS_ID, _LOCK_KEY_OBJECT_ID),
            )
    except Exception:
        pass
    finally:
        connection.close()


def _build_lock_metadata(*, holder: str, application_name: str) -> dict[str, object]:
    settings = get_postgres_connection_settings()
    return {
        "lock_backend": "postgresql-session-advisory-lock",
        "lock_scope": "backend-single-writer",
        "lock_namespace": LOCK_NAMESPACE,
        "lock_key_class_id": _LOCK_KEY_CLASS_ID,
        "lock_key_object_id": _LOCK_KEY_OBJECT_ID,
        "holder": holder,
        "started_at": _utc_now_iso(),
        "hostname": socket.gethostname(),
        "pid": _current_backend_pid(),
        "runtime_scope": "database-session",
        "postgres_host": settings["host"],
        "postgres_port": settings["port"],
        "postgres_database": settings["database"],
        "postgres_user": settings["user"],
        "postgres_application_name": application_name,
        "stale_lock_strategy": "automatic-release-on-session-close",
    }


def _fetch_active_writer_lock_metadata() -> dict[str, object] | None:
    connection = connect_postgres(autocommit=True)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    l.pid AS postgres_pid,
                    a.application_name,
                    a.usename,
                    a.client_addr::text AS client_addr,
                    a.backend_start,
                    a.state,
                    a.wait_event_type,
                    a.wait_event,
                    a.query_start,
                    a.query
                FROM pg_locks AS l
                LEFT JOIN pg_stat_activity AS a
                    ON a.pid = l.pid
                WHERE l.locktype = 'advisory'
                  AND l.classid = %s
                  AND l.objid = %s
                  AND l.mode = 'ExclusiveLock'
                  AND l.granted = TRUE
                  AND l.pid <> pg_backend_pid()
                ORDER BY a.backend_start ASC NULLS LAST, l.pid ASC
                LIMIT 1
                """,
                (_LOCK_KEY_CLASS_ID, _LOCK_KEY_OBJECT_ID),
            )
            row = cursor.fetchone()
    finally:
        connection.close()

    if not row:
        return None

    return {
        "holder": row.get("application_name") or "unknown-holder",
        "started_at": _serialize_timestamp(row.get("backend_start")),
        "active_hostname": row.get("client_addr") or "database-local-session",
        "active_pid": row.get("postgres_pid"),
        "active_runtime_scope": "postgresql-session",
        "postgres_user": row.get("usename"),
        "postgres_application_name": row.get("application_name"),
        "postgres_state": row.get("state"),
        "postgres_wait_event_type": row.get("wait_event_type"),
        "postgres_wait_event": row.get("wait_event"),
        "postgres_query_started_at": _serialize_timestamp(row.get("query_start")),
        "postgres_query": _normalize_query_text(row.get("query")),
        "lock_age_seconds": _calculate_lock_age_seconds(row.get("backend_start")),
        "heartbeat_age_seconds": None,
        "holder_scope": "postgresql-session",
        "reason": "advisory-lock-held-by-active-postgresql-session",
        "status": "active",
    }


def _build_lock_timeout_message(
    *,
    holder: str,
    timeout_seconds: float,
    existing_metadata: dict[str, object] | None,
) -> str:
    if not existing_metadata:
        return (
            "PostgreSQL advisory lock could not be acquired within "
            f"{timeout_seconds:.1f}s for {holder}, but no active holder metadata was visible."
        )

    active_holder = existing_metadata.get("holder") or "unknown-holder"
    started_at = existing_metadata.get("started_at") or "unknown-started-at"
    postgres_pid = existing_metadata.get("active_pid") or "unknown-pid"
    return (
        "PostgreSQL advisory lock is busy. Held by "
        f"{active_holder} since {started_at} on backend pid {postgres_pid}. "
        f"Timed out after waiting {timeout_seconds:.1f}s for {holder}."
    )


def _build_writer_lock_payload(
    *,
    status: str,
    holder: str,
    existing_metadata: dict[str, object] | None,
    waited_seconds: float,
    message: str,
    corrective_action: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": status,
        "holder": holder,
        "lock_backend": "postgresql-session-advisory-lock",
        "lock_scope": "backend-single-writer",
        "lock_namespace": LOCK_NAMESPACE,
        "lock_key_class_id": _LOCK_KEY_CLASS_ID,
        "lock_key_object_id": _LOCK_KEY_OBJECT_ID,
        "waited_seconds": round(max(0.0, waited_seconds), 3),
        "postgres_advisory_lock_timeout_seconds": get_postgres_advisory_lock_timeout_seconds(),
        "postgres_advisory_lock_poll_interval_seconds": get_postgres_advisory_lock_poll_interval_seconds(),
        "sqlite_writer_timeout_seconds": get_sqlite_writer_timeout_seconds(),
        "sqlite_busy_timeout_ms": get_sqlite_busy_timeout_ms(),
        "sqlite_runtime_role": "transitional-legacy-only",
        "stale_lock_strategy": "automatic-release-on-session-close",
        "message": message,
    }
    if corrective_action:
        payload["corrective_action"] = corrective_action
    if existing_metadata:
        payload["lock_diagnosis"] = existing_metadata.get("status")
        payload["lock_reason"] = existing_metadata.get("reason")
        payload["active_holder_scope"] = existing_metadata.get("holder_scope")
        payload["active_lock_age_seconds"] = existing_metadata.get("lock_age_seconds")
        payload["active_heartbeat_age_seconds"] = existing_metadata.get("heartbeat_age_seconds")
        payload["active_holder"] = existing_metadata.get("holder")
        payload["active_started_at"] = existing_metadata.get("started_at")
        payload["active_hostname"] = existing_metadata.get("active_hostname")
        payload["active_pid"] = existing_metadata.get("active_pid")
        payload["active_runtime_scope"] = existing_metadata.get("active_runtime_scope")
        payload["active_postgres_user"] = existing_metadata.get("postgres_user")
        payload["active_postgres_application_name"] = existing_metadata.get(
            "postgres_application_name"
        )
        payload["active_postgres_state"] = existing_metadata.get("postgres_state")
        payload["active_postgres_wait_event_type"] = existing_metadata.get(
            "postgres_wait_event_type"
        )
        payload["active_postgres_wait_event"] = existing_metadata.get(
            "postgres_wait_event"
        )
        payload["active_postgres_query_started_at"] = existing_metadata.get(
            "postgres_query_started_at"
        )
        payload["active_postgres_query"] = existing_metadata.get("postgres_query")
    else:
        payload["lock_diagnosis"] = "not-held"
        payload["lock_reason"] = "no-active-postgresql-advisory-lock-holder-visible"
        payload["active_holder_scope"] = "none"
        payload["active_lock_age_seconds"] = None
        payload["active_heartbeat_age_seconds"] = None
    return payload


def _normalize_postgres_application_name(holder: str) -> str:
    compact_holder = " ".join(holder.split())
    if len(compact_holder) <= 63:
        return compact_holder
    suffix = hashlib.sha1(compact_holder.encode("utf-8")).hexdigest()[:8]
    return f"{compact_holder[:54]}-{suffix}"


def _serialize_timestamp(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    text = str(value).strip()
    return text or None


def _calculate_lock_age_seconds(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        started_at = value
    else:
        raw_value = str(value).strip()
        if not raw_value:
            return None
        try:
            started_at = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - started_at.astimezone(timezone.utc)
    return max(0.0, delta.total_seconds())


def _normalize_query_text(query: object) -> str | None:
    if not isinstance(query, str):
        return None
    compact_query = " ".join(query.split())
    return compact_query[:240] if compact_query else None


def _current_backend_pid() -> int:
    connection = connect_postgres(autocommit=True)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_backend_pid() AS pid")
            row = cursor.fetchone() or {}
    finally:
        connection.close()
    return int(row.get("pid") or 0)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
