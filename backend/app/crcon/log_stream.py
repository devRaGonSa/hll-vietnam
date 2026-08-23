"""Bounded process-local consumer for CRCON 12.0.1 structured log streams."""

from __future__ import annotations

import json
from collections import deque
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from threading import Event, Lock, Thread
from typing import Protocol
from urllib.parse import urlsplit, urlunsplit

from websocket import (  # type: ignore[import-untyped]
    WebSocketBadStatusException,
    WebSocketTimeoutException,
    create_connection,
)


CRCON_CURRENT_MATCH_ACTIONS = ("KILL", "TEAM KILL")
CRCON_LOG_STREAM_BUFFER_SIZE = 18
CRCON_LOG_STREAM_BACKOFF_SECONDS = (1.0, 2.0, 4.0, 8.0, 15.0)
CRCON_LOG_STREAM_SOCKET_TIMEOUT_SECONDS = 1.0


class CrconLogStreamStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    DISABLED = "DISABLED"
    AUTH_FAILED = "AUTH_FAILED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class CrconLogStreamTarget:
    """Private runtime websocket configuration; never serialize this object."""

    server_slug: str
    base_url: str
    bearer_token: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class CrconCurrentMatchEvent:
    event_id: str
    timestamp: datetime
    action: str
    killer_id: str | None
    killer_name: str | None
    victim_id: str | None
    victim_name: str | None
    weapon: str | None
    teamkill: bool


@dataclass(frozen=True, slots=True)
class CrconLogStreamBatch:
    events: tuple[CrconCurrentMatchEvent, ...]
    last_seen_id: str | None
    error: str | None


@dataclass(frozen=True, slots=True)
class CrconLogStreamWindow:
    events: tuple[CrconCurrentMatchEvent, ...]
    status: CrconLogStreamStatus
    gap_detected: bool
    reason: str | None
    last_seen_id: str | None
    truncated: bool


class WebSocketConnection(Protocol):
    def send(self, payload: str) -> object: ...

    def recv(self) -> str | bytes | None: ...

    def close(self) -> object: ...


ConnectionFactory = Callable[[str, tuple[str, ...], float], WebSocketConnection]
BackoffWaiter = Callable[[Event, float], bool]


class _TargetBuffer:
    def __init__(self, max_events: int) -> None:
        self._events: deque[CrconCurrentMatchEvent] = deque(maxlen=max_events)
        self._seen_ids: set[str] = set()
        self._lock = Lock()
        self._last_order_key: tuple[int, int] | None = None
        self._last_seen_id: str | None = None
        self._match_id: str | None = None
        self._status = CrconLogStreamStatus.UNAVAILABLE
        self._reason: str | None = "crcon-log-stream-not-started"
        self._gap_detected = False
        self._truncated = False

    @property
    def last_seen_id(self) -> str | None:
        with self._lock:
            return self._last_seen_id

    def update_status(
        self,
        status: CrconLogStreamStatus,
        reason: str | None,
    ) -> None:
        with self._lock:
            self._status = status
            self._reason = reason

    def mark_invalid_cursor(self) -> None:
        with self._lock:
            self._last_seen_id = None
            self._gap_detected = True
            self._status = CrconLogStreamStatus.UNAVAILABLE
            self._reason = "crcon-log-stream-invalid-cursor"

    def record(self, batch: CrconLogStreamBatch) -> None:
        with self._lock:
            for event in batch.events:
                if event.action not in CRCON_CURRENT_MATCH_ACTIONS:
                    continue
                order_key = _stream_order_key(event.event_id)
                if event.event_id in self._seen_ids:
                    continue
                if (
                    self._last_order_key is not None
                    and order_key is not None
                    and order_key <= self._last_order_key
                ):
                    continue
                if len(self._events) == self._events.maxlen and self._events:
                    evicted = self._events[0]
                    self._seen_ids.discard(evicted.event_id)
                    self._truncated = True
                self._events.append(event)
                self._seen_ids.add(event.event_id)
                if order_key is not None:
                    self._last_order_key = order_key
            if batch.last_seen_id:
                self._last_seen_id = batch.last_seen_id
            self._status = CrconLogStreamStatus.AVAILABLE
            self._reason = None

    def window_for_match(
        self,
        match_id: str,
        started_at: datetime,
    ) -> CrconLogStreamWindow:
        boundary = _ensure_utc(started_at)
        with self._lock:
            transitioned = self._match_id is not None and self._match_id != match_id
            if self._match_id != match_id:
                self._match_id = match_id
                if transitioned:
                    self._gap_detected = False
                    self._truncated = False
            retained = tuple(
                event for event in self._events if event.timestamp >= boundary
            )
            if len(retained) != len(self._events):
                self._events = deque(retained, maxlen=self._events.maxlen)
                self._seen_ids = {event.event_id for event in retained}
            return CrconLogStreamWindow(
                events=retained,
                status=self._status,
                gap_detected=self._gap_detected,
                reason=self._reason,
                last_seen_id=self._last_seen_id,
                truncated=self._truncated,
            )


