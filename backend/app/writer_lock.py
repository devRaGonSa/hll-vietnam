"""Shared single-writer lock coordination for backend automation jobs."""

from __future__ import annotations

import json
import os
import socket
import sys
import time
import ctypes
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .config import (
    get_storage_path,
    get_sqlite_busy_timeout_ms,
    get_sqlite_writer_timeout_seconds,
    get_writer_lock_poll_interval_seconds,
    get_writer_lock_timeout_seconds,
)


class BackendWriterLockTimeoutError(RuntimeError):
    """Raised when the shared backend writer lock cannot be acquired in time."""


class BackendWriterLockConflictError(RuntimeError):
    """Raised when a manual command detects an active conflicting backend writer."""

    def __init__(self, message: str, *, payload: dict[str, object]):
        super().__init__(message)
        self.payload = payload


_ACTIVE_LOCK_DEPTH_BY_PATH: dict[Path, int] = {}
_ACTIVE_LOCK_TOKEN_BY_PATH: dict[Path, str] = {}
CONTAINER_STALE_LOCK_GRACE_SECONDS = 300


def resolve_backend_writer_lock_path(*, storage_path: Path | None = None) -> Path:
    """Return the shared lock path derived from the configured SQLite storage path."""
    resolved_storage_path = storage_path or get_storage_path()
    return resolved_storage_path.parent / f"{resolved_storage_path.stem}.writer.lock"


@contextmanager
def backend_writer_lock(
    *,
    holder: str,
    storage_path: Path | None = None,
    timeout_seconds: float | None = None,
    poll_interval_seconds: float | None = None,
):
    """Acquire the shared backend writer lock with reentrant safety per process."""
    lock_path = resolve_backend_writer_lock_path(storage_path=storage_path).resolve()
    if lock_path in _ACTIVE_LOCK_DEPTH_BY_PATH:
        _ACTIVE_LOCK_DEPTH_BY_PATH[lock_path] += 1
        try:
            yield _read_lock_metadata(lock_path)
        finally:
            _ACTIVE_LOCK_DEPTH_BY_PATH[lock_path] -= 1
            if _ACTIVE_LOCK_DEPTH_BY_PATH[lock_path] <= 0:
                _ACTIVE_LOCK_DEPTH_BY_PATH.pop(lock_path, None)
                _ACTIVE_LOCK_TOKEN_BY_PATH.pop(lock_path, None)
        return

    metadata = _acquire_backend_writer_lock(
        lock_path=lock_path,
        holder=holder,
        timeout_seconds=get_writer_lock_timeout_seconds()
        if timeout_seconds is None
        else timeout_seconds,
        poll_interval_seconds=get_writer_lock_poll_interval_seconds()
        if poll_interval_seconds is None
        else poll_interval_seconds,
    )
    _ACTIVE_LOCK_DEPTH_BY_PATH[lock_path] = 1
    _ACTIVE_LOCK_TOKEN_BY_PATH[lock_path] = str(metadata["lock_token"])
    try:
        yield metadata
    finally:
        _release_backend_writer_lock(lock_path)
        _ACTIVE_LOCK_DEPTH_BY_PATH.pop(lock_path, None)
        _ACTIVE_LOCK_TOKEN_BY_PATH.pop(lock_path, None)


def build_writer_lock_holder(label: str) -> str:
    """Build one readable holder label from the current command line."""
    argv = " ".join(sys.argv).strip()
    if argv:
        return f"{label} [{argv}]"
    return label


def check_manual_writer_lock_preflight(
    *,
    holder: str,
    storage_path: Path | None = None,
) -> dict[str, object]:
    """Fail fast for manual commands when another backend writer is already active."""
    lock_path = resolve_backend_writer_lock_path(storage_path=storage_path).resolve()
    existing_metadata = _read_lock_metadata(lock_path)
    stale_lock_cleared = False
    if _can_clear_stale_lock(existing_metadata):
        _remove_lock_file(lock_path)
        existing_metadata = None
        stale_lock_cleared = True

    if existing_metadata:
        payload = _build_writer_lock_payload(
            status="aborted-conflict-detected-before-wait",
            holder=holder,
            lock_path=lock_path,
            existing_metadata=existing_metadata,
            waited_seconds=0.0,
            message=(
                "Another backend writer is active. Stop the running backend worker, "
                "scheduled job, or containerized daemon before retrying this manual command."
            ),
            corrective_action=(
                "Stop or disable the active backend writer shown in active_holder, then rerun "
                "the manual command."
            ),
        )
        raise BackendWriterLockConflictError(str(payload["message"]), payload=payload)

    return _build_writer_lock_payload(
        status="ready-no-conflict-detected",
        holder=holder,
        lock_path=lock_path,
        existing_metadata=None,
        waited_seconds=0.0,
        message=(
            "No active conflicting backend writer was detected before starting the manual command."
        ),
        stale_lock_cleared=stale_lock_cleared,
    )


