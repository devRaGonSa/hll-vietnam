"""Minimal Hell Let Loose RCON client for live server state queries."""

from __future__ import annotations

import base64
import itertools
import json
import socket
import struct
from collections.abc import Mapping
from dataclasses import dataclass

from .config import (
    DEFAULT_RCON_SOURCE_NAME,
    get_rcon_request_timeout_seconds,
    get_rcon_targets_payload,
)


RCON_BUFFER_SIZE = 32768
RCON_HEADER_FORMAT = "<III"
RCON_MAGIC_HEADER_VALUE = 0xDE450508
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


class RconQueryError(RuntimeError):
    """Normalized RCON query failure with a machine-readable error type."""

    def __init__(
        self,
        error_type: str,
        message: str,
        *,
        error_stage: str | None = None,
    ) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.error_stage = error_stage


class HllRconConnection:
    """Synchronous HLL RCON v2 connection for lightweight live status queries."""

    def __init__(self, *, timeout_seconds: float) -> None:
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.settimeout(timeout_seconds)
        self._xor_key: bytes | None = None
        self._auth_token: str | None = None
        self._request_ids = itertools.count(1)
        self._current_stage = "tcp_connect"

    def connect(self, *, host: str, port: int, password: str) -> None:
        self._run_socket_stage(
            "tcp_connect",
            lambda: self._socket.connect((host, port)),
        )

        server_connect_response = self._exchange(
            "ServerConnect",
            "",
            request_stage="server_connect_request",
            response_stage="server_connect_response",
        )
        self._current_stage = "xor_key_decode"
        xor_key_b64 = _expect_text_content(server_connect_response, command_name="ServerConnect")
        try:
            self._xor_key = base64.b64decode(xor_key_b64)
        except (ValueError, TypeError) as error:
            raise RconQueryError(
                "payload-invalid",
                "The HLL server returned an invalid RCON XOR key.",
                error_stage="xor_key_decode",
            ) from error
        if not self._xor_key:
            raise RconQueryError(
                "unexpected-response",
                "The HLL server returned an empty RCON XOR key.",
                error_stage="xor_key_decode",
            )

        login_response = self._exchange(
            "Login",
            password,
            request_stage="login_request",
            response_stage="login_response",
        )
        self._auth_token = _expect_text_content(login_response, command_name="Login")
        if not self._auth_token:
            raise RconQueryError(
                "unexpected-response",
                "The HLL server returned an empty RCON auth token.",
                error_stage="login_response",
            )

    def execute_json(
        self,
        command: str,
        content: dict[str, object] | str = "",
    ) -> dict[str, object]:
        stage_prefix = _resolve_command_stage_prefix(command)
        response = self._exchange(
            command,
            content,
            request_stage=f"{stage_prefix}_request",
            response_stage=f"{stage_prefix}_response",
        )
        self._current_stage = "payload_decode"
        content_body = response.get("contentBody")
        if isinstance(content_body, dict):
            return content_body
        if isinstance(content_body, str):
            try:
                parsed = json.loads(content_body)
            except json.JSONDecodeError as error:
                raise RconQueryError(
                    "payload-invalid",
                    f"The HLL server returned invalid JSON content for {command}.",
                    error_stage="payload_decode",
                ) from error
            if isinstance(parsed, dict):
                return parsed
        raise RconQueryError(
            "unexpected-response",
            f"The HLL server returned an unexpected payload for {command}.",
            error_stage="unexpected_response",
        )

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
        *,
        request_stage: str,
        response_stage: str,
    ) -> dict[str, object]:
        request_id = next(self._request_ids)
        self._send_request(
            request_id=request_id,
            command=command,
            content=content,
            request_stage=request_stage,
        )
        response = self._receive_response(response_stage=response_stage)
        response_request_id = int(response.get("requestId") or 0)
        if response_request_id != request_id:
            raise RconQueryError(
                "unexpected-response",
                f"Unexpected RCON response id {response_request_id} for request {request_id}.",
                error_stage="unexpected_response",
            )
        _raise_for_status(response, command_name=command, error_stage=response_stage)
        return response

    def _send_request(
        self,
        *,
        request_id: int,
        command: str,
        content: dict[str, object] | str,
        request_stage: str,
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
        header = struct.pack(
            RCON_HEADER_FORMAT,
            RCON_MAGIC_HEADER_VALUE,
            request_id,
            len(body),
        )
        self._run_socket_stage(
            request_stage,
            lambda: self._socket.sendall(header + self._xor(body)),
        )

    def _receive_response(self, *, response_stage: str) -> dict[str, object]:
        header_size = struct.calcsize(RCON_HEADER_FORMAT)
        header_bytes = self._recv_exact(
            header_size,
            stage=response_stage,
            receive_context="response header",
        )
        try:
            magic_value, request_id, body_length = struct.unpack(
                RCON_HEADER_FORMAT,
                header_bytes,
            )
        except struct.error as error:
            raise RconQueryError(
                "payload-invalid",
                "The HLL server returned an invalid RCON response header.",
                error_stage=response_stage,
            ) from error
        if magic_value != RCON_MAGIC_HEADER_VALUE:
            raise RconQueryError(
                "invalid-magic",
                (
                    "The HLL server returned an unexpected RCON magic value: "
                    f"{magic_value:#x} (expected {RCON_MAGIC_HEADER_VALUE:#x})."
                ),
                error_stage=response_stage,
            )
        if body_length <= 0:
            raise RconQueryError(
                "unexpected-response",
                "The HLL server returned an empty RCON response body.",
                error_stage=response_stage,
            )

        body = self._xor(self._recv_body(body_length, stage=response_stage))
        try:
            parsed = json.loads(body.decode("utf-8", errors="replace"))
        except json.JSONDecodeError as error:
            raise RconQueryError(
                "payload-invalid",
                "The HLL server returned malformed RCON JSON.",
                error_stage="payload_decode",
            ) from error
        if not isinstance(parsed, dict):
            raise RconQueryError(
                "unexpected-response",
                "The HLL server returned a non-object RCON response.",
                error_stage="unexpected_response",
            )

        parsed["requestId"] = request_id
        return parsed

    def _recv_body(self, expected_length: int, *, stage: str) -> bytes:
        chunks = bytearray()
        original_timeout = self._socket.gettimeout()
        body_timeout_seconds = min(3.0, original_timeout or 3.0)
        self._socket.settimeout(body_timeout_seconds)
        try:
            while len(chunks) < expected_length:
                self._current_stage = stage
                try:
                    chunk = self._socket.recv(
                        min(RCON_BUFFER_SIZE, expected_length - len(chunks))
                    )
                except (TimeoutError, socket.timeout) as error:
                    raise RconQueryError(
                        "timeout",
                        (
                            f"Timed out during {stage} while waiting for response body "
                            f"({len(chunks)}/{expected_length} bytes received)."
                        ),
                        error_stage=stage,
                    ) from error
                except OSError as error:
                    raise RconQueryError(
                        _classify_socket_error_type(error),
                        f"RCON socket error during {stage}: {error}",
                        error_stage=stage,
                    ) from error
                if not chunk:
                    raise RconQueryError(
                        "connection-closed",
                        (
                            "The HLL RCON connection closed unexpectedly while waiting for "
                            f"response body ({len(chunks)}/{expected_length} bytes received)."
                        ),
                        error_stage=stage,
                    )
                chunks.extend(chunk)
        finally:
            self._socket.settimeout(original_timeout)
        return bytes(chunks)

    def _recv_exact(
        self,
        expected_length: int,
        *,
        stage: str,
        receive_context: str,
    ) -> bytes:
        chunks = bytearray()
        while len(chunks) < expected_length:
            self._current_stage = stage
            try:
                chunk = self._socket.recv(min(RCON_BUFFER_SIZE, expected_length - len(chunks)))
            except (TimeoutError, socket.timeout) as error:
                raise RconQueryError(
                    "timeout",
                    (
                        f"Timed out during {stage} while waiting for {receive_context} "
                        f"({len(chunks)}/{expected_length} bytes received)."
                    ),
                    error_stage=stage,
                ) from error
            except OSError as error:
                raise RconQueryError(
                    _classify_socket_error_type(error),
                    f"RCON socket error during {stage}: {error}",
                    error_stage=stage,
                ) from error
            if not chunk:
                raise RconQueryError(
                    "connection-closed",
                    (
                        "The HLL RCON connection closed unexpectedly while waiting for "
                        f"{receive_context} ({len(chunks)}/{expected_length} bytes received)."
                    ),
                    error_stage=stage,
                )
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

    def _run_socket_stage(self, stage: str, operation: object) -> object:
        self._current_stage = stage
        try:
            return operation()
        except (TimeoutError, socket.timeout) as error:
            raise RconQueryError(
                "timeout",
                f"Timed out during {stage}.",
                error_stage=stage,
            ) from error
        except OSError as error:
            raise RconQueryError(
                _classify_socket_error_type(error),
                f"RCON socket error during {stage}: {error}",
                error_stage=stage,
            ) from error


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
    try:
        with HllRconConnection(timeout_seconds=resolved_timeout) as connection:
            connection.connect(host=target.host, port=target.port, password=target.password)
            session = connection.execute_json(
                "GetServerInformation",
                {"Name": "session", "Value": ""},
            )
    except RconQueryError:
        raise
    except (TimeoutError, socket.timeout) as error:
        raise RconQueryError(
            "timeout",
            f"Timed out after {resolved_timeout:.1f}s while querying {target.host}:{target.port}.",
        ) from error
    except ConnectionRefusedError as error:
        raise RconQueryError(
            "connection-refused",
            f"Connection refused by {target.host}:{target.port}.",
        ) from error
    except OSError as error:
        raise RconQueryError(
            _classify_socket_error_type(error),
            f"RCON socket error against {target.host}:{target.port}: {error}",
        ) from error
    except RuntimeError as error:
        raise RconQueryError(
            _classify_runtime_error_type(error),
            str(error),
            error_stage=getattr(error, "error_stage", None),
        ) from error

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
    slug = _string_or_none(raw_target.get("slug"))
    external_server_id = _string_or_none(raw_target.get("external_server_id")) or slug
    name = _string_or_none(raw_target.get("name")) or _slug_to_display_name(slug) or "Unnamed RCON target"
    host = _required_string(raw_target, "host")
    password = _required_string(raw_target, "password")
    source_name = _string_or_none(raw_target.get("source_name")) or DEFAULT_RCON_SOURCE_NAME
    port = _required_positive_int(raw_target, "port")
    if not host:
        raise ValueError("Each RCON target must define a non-empty 'host'.")
    if port <= 0:
        raise ValueError("Each RCON target must define a positive 'port'.")
    if not password:
        raise ValueError("Each RCON target must define a non-empty 'password'.")

    return RconServerTarget(
        name=name,
        host=host,
        port=port,
        password=password,
        source_name=source_name or DEFAULT_RCON_SOURCE_NAME,
        external_server_id=external_server_id,
        region=_string_or_none(raw_target.get("region")),
        game_port=_coerce_optional_positive_int(raw_target.get("game_port")),
        query_port=_coerce_optional_positive_int(raw_target.get("query_port")),
    )


def _raise_for_status(
    response: dict[str, object],
    *,
    command_name: str,
    error_stage: str,
) -> None:
    status_code = int(response.get("statusCode") or 0)
    if status_code == 200:
        return
    status_message = _string_or_none(response.get("statusMessage")) or "Unknown RCON error."
    if command_name == "Login" and status_code in {401, 403}:
        raise RconQueryError(
            "auth/login",
            f"{command_name} failed with RCON status {status_code}: {status_message}",
            error_stage=error_stage,
        )
    raise RconQueryError(
        "unexpected-response",
        f"{command_name} failed with RCON status {status_code}: {status_message}",
        error_stage=error_stage,
    )


def _expect_text_content(response: dict[str, object], *, command_name: str) -> str:
    content = response.get("contentBody")
    if isinstance(content, str):
        return content
    raise RconQueryError(
        "unexpected-response",
        f"The HLL server returned unexpected text content for {command_name}.",
        error_stage="unexpected_response",
    )


def _resolve_command_stage_prefix(command: str) -> str:
    normalized_command = str(command or "").strip().lower()
    stage_prefix_by_command = {
        "serverconnect": "server_connect",
        "login": "login",
        "getserverinformation": "get_server_information",
    }
    return stage_prefix_by_command.get(normalized_command, normalized_command or "rcon_command")


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


def _required_string(raw_target: Mapping[str, object], field_name: str) -> str:
    value = _string_or_none(raw_target.get(field_name))
    if value is None:
        available_fields = ", ".join(sorted(raw_target.keys()))
        raise ValueError(
            f"Each RCON target must define a non-empty '{field_name}'. "
            f"Available fields: {available_fields or 'none'}."
        )
    return value


def _required_positive_int(raw_target: Mapping[str, object], field_name: str) -> int:
    raw_value = raw_target.get(field_name)
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as error:
        available_fields = ", ".join(sorted(raw_target.keys()))
        raise ValueError(
            f"Each RCON target must define a valid integer '{field_name}'. "
            f"Available fields: {available_fields or 'none'}."
        ) from error
    if value <= 0:
        raise ValueError(f"Each RCON target must define a positive '{field_name}'.")
    return value


def _slug_to_display_name(slug: str | None) -> str | None:
    normalized_slug = _string_or_none(slug)
    if normalized_slug is None:
        return None
    if normalized_slug.startswith("comunidad-hispana-"):
        suffix = normalized_slug.removeprefix("comunidad-hispana-")
        if suffix.isdigit():
            return f"Comunidad Hispana #{suffix.zfill(2)}"
    parts = [part for part in normalized_slug.replace("_", "-").split("-") if part]
    if not parts:
        return None
    return " ".join(part.upper() if part.isdigit() else part.capitalize() for part in parts)


def _classify_socket_error_type(error: OSError) -> str:
    if isinstance(error, TimeoutError):
        return "timeout"
    if isinstance(error, ConnectionRefusedError):
        return "connection-refused"
    if getattr(error, "errno", None) in {10060, 110, 60}:
        return "timeout"
    return "other-error"


def _classify_runtime_error_type(error: RuntimeError) -> str:
    message = str(error).lower()
    if "auth token" in message or "login failed" in message or "status 401" in message or "status 403" in message:
        return "auth/login"
    if "invalid magic" in message:
        return "invalid-magic"
    if "closed unexpectedly" in message or "closed connection" in message:
        return "connection-closed"
    if "invalid json" in message or "unexpected payload" in message or "malformed" in message or "invalid rcon" in message:
        return "payload-invalid"
    if "timed out" in message:
        return "timeout"
    if "unexpected" in message:
        return "unexpected-response"
    return "other-error"
