"""Minimal Hell Let Loose RCON client for live server state queries."""

from __future__ import annotations

import json
import socket
from dataclasses import dataclass

from .config import (
    DEFAULT_RCON_SOURCE_NAME,
    get_rcon_request_timeout_seconds,
    get_rcon_targets_payload,
)


RCON_BUFFER_SIZE = 32768


@dataclass(frozen=True, slots=True)
class RconServerTarget:
    """Configuration needed to query one HLL RCON endpoint."""

    name: str
    host: str
    port: int
    password: str
    source_name: str
    external_server_id: str | None = None
    region: str | None = None
    game_port: int | None = None
    query_port: int | None = None


class HllRconConnection:
    """Tiny synchronous HLL RCON connection using the documented XOR flow."""

    def __init__(self, *, timeout_seconds: float) -> None:
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.settimeout(timeout_seconds)
        self._xor_key: bytes | None = None

    def connect(self, *, host: str, port: int, password: str) -> None:
        self._socket.connect((host, port))
        self._xor_key = self._socket.recv(RCON_BUFFER_SIZE)
        response = self.execute(f"Login {password}")
        if response != "SUCCESS":
            raise RuntimeError("Invalid RCON password.")

    def execute(self, command: str) -> str:
        payload = command.encode("utf-8")
        self._socket.sendall(self._xor(payload))
        return self._receive().decode("utf-8", errors="replace")

    def close(self) -> None:
        try:
            self._socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self._socket.close()

    def _receive(self) -> bytes:
        chunks: list[bytes] = []
        while True:
            chunk = self._socket.recv(RCON_BUFFER_SIZE)
            chunks.append(self._xor(chunk))
            if len(chunk) < RCON_BUFFER_SIZE:
                break
        return b"".join(chunks)

    def _xor(self, payload: bytes) -> bytes:
        if not self._xor_key:
            raise RuntimeError("The HLL server did not provide an RCON XOR key.")
        return bytes(
            value ^ self._xor_key[index % len(self._xor_key)]
            for index, value in enumerate(payload)
        )

    def __enter__(self) -> HllRconConnection:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()


def load_rcon_targets() -> tuple[RconServerTarget, ...]:
    """Load RCON targets from JSON env payload."""
    raw_payload = get_rcon_targets_payload()
    if raw_payload is None:
        return ()
    parsed = json.loads(raw_payload)
    if not isinstance(parsed, list):
        raise ValueError("HLL_BACKEND_RCON_TARGETS must be a JSON array.")
    return tuple(_coerce_rcon_target(item) for item in parsed if isinstance(item, dict))


def query_live_server_state(
    target: RconServerTarget,
    *,
    timeout_seconds: float | None = None,
) -> dict[str, object]:
    """Query one HLL server via RCON and normalize it to the live snapshot shape."""
    resolved_timeout = timeout_seconds or get_rcon_request_timeout_seconds()
    with HllRconConnection(timeout_seconds=resolved_timeout) as connection:
        connection.connect(host=target.host, port=target.port, password=target.password)
        server_name = connection.execute("Get Name").strip()
        slots = connection.execute("Get Slots").strip()
        game_state = connection.execute("Get GameState").strip()

    players, max_players = _parse_slots(slots)
    current_map = _parse_gamestate_value(game_state, "Map")
    resolved_external_id = target.external_server_id or f"rcon:{target.host}:{target.port}"
    return {
        "external_server_id": resolved_external_id,
        "server_name": server_name or target.name,
        "status": "online",
        "players": players,
        "max_players": max_players,
        "current_map": current_map,
        "region": target.region,
        "source_name": target.source_name,
        "snapshot_origin": "real-rcon",
        "source_ref": f"rcon://{target.host}:{target.port}",
    }


def _coerce_rcon_target(raw_target: dict[str, object]) -> RconServerTarget:
    name = str(raw_target.get("name") or "Unnamed RCON target").strip()
    host = str(raw_target.get("host") or "").strip()
    password = str(raw_target.get("password") or "").strip()
    source_name = str(raw_target.get("source_name") or DEFAULT_RCON_SOURCE_NAME).strip()
    port = int(raw_target.get("port") or 0)
    if not host:
        raise ValueError("Each RCON target must define a non-empty host.")
    if port <= 0:
        raise ValueError("Each RCON target must define a valid port.")
    if not password:
        raise ValueError("Each RCON target must define a non-empty password.")

    return RconServerTarget(
        name=name,
        host=host,
        port=port,
        password=password,
        source_name=source_name or DEFAULT_RCON_SOURCE_NAME,
        external_server_id=_string_or_none(raw_target.get("external_server_id")),
        region=_string_or_none(raw_target.get("region")),
        game_port=_coerce_optional_positive_int(raw_target.get("game_port")),
        query_port=_coerce_optional_positive_int(raw_target.get("query_port")),
    )


def _parse_slots(payload: str) -> tuple[int | None, int | None]:
    if "/" not in payload:
        return None, None
    left, right = payload.split("/", 1)
    try:
        return int(left.strip()), int(right.strip())
    except ValueError:
        return None, None


def _parse_gamestate_value(payload: str, label: str) -> str | None:
    prefix = f"{label}:"
    for line in payload.splitlines():
        if line.startswith(prefix):
            value = line.removeprefix(prefix).strip()
            return value or None
    return None


def _string_or_none(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _coerce_optional_positive_int(value: object) -> int | None:
    if value is None:
        return None
    coerced = int(value)
    if coerced <= 0:
        raise ValueError("Configured RCON target ports must be positive when defined.")
    return coerced