def build_acquired_writer_lock_payload(
    *,
    holder: str,
    metadata: dict[str, object] | None,
    storage_path: Path | None = None,
    waited_seconds: float = 0.0,
) -> dict[str, object]:
    """Return one structured payload for a successfully acquired writer lock."""
    return _build_writer_lock_payload(
        status="acquired",
        holder=holder,
        lock_path=resolve_backend_writer_lock_path(storage_path=storage_path).resolve(),
        existing_metadata=metadata,
        waited_seconds=waited_seconds,
        message="Manual command acquired the shared backend writer lock.",
    )


def build_writer_lock_timeout_payload(
    *,
    holder: str,
    storage_path: Path | None = None,
    waited_seconds: float | None = None,
) -> dict[str, object]:
    """Return one structured payload for a writer-lock timeout or late contention race."""
    resolved_wait = (
        get_writer_lock_timeout_seconds() if waited_seconds is None else waited_seconds
    )
    lock_path = resolve_backend_writer_lock_path(storage_path=storage_path).resolve()
    existing_metadata = _read_lock_metadata(lock_path)
    return _build_writer_lock_payload(
        status="timed-out",
        holder=holder,
        lock_path=lock_path,
        existing_metadata=existing_metadata,
        waited_seconds=resolved_wait,
        message=(
            "The manual command timed out while waiting for the shared backend writer lock."
        ),
        corrective_action=(
            "Stop or disable the active backend writer shown in active_holder before retrying "
            "this manual command."
        ),
    )


def _acquire_backend_writer_lock(
    *,
    lock_path: Path,
    holder: str,
    timeout_seconds: float,
    poll_interval_seconds: float,
) -> dict[str, object]:
    if timeout_seconds < 0:
        raise ValueError("Writer lock timeout must be zero or positive.")
    if poll_interval_seconds <= 0:
        raise ValueError("Writer lock poll interval must be positive.")

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout_seconds
    metadata = _build_lock_metadata(holder=holder)

    while True:
        try:
            file_descriptor = os.open(
                lock_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            )
        except FileExistsError:
            existing_metadata = _read_lock_metadata(lock_path)
            if _can_clear_stale_lock(existing_metadata):
                _remove_lock_file(lock_path)
                continue
            if time.monotonic() >= deadline:
                raise BackendWriterLockTimeoutError(
                    _build_lock_timeout_message(
                        lock_path=lock_path,
                        holder=holder,
                        timeout_seconds=timeout_seconds,
                        existing_metadata=existing_metadata,
                    )
                )
            time.sleep(poll_interval_seconds)
            continue

        try:
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
                json.dump(metadata, handle, ensure_ascii=True, indent=2)
                handle.write("\n")
            return metadata
        except Exception:
            _remove_lock_file(lock_path)
            raise


def _release_backend_writer_lock(lock_path: Path) -> None:
    expected_token = _ACTIVE_LOCK_TOKEN_BY_PATH.get(lock_path)
    existing_metadata = _read_lock_metadata(lock_path)
    if existing_metadata and expected_token and existing_metadata.get("lock_token") != expected_token:
        return
    _remove_lock_file(lock_path)


def _remove_lock_file(lock_path: Path) -> None:
    try:
        lock_path.unlink()
    except FileNotFoundError:
        return


def _build_lock_metadata(*, holder: str) -> dict[str, object]:
    return {
        "lock_token": uuid4().hex,
        "holder": holder,
        "started_at": _utc_now_iso(),
        "hostname": socket.gethostname(),
        "pid": os.getpid(),
        "cwd": str(Path.cwd()),
    }