class CrconLogStreamManager:
    """Own exactly one reconnecting consumer and bounded buffer per target."""

    def __init__(
        self,
        targets: Sequence[CrconLogStreamTarget],
        *,
        buffer_size: int = CRCON_LOG_STREAM_BUFFER_SIZE,
        connection_factory: ConnectionFactory | None = None,
        backoff_seconds: Sequence[float] = CRCON_LOG_STREAM_BACKOFF_SECONDS,
        waiter: BackoffWaiter | None = None,
        socket_timeout_seconds: float = CRCON_LOG_STREAM_SOCKET_TIMEOUT_SECONDS,
    ) -> None:
        if buffer_size < 1:
            raise ValueError("buffer_size must be positive.")
        if not backoff_seconds or any(delay < 0 for delay in backoff_seconds):
            raise ValueError("backoff_seconds must contain non-negative delays.")
        by_slug: dict[str, CrconLogStreamTarget] = {}
        for target in targets:
            slug = target.server_slug.strip()
            if not slug or slug in by_slug:
                raise ValueError("CRCON Log Stream targets need unique server slugs.")
            if not target.bearer_token:
                raise ValueError("CRCON Log Stream bearer token must be non-empty.")
            by_slug[slug] = target
        self._targets = by_slug
        self._buffers = {
            slug: _TargetBuffer(buffer_size) for slug in self._targets
        }
        self._connection_factory = connection_factory or _open_websocket
        self._backoff_seconds = tuple(float(delay) for delay in backoff_seconds)
        self._waiter = waiter or (lambda stop, delay: stop.wait(delay))
        self._socket_timeout_seconds = socket_timeout_seconds
        self._stop = Event()
        self._lifecycle_lock = Lock()
        self._connection_lock = Lock()
        self._threads: dict[str, Thread] = {}
        self._connections: dict[str, WebSocketConnection] = {}

    @property
    def target_slugs(self) -> tuple[str, ...]:
        return tuple(self._targets)

    def start(self) -> None:
        with self._lifecycle_lock:
            if self._threads:
                return
            self._stop.clear()
            for slug, target in self._targets.items():
                thread = Thread(
                    target=self._consume_target,
                    args=(target,),
                    name=f"crcon-log-stream-{slug}",
                    daemon=True,
                )
                self._threads[slug] = thread
                thread.start()

    def stop(self, *, timeout_seconds: float = 3.0) -> None:
        with self._lifecycle_lock:
            threads = tuple(self._threads.items())
            self._stop.set()
            with self._connection_lock:
                connections = tuple(self._connections.values())
            for connection in connections:
                try:
                    connection.close()
                except Exception:  # noqa: BLE001 - shutdown remains best effort
                    pass
            for _slug, thread in threads:
                thread.join(timeout=timeout_seconds)
            self._threads = {
                slug: thread for slug, thread in threads if thread.is_alive()
            }

    def window_for_match(
        self,
        server_slug: str,
        match_id: str,
        started_at: datetime,
    ) -> CrconLogStreamWindow:
        buffer = self._buffers.get(str(server_slug or "").strip())
        if buffer is None:
            return CrconLogStreamWindow(
                events=(),
                status=CrconLogStreamStatus.UNAVAILABLE,
                gap_detected=False,
                reason="crcon-log-stream-credential-unconfigured",
                last_seen_id=None,
                truncated=False,
            )
        return buffer.window_for_match(match_id, started_at)

    def _consume_target(self, target: CrconLogStreamTarget) -> None:
        buffer = self._buffers[target.server_slug]
        backoff_index = 0
        while not self._stop.is_set():
            connection: WebSocketConnection | None = None
            received_success = False
            try:
                headers = (f"Authorization: Bearer {target.bearer_token}",)
                connection = self._connection_factory(
                    _websocket_url(target.base_url),
                    headers,
                    self._socket_timeout_seconds,
                )
                with self._connection_lock:
                    self._connections[target.server_slug] = connection
                connection.send(
                    json.dumps(
                        {
                            "last_seen_id": buffer.last_seen_id,
                            "actions": list(CRCON_CURRENT_MATCH_ACTIONS),
                        },
                        separators=(",", ":"),
                    )
                )
                while not self._stop.is_set():
                    try:
                        raw_payload = connection.recv()
                    except WebSocketTimeoutException:
                        continue
                    if raw_payload in {None, "", b""}:
                        raise ConnectionError("CRCON Log Stream disconnected.")
                    batch = parse_log_stream_payload(raw_payload)
                    if batch.error:
                        classification = _classify_stream_error(batch.error)
                        if classification == "invalid-cursor":
                            buffer.mark_invalid_cursor()
                        elif classification == "disabled":
                            buffer.update_status(
                                CrconLogStreamStatus.DISABLED,
                                "crcon-log-stream-disabled",
                            )
                        else:
                            buffer.update_status(
                                CrconLogStreamStatus.UNAVAILABLE,
                                "crcon-log-stream-error",
                            )
                        break
                    buffer.record(batch)
                    received_success = True
                    backoff_index = 0
            except WebSocketBadStatusException as error:
                status_code = getattr(error, "status_code", None)
                if status_code in {401, 403}:
                    buffer.update_status(
                        CrconLogStreamStatus.AUTH_FAILED,
                        "crcon-log-stream-auth-failed",
                    )
                else:
                    buffer.update_status(
                        CrconLogStreamStatus.UNAVAILABLE,
                        "crcon-log-stream-unavailable",
                    )
            except Exception:  # noqa: BLE001 - consumer must survive transport failures
                buffer.update_status(
                    CrconLogStreamStatus.UNAVAILABLE,
                    "crcon-log-stream-unavailable",
                )
            finally:
                with self._connection_lock:
                    self._connections.pop(target.server_slug, None)
                if connection is not None:
                    try:
                        connection.close()
                    except Exception:  # noqa: BLE001 - reconnect must continue
                        pass
            if self._stop.is_set():
                break
            if received_success:
                backoff_index = 0
            delay = self._backoff_seconds[
                min(backoff_index, len(self._backoff_seconds) - 1)
            ]
            if self._waiter(self._stop, delay):
                break
            backoff_index = min(backoff_index + 1, len(self._backoff_seconds) - 1)


