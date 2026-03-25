"""Shared single-writer lock coordination for backend automation jobs."""

from __future__ import annotations

import json
import os
import socket
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .config import (
    get_storage_path,
    get_writer_lock_poll_interval_seconds,
    get_writer_lock_timeout_seconds,
)


class BackendWriterLockTimeoutError(RuntimeError):
    """Raised when the shared backend writer lock cannot be acquired in time."""


_ACTIVE_LOCK_DEPTH_BY_PATH: dict[Path, int] = {}
_ACTIVE_LOCK_TOKEN_BY_PATH: dict[Path, str] = {}


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
    if str(existing_metadata.get("hostname") or "") != socket.gethostname():
        return False
    try:
        holder_pid = int(existing_metadata.get("pid"))
    except (TypeError, ValueError):
        return False
    if holder_pid <= 0:
        return False
    return not _is_process_alive(holder_pid)


def _is_process_alive(pid: int) -> bool:
    if pid == os.getpid():
        return True
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


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