def _read_lock_metadata(lock_path: Path) -> dict[str, object] | None:
    try:
        return json.loads(lock_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None


def _can_clear_stale_lock(existing_metadata: dict[str, object] | None) -> bool:
    if not existing_metadata:
        return False
    try:
        holder_pid = int(existing_metadata.get("pid"))
    except (TypeError, ValueError):
        return False
    if holder_pid <= 0:
        return False

    holder_hostname = str(existing_metadata.get("hostname") or "").strip()
    current_hostname = socket.gethostname()
    if holder_hostname == current_hostname:
        if _is_process_alive(holder_pid):
            return False
        return True
    if not _looks_like_containerized_holder(existing_metadata):
        return False
    lock_age_seconds = _calculate_lock_age_seconds(existing_metadata)
    if lock_age_seconds is None:
        return False
    if lock_age_seconds < CONTAINER_STALE_LOCK_GRACE_SECONDS:
        return False
    return True


def _is_process_alive(pid: int) -> bool:
    if pid == os.getpid():
        return True
    if os.name == "nt":
        process_query_limited_information = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(
            process_query_limited_information,
            False,
            pid,
        )
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        last_error = ctypes.GetLastError()
        if last_error in {5}:
            return True
        if last_error in {87, 1168}:
            return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError as exc:
        winerror = getattr(exc, "winerror", None)
        if winerror in {3, 87} or exc.errno in {3}:
            return False
        return True
    return True


def _build_lock_timeout_message(
    *,
    lock_path: Path,
    holder: str,
    timeout_seconds: float,
    existing_metadata: dict[str, object] | None,
) -> str:
    if not existing_metadata:
        return (
            f"Writer lock is busy at {lock_path} and could not be acquired within "
            f"{timeout_seconds:.1f}s for {holder}."
        )

    existing_holder = existing_metadata.get("holder") or "unknown-holder"
    started_at = existing_metadata.get("started_at") or "unknown-started-at"
    hostname = existing_metadata.get("hostname") or "unknown-host"
    pid = existing_metadata.get("pid") or "unknown-pid"
    return (
        f"Writer lock is busy at {lock_path}. Held by {existing_holder} "
        f"since {started_at} on {hostname} (pid {pid}). "
        f"Timed out after waiting {timeout_seconds:.1f}s for {holder}."
    )


def _build_writer_lock_payload(
    *,
    status: str,
    holder: str,
    lock_path: Path,
    existing_metadata: dict[str, object] | None,
    waited_seconds: float,
    message: str,
    corrective_action: str | None = None,
    stale_lock_cleared: bool = False,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": status,
        "holder": holder,
        "lock_path": str(lock_path),
        "waited_seconds": round(max(0.0, waited_seconds), 3),
        "writer_lock_timeout_seconds": get_writer_lock_timeout_seconds(),
        "writer_lock_poll_interval_seconds": get_writer_lock_poll_interval_seconds(),
        "sqlite_writer_timeout_seconds": get_sqlite_writer_timeout_seconds(),
        "sqlite_busy_timeout_ms": get_sqlite_busy_timeout_ms(),
        "message": message,
        "stale_lock_cleared": stale_lock_cleared,
    }
    if corrective_action:
        payload["corrective_action"] = corrective_action
    if existing_metadata:
        payload["active_holder"] = existing_metadata.get("holder")
        payload["active_started_at"] = existing_metadata.get("started_at")
        payload["active_hostname"] = existing_metadata.get("hostname")
        payload["active_pid"] = existing_metadata.get("pid")
    return payload


def _looks_like_containerized_holder(existing_metadata: dict[str, object]) -> bool:
    holder_cwd = str(existing_metadata.get("cwd") or "").strip().lower()
    return holder_cwd.startswith("/app")


def _calculate_lock_age_seconds(existing_metadata: dict[str, object]) -> float | None:
    started_at_raw = str(existing_metadata.get("started_at") or "").strip()
    if not started_at_raw:
        return None
    try:
        started_at = datetime.fromisoformat(started_at_raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - started_at.astimezone(timezone.utc)
    return max(0.0, delta.total_seconds())


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