def parse_log_stream_payload(raw_payload: str | bytes) -> CrconLogStreamBatch:
    """Parse one CRCON 12.0.1 websocket response without retaining raw logs."""
    try:
        payload = json.loads(raw_payload)
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("CRCON Log Stream payload is not valid JSON.") from None
    if not isinstance(payload, Mapping):
        raise ValueError("CRCON Log Stream payload must be a JSON object.")
    raw_logs = payload.get("logs", [])
    if not isinstance(raw_logs, list):
        raise ValueError("CRCON Log Stream logs must be a JSON array.")
    events: list[CrconCurrentMatchEvent] = []
    for item in raw_logs:
        if not isinstance(item, Mapping):
            continue
        event_id = _text(item.get("id"))
        structured = item.get("log")
        if event_id is None or not isinstance(structured, Mapping):
            continue
        action = _text(structured.get("action"))
        timestamp = _event_timestamp(structured)
        if action not in CRCON_CURRENT_MATCH_ACTIONS or timestamp is None:
            continue
        events.append(
            CrconCurrentMatchEvent(
                event_id=event_id,
                timestamp=timestamp,
                action=action,
                killer_id=_text(structured.get("player_id_1")),
                killer_name=_text(structured.get("player_name_1")),
                victim_id=_text(structured.get("player_id_2")),
                victim_name=_text(structured.get("player_name_2")),
                weapon=_text(structured.get("weapon")),
                teamkill=action == "TEAM KILL",
            )
        )
    return CrconLogStreamBatch(
        events=tuple(events),
        last_seen_id=_text(payload.get("last_seen_id")),
        error=_text(payload.get("error")),
    )


def _open_websocket(
    url: str,
    headers: tuple[str, ...],
    timeout_seconds: float,
) -> WebSocketConnection:
    return create_connection(
        url,
        header=list(headers),
        timeout=timeout_seconds,
    )


def _websocket_url(base_url: str) -> str:
    parsed = urlsplit(str(base_url or "").strip().rstrip("/"))
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("CRCON Log Stream base URL must be an HTTP(S) origin.")
    scheme = "wss" if parsed.scheme == "https" else "ws"
    path = f"{parsed.path.rstrip('/')}/ws/logs"
    return urlunsplit((scheme, parsed.netloc, path, "", ""))


def _event_timestamp(payload: Mapping[str, object]) -> datetime | None:
    timestamp_ms = payload.get("timestamp_ms")
    if isinstance(timestamp_ms, (int, float)) and not isinstance(timestamp_ms, bool):
        return datetime.fromtimestamp(float(timestamp_ms) / 1000.0, UTC)
    event_time = _text(payload.get("event_time"))
    if event_time is None:
        return None
    try:
        parsed = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
    except ValueError:
        return None
    return _ensure_utc(parsed)


def _classify_stream_error(message: str) -> str:
    normalized = message.casefold().replace("_", " ")
    if "not enabled" in normalized or "disabled" in normalized:
        return "disabled"
    if "invalid stream id" in normalized or "streaminvalidid" in normalized:
        return "invalid-cursor"
    return "error"


def _stream_order_key(event_id: str) -> tuple[int, int] | None:
    try:
        milliseconds, sequence = event_id.split("-", 1)
        return int(milliseconds), int(sequence)
    except (ValueError, TypeError):
        return None


def _text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
