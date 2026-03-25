"""Minimal Hell Let Loose RCON client for live server state queries."""

from __future__ import annotations

import base64
import itertools
import json
import socket
import struct
from dataclasses import dataclass

from .config import (
    DEFAULT_RCON_SOURCE_NAME,
    get_rcon_request_timeout_seconds,
    get_rcon_targets_payload,
)


RCON_BUFFER_SIZE = 32768
RCON_HEADER_FORMAT = "<II"
RCON_PROTOCOL_VERSION = 2


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
    """Synchronous HLL RCON v2 connection for lightweight live status queries."""

    def __init__(self, *, timeout_seconds: float) -> None:
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.settimeout(timeout_seconds)
        self._xor_key: bytes | None = None
        self._auth_token: str | None = None
        self._request_ids = itertools.count(1)

    def connect(self, *, host: str, port: int, password: str) -> None:
        self._socket.connect((host, port))

        server_connect_response = self._exchange("ServerConnect", "")
        xor_key_b64 = _expect_text_content(server_connect_response, command_name="ServerConnect")
        try:
            self._xor_key = base64.b64decode(xor_key_b64)
        except (ValueError, TypeError) as error:
            raise RuntimeError("The HLL server returned an invalid RCON XOR key.") from error
        if not self._xor_key:
            raise RuntimeError("The HLL server returned an empty RCON XOR key.")

        login_response = self._exchange("Login", password)
        self._auth_token = _expect_text_content(login_response, command_name="Login")
        if not self._auth_token:
            raise RuntimeError("The HLL server returned an empty RCON auth token.")

    def execute_json(
        self,
        command: str,
        content: dict[str, object] | str = "",
    ) -> dict[str, object]:
        response = self._exchange(command, content)
        content_body = response.get("contentBody")
        if isinstance(content_body, dict):
            return content_body
        if isinstance(content_body, str):
            try:
                parsed = json.loads(content_body)
            except json.JSONDecodeError as error:
                raise RuntimeError(
                    f"The HLL server returned invalid JSON content for {command}."
                ) from error
            if isinstance(parsed, dict):
                return parsed
        raise RuntimeError(f"The HLL server returned an unexpected payload for {command}.")

    def close(self) -> None:
        try:
            self._socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self._socket.close()

    def _exchange(
        self,
        command: str,
        content: dict[str, object] | str = "",
    ) -> dict[str, object]:
        request_id = next(self._request_ids)
        self._send_request(request_id=request_id, command=command, content=content)
        response = self._receive_response()
        response_request_id = int(response.get("requestId") or 0)
        if response_request_id != request_id:
            raise RuntimeError(
                f"Unexpected RCON response id {response_request_id} for request {request_id}."
            )
        _raise_for_status(response, command_name=command)
        return response

    def _send_request(
        self,
        *,
        request_id: int,
        command: str,
        content: dict[str, object] | str,
    ) -> None:
        content_body = (
            content
            if isinstance(content, str)
            else json.dumps(content, separators=(",", ":"))
        )
        body = json.dumps(
            {
                "authToken": self._auth_token or "",
                "version": RCON_PROTOCOL_VERSION,
                "name": command,
                "contentBody": content_body,
            },
            separators=(",", ":"),
        ).encode("utf-8")
        header = struct.pack(RCON_HEADER_FORMAT, request_id, len(body))
        self._socket.sendall(header + self._xor(body))

    def _receive_response(self) -> dict[str, object]:
        header_size = struct.calcsize(RCON_HEADER_FORMAT)
        header_bytes = self._recv_exact(header_size)
        try:
            request_id, body_length = struct.unpack(RCON_HEADER_FORMAT, header_bytes)
        except struct.error as error:
            raise RuntimeError("The HLL server returned an invalid RCON response header.") from error
        if body_length <= 0:
            raise RuntimeError("The HLL server returned an empty RCON response body.")

        body = self._xor(self._recv_exact(body_length))
        try:
            parsed = json.loads(body.decode("utf-8", errors="replace"))
        except json.JSONDecodeError as error:
            raise RuntimeError("The HLL server returned malformed RCON JSON.") from error
        if not isinstance(parsed, dict):
            raise RuntimeError("The HLL server returned a non-object RCON response.")

        parsed["requestId"] = request_id
        return parsed

    def _recv_exact(self, expected_length: int) -> bytes:
        chunks = bytearray()
        while len(chunks) < expected_length:
            chunk = self._socket.recv(min(RCON_BUFFER_SIZE, expected_length - len(chunks)))
            if not chunk:
                raise RuntimeError("The HLL RCON connection closed unexpectedly.")
            chunks.extend(chunk)
        return bytes(chunks)

    def _xor(self, payload: bytes) -> bytes:
        if not self._xor_key:
            return payload
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
    sample = query_live_server_sample(target, timeout_seconds=timeout_seconds)
    return dict(sample["normalized"])


def query_live_server_sample(
    target: RconServerTarget,
    *,
    timeout_seconds: float | None = None,
) -> dict[str, object]:
    """Query one HLL server and return both normalized and raw session data."""
    resolved_timeout = timeout_seconds or get_rcon_request_timeout_seconds()
    with HllRconConnection(timeout_seconds=resolved_timeout) as connection:
        connection.connect(host=target.host, port=target.port, password=target.password)
        session = connection.execute_json(
            "GetServerInformation",
            {"Name": "session", "Value": ""},
        )

    resolved_external_id = target.external_server_id or f"rcon:{target.host}:{target.port}"
    return {
        "target": {
            "target_key": build_rcon_target_key(target),
            "name": target.name,
            "host": target.host,
            "port": target.port,
            "external_server_id": target.external_server_id,
            "region": target.region,
            "game_port": target.game_port,
            "query_port": target.query_port,
            "source_name": target.source_name,
        },
        "normalized": {
            "external_server_id": resolved_external_id,
            "server_name": _string_or_none(session.get("serverName")) or target.name,
            "status": "online",
            "players": _coerce_optional_int(session.get("playerCount")),
            "max_players": _coerce_optional_int(session.get("maxPlayerCount")),
            "current_map": (
                _string_or_none(session.get("mapId")) or _string_or_none(session.get("mapName"))
            ),
            "region": target.region,
            "source_name": target.source_name,
            "snapshot_origin": "real-rcon",
            "source_ref": f"rcon://{target.host}:{target.port}",
        },
        "raw_session": session,
    }


def build_rcon_target_key(target: RconServerTarget) -> str:
    """Build a stable local key for one configured RCON target."""
    external_server_id = _string_or_none(target.external_server_id)
    if external_server_id:
        return external_server_id
    return f"rcon:{target.host}:{target.port}"


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


def _raise_for_status(response: dict[str, object], *, command_name: str) -> None:
    status_code = int(response.get("statusCode") or 0)
    if status_code == 200:
        return
    status_message = _string_or_none(response.get("statusMessage")) or "Unknown RCON error."
    raise RuntimeError(f"{command_name} failed with RCON status {status_code}: {status_message}")


def _expect_text_content(response: dict[str, object], *, command_name: str) -> str:
    content = response.get("contentBody")
    if isinstance(content, str):
        return content
    raise RuntimeError(f"The HLL server returned unexpected text content for {command_name}.")


def _string_or_none(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _coerce_optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_optional_positive_int(value: object) -> int | None:
    if value is None:
        return None
    coerced = int(value)
    if coerced <= 0:
        raise ValueError("Configured RCON target ports must be positive when defined.")
    return coerced
