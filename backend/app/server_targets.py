"""Registry helpers for development-time A2S probe targets."""

from __future__ import annotations

import json
from dataclasses import dataclass

from .config import DEFAULT_A2S_SOURCE_NAME, get_a2s_targets_payload


DEFAULT_A2S_TARGETS = (
    {
        "name": "Comunidad Hispana #01",
        "host": "152.114.195.174",
        "query_port": 7778,
        "game_port": 7777,
        "source_name": DEFAULT_A2S_SOURCE_NAME,
        "external_server_id": "comunidad-hispana-01",
        "region": "ES",
    },
    {
        "name": "Comunidad Hispana #02",
        "host": "152.114.195.150",
        "query_port": 7878,
        "game_port": 7877,
        "source_name": DEFAULT_A2S_SOURCE_NAME,
        "external_server_id": "comunidad-hispana-02",
        "region": "ES",
    },
)


@dataclass(frozen=True, slots=True)
class A2SServerTarget:
    """Minimal configuration needed to query one A2S target."""

    name: str
    host: str
    query_port: int
    game_port: int | None
    source_name: str
    external_server_id: str | None = None
    region: str | None = None


def load_a2s_targets() -> tuple[A2SServerTarget, ...]:
    """Load configured A2S targets from env JSON or the local default registry."""
    raw_payload = get_a2s_targets_payload()
    raw_targets = DEFAULT_A2S_TARGETS if raw_payload is None else _parse_targets(raw_payload)
    return tuple(_coerce_target(item) for item in raw_targets)


def _parse_targets(raw_payload: str) -> list[dict[str, object]]:
    try:
        parsed = json.loads(raw_payload)
    except json.JSONDecodeError as error:
        raise ValueError("HLL_BACKEND_A2S_TARGETS must be valid JSON.") from error

    if not isinstance(parsed, list):
        raise ValueError("HLL_BACKEND_A2S_TARGETS must be a JSON array.")

    return [item for item in parsed if isinstance(item, dict)]


def _coerce_target(raw_target: dict[str, object]) -> A2SServerTarget:
    name = str(raw_target.get("name") or "Unnamed target").strip()
    host = str(raw_target.get("host") or "").strip()
    source_name = str(raw_target.get("source_name") or DEFAULT_A2S_SOURCE_NAME).strip()
    query_port = int(raw_target.get("query_port") or 0)
    game_port = _coerce_optional_positive_int(raw_target.get("game_port"))
    external_server_id = _string_or_none(raw_target.get("external_server_id"))
    region = _string_or_none(raw_target.get("region"))

    if not host:
        raise ValueError("Each A2S target must define a non-empty host.")
    if query_port <= 0:
        raise ValueError("Each A2S target must define a valid query_port.")

    return A2SServerTarget(
        name=name,
        host=host,
        query_port=query_port,
        game_port=game_port,
        source_name=source_name or DEFAULT_A2S_SOURCE_NAME,
        external_server_id=external_server_id,
        region=region,
    )


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
        raise ValueError("Each A2S target game_port must be positive when defined.")

    return coerced
