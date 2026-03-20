"""Minimal Steam A2S info client for development-time HLL server probes."""

from __future__ import annotations

import argparse
import json
import socket
import struct
from dataclasses import asdict, dataclass


DEFAULT_A2S_TIMEOUT = 6.0
_A2S_PREFIX = b"\xFF\xFF\xFF\xFF"
_A2S_INFO_REQUEST = _A2S_PREFIX + b"\x54Source Engine Query\x00"
_A2S_CHALLENGE_RESPONSE = 0x41
_A2S_INFO_RESPONSE = 0x49


class A2SError(RuntimeError):
    """Base error for A2S query failures."""


class A2STimeoutError(A2SError):
    """Raised when an A2S query does not complete before the timeout."""


class A2SProtocolError(A2SError):
    """Raised when an A2S server returns an unexpected payload."""


@dataclass(frozen=True, slots=True)
class A2SServerInfo:
    """Minimal metadata returned by an A2S info query."""

    host: str
    query_port: int
    server_name: str
    map_name: str | None
    players: int
    max_players: int
    protocol: int
    folder: str | None = None
    game: str | None = None
    version: str | None = None


def query_server_info(
    host: str,
    query_port: int,
    *,
    timeout: float = DEFAULT_A2S_TIMEOUT,
) -> A2SServerInfo:
    """Query one server using A2S_INFO and return minimal reusable metadata."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.settimeout(timeout)
        address = (host, query_port)

        try:
            udp_socket.sendto(_A2S_INFO_REQUEST, address)
            payload = _receive_packet(udp_socket)
            if _is_challenge_packet(payload):
                challenge = payload[5:9]
                udp_socket.sendto(_A2S_INFO_REQUEST + challenge, address)
                payload = _receive_packet(udp_socket)
        except socket.timeout as error:
            raise A2STimeoutError(
                f"A2S query to {host}:{query_port} timed out after {timeout:.1f}s."
            ) from error
        except OSError as error:
            raise A2SError(
                f"A2S query to {host}:{query_port} failed: {error}."
            ) from error

    return _parse_info_payload(payload, host=host, query_port=query_port)


def main() -> None:
    """Allow a direct development-time probe of one A2S target."""
    parser = argparse.ArgumentParser(description="Probe one server with A2S_INFO.")
    parser.add_argument("host", help="Server hostname or IPv4 address.")
    parser.add_argument("query_port", type=int, help="Server Steam query port.")
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_A2S_TIMEOUT,
        help="Socket timeout in seconds.",
    )
    args = parser.parse_args()

    payload = asdict(
        query_server_info(args.host, args.query_port, timeout=args.timeout)
    )
    print(json.dumps(payload, indent=2))


def _receive_packet(udp_socket: socket.socket) -> bytes:
    payload, _ = udp_socket.recvfrom(4096)
    return payload


def _is_challenge_packet(payload: bytes) -> bool:
    return (
        len(payload) >= 9
        and payload.startswith(_A2S_PREFIX)
        and payload[4] == _A2S_CHALLENGE_RESPONSE
    )


def _parse_info_payload(
    payload: bytes,
    *,
    host: str,
    query_port: int,
) -> A2SServerInfo:
    if len(payload) < 6 or not payload.startswith(_A2S_PREFIX):
        raise A2SProtocolError("A2S response did not include the expected packet header.")
    if payload[4] != _A2S_INFO_RESPONSE:
        raise A2SProtocolError(
            f"A2S response type {payload[4]!r} is not an info response."
        )

    protocol = payload[5]
    offset = 6
    server_name, offset = _read_c_string(payload, offset)
    map_name, offset = _read_c_string(payload, offset)
    folder, offset = _read_c_string(payload, offset)
    game, offset = _read_c_string(payload, offset)
    offset += 2  # app id
    players = _read_byte(payload, offset)
    max_players = _read_byte(payload, offset + 1)
    offset += 6  # players, max, bots, server type, environment, visibility
    offset += 1  # vac
    version, offset = _read_c_string(payload, offset)

    if offset < len(payload):
        extra_data_flag = payload[offset]
        offset += 1
        if extra_data_flag & 0x80:
            offset += 2
        if extra_data_flag & 0x10:
            _, offset = _read_c_string(payload, offset)
        if extra_data_flag & 0x40:
            offset += 2
            offset += 8
        if extra_data_flag & 0x20:
            offset += 8

    return A2SServerInfo(
        host=host,
        query_port=query_port,
        server_name=server_name or "Unknown server",
        map_name=map_name or None,
        players=players,
        max_players=max_players,
        protocol=protocol,
        folder=folder or None,
        game=game or None,
        version=version or None,
    )


def _read_c_string(payload: bytes, offset: int) -> tuple[str, int]:
    end = payload.find(b"\x00", offset)
    if end == -1:
        raise A2SProtocolError("A2S response ended before a null-terminated string.")
    return payload[offset:end].decode("utf-8", errors="replace"), end + 1


def _read_byte(payload: bytes, offset: int) -> int:
    if offset >= len(payload):
        raise A2SProtocolError("A2S response ended before expected integer fields.")
    return struct.unpack_from("<B", payload, offset)[0]


if __name__ == "__main__":
    main()
