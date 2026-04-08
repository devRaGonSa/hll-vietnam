"""Shared single-writer lock coordination for backend automation jobs."""

from __future__ import annotations

import json
import os
import socket
import sys
import time
import threading
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
CONTAINER_STALE_LOCK_GRACE_SECONDS = 20
CONTAINER_LOCK_HEARTBEAT_INTERVAL_SECONDS = 5.0
CONTAINER_LOCK_HEARTBEAT_STALE_SECONDS = 15.0


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
    heartbeat_stop_event = threading.Event()
    heartbeat_thread = _start_lock_heartbeat(
        lock_path=lock_path,
        lock_token=str(metadata["lock_token"]),
        stop_event=heartbeat_stop_event,
    )
    try:
        yield metadata
    finally:
        heartbeat_stop_event.set()
        if heartbeat_thread is not None:
            heartbeat_thread.join(timeout=CONTAINER_LOCK_HEARTBEAT_INTERVAL_SECONDS)
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
    existing_state = _classify_lock_state(existing_metadata)
    stale_lock_cleared = False
    if existing_state["status"] == "stale-clearable":
        _remove_lock_file(lock_path)
        existing_metadata = None
        existing_state = {
            "status": "stale-cleared",
            "reason": str(existing_state["reason"]),
            "holder_scope": str(existing_state["holder_scope"]),
            "lock_age_seconds": existing_state["lock_age_seconds"],
            "heartbeat_age_seconds": existing_state["heartbeat_age_seconds"],
        }
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
            lock_state=existing_state,
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
        lock_state=existing_state,
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
        lock_state=_classify_lock_state(metadata),
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
        lock_state=_classify_lock_state(existing_metadata),
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
            existing_state = _classify_lock_state(existing_metadata)
            if existing_state["status"] == "stale-clearable":
                _remove_lock_file(lock_path)
                continue
            if time.monotonic() >= deadline:
                raise BackendWriterLockTimeoutError(
                    _build_lock_timeout_message(
                        lock_path=lock_path,
                        holder=holder,
                        timeout_seconds=timeout_seconds,
                        existing_metadata=existing_metadata,
                        lock_state=existing_state,
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
    now_iso = _utc_now_iso()
    return {
        "lock_token": uuid4().hex,
        "holder": holder,
        "started_at": now_iso,
        "heartbeat_at": now_iso,
        "hostname": socket.gethostname(),
        "pid": os.getpid(),
        "cwd": str(Path.cwd()),
        "runtime_scope": "container" if _is_current_process_containerized() else "host",
    }


def _read_lock_metadata(lock_path: Path) -> dict[str, object] | None:
    try:
        return json.loads(lock_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None


def _classify_lock_state(existing_metadata: dict[str, object] | None) -> dict[str, object]:
    if not existing_metadata:
        return {
            "status": "missing",
            "reason": "no-lock-file-present",
            "holder_scope": "none",
            "lock_age_seconds": None,
            "heartbeat_age_seconds": None,
        }

    lock_age_seconds = _calculate_lock_age_seconds(existing_metadata)
    heartbeat_age_seconds = _calculate_lock_age_seconds(existing_metadata, timestamp_key="heartbeat_at")
    holder_scope = _classify_holder_scope(existing_metadata)
    recent_heartbeat = (
        heartbeat_age_seconds is not None
        and heartbeat_age_seconds <= CONTAINER_LOCK_HEARTBEAT_STALE_SECONDS
    )
    holder_pid = _coerce_positive_pid(existing_metadata.get("pid"))

    if holder_scope == "same-host":
        if holder_pid is not None and _is_process_alive(holder_pid):
            return {
                "status": "active",
                "reason": "same-host-process-is-running",
                "holder_scope": holder_scope,
                "lock_age_seconds": lock_age_seconds,
                "heartbeat_age_seconds": heartbeat_age_seconds,
            }
        return {
            "status": "stale-clearable",
            "reason": "same-host-process-is-not-running",
            "holder_scope": holder_scope,
            "lock_age_seconds": lock_age_seconds,
            "heartbeat_age_seconds": heartbeat_age_seconds,
        }

    if _looks_like_containerized_holder(existing_metadata):
        if recent_heartbeat:
            return {
                "status": "active",
                "reason": "cross-container-lock-has-recent-heartbeat",
                "holder_scope": holder_scope,
                "lock_age_seconds": lock_age_seconds,
                "heartbeat_age_seconds": heartbeat_age_seconds,
            }
        if lock_age_seconds is not None and lock_age_seconds < CONTAINER_STALE_LOCK_GRACE_SECONDS:
            return {
                "status": "stale-unsafe",
                "reason": "cross-container-lock-is-still-within-grace-window",
                "holder_scope": holder_scope,
                "lock_age_seconds": lock_age_seconds,
                "heartbeat_age_seconds": heartbeat_age_seconds,
            }
        return {
            "status": "stale-clearable",
            "reason": (
                "cross-container-lock-heartbeat-missing-or-stale"
                if heartbeat_age_seconds is None
                else "cross-container-lock-heartbeat-expired"
            ),
            "holder_scope": holder_scope,
            "lock_age_seconds": lock_age_seconds,
            "heartbeat_age_seconds": heartbeat_age_seconds,
        }

    return {
        "status": "stale-unsafe",
        "reason": "non-container-foreign-host-lock-cannot-be-cleared-safely",
        "holder_scope": holder_scope,
        "lock_age_seconds": lock_age_seconds,
        "heartbeat_age_seconds": heartbeat_age_seconds,
    }


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
    lock_state: dict[str, object],
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
    diagnosis = str(lock_state.get("status") or "unknown")
    reason = str(lock_state.get("reason") or "unknown-reason")
    return (
        f"Writer lock is busy at {lock_path}. Held by {existing_holder} "
        f"since {started_at} on {hostname} (pid {pid}). "
        f"Diagnosis {diagnosis} ({reason}). "
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
    lock_state: dict[str, object] | None = None,
) -> dict[str, object]:
    resolved_lock_state = lock_state or _classify_lock_state(existing_metadata)
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
        "lock_diagnosis": resolved_lock_state.get("status"),
        "lock_reason": resolved_lock_state.get("reason"),
        "active_holder_scope": resolved_lock_state.get("holder_scope"),
        "active_lock_age_seconds": resolved_lock_state.get("lock_age_seconds"),
        "active_heartbeat_age_seconds": resolved_lock_state.get("heartbeat_age_seconds"),
    }
    if corrective_action:
        payload["corrective_action"] = corrective_action
    if existing_metadata:
        payload["active_holder"] = existing_metadata.get("holder")
        payload["active_started_at"] = existing_metadata.get("started_at")
        payload["active_heartbeat_at"] = existing_metadata.get("heartbeat_at")
        payload["active_hostname"] = existing_metadata.get("hostname")
        payload["active_pid"] = existing_metadata.get("pid")
        payload["active_runtime_scope"] = existing_metadata.get("runtime_scope")
    return payload


def _start_lock_heartbeat(
    *,
    lock_path: Path,
    lock_token: str,
    stop_event: threading.Event,
) -> threading.Thread | None:
    interval_seconds = min(
        CONTAINER_LOCK_HEARTBEAT_INTERVAL_SECONDS,
        max(1.0, get_writer_lock_poll_interval_seconds()),
    )
    if interval_seconds <= 0:
        return None

    thread = threading.Thread(
        target=_heartbeat_lock_file,
        kwargs={
            "lock_path": lock_path,
            "lock_token": lock_token,
            "stop_event": stop_event,
            "interval_seconds": interval_seconds,
        },
        name=f"backend-writer-lock-heartbeat-{lock_path.stem}",
        daemon=True,
    )
    thread.start()
    return thread


def _heartbeat_lock_file(
    *,
    lock_path: Path,
    lock_token: str,
    stop_event: threading.Event,
    interval_seconds: float,
) -> None:
    while not stop_event.wait(interval_seconds):
        metadata = _read_lock_metadata(lock_path)
        if not metadata or str(metadata.get("lock_token") or "") != lock_token:
            return
        metadata["heartbeat_at"] = _utc_now_iso()
        _write_lock_metadata(lock_path, metadata, expected_token=lock_token)


def _write_lock_metadata(
    lock_path: Path,
    metadata: dict[str, object],
    *,
    expected_token: str | None = None,
) -> None:
    if expected_token is not None:
        current_metadata = _read_lock_metadata(lock_path)
        if not current_metadata or str(current_metadata.get("lock_token") or "") != expected_token:
            return
    temporary_path = lock_path.with_suffix(f"{lock_path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(metadata, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary_path, lock_path)


def _looks_like_containerized_holder(existing_metadata: dict[str, object]) -> bool:
    runtime_scope = str(existing_metadata.get("runtime_scope") or "").strip().lower()
    if runtime_scope == "container":
        return True
    holder_cwd = str(existing_metadata.get("cwd") or "").strip().lower()
    return holder_cwd.startswith("/app")


def _is_current_process_containerized() -> bool:
    current_cwd = str(Path.cwd()).strip().lower()
    return current_cwd.startswith("/app")


def _classify_holder_scope(existing_metadata: dict[str, object]) -> str:
    holder_hostname = str(existing_metadata.get("hostname") or "").strip()
    if not holder_hostname:
        return "unknown"
    if holder_hostname == socket.gethostname():
        return "same-host"
    if _looks_like_containerized_holder(existing_metadata):
        return "cross-container"
    return "cross-host"


def _coerce_positive_pid(value: object) -> int | None:
    try:
        pid = int(value)
    except (TypeError, ValueError):
        return None
    return pid if pid > 0 else None


def _calculate_lock_age_seconds(
    existing_metadata: dict[str, object],
    *,
    timestamp_key: str = "started_at",
) -> float | None:
    started_at_raw = str(existing_metadata.get(timestamp_key) or "").strip()
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
