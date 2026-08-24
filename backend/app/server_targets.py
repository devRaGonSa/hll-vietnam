"""Canonical server registry plus temporary A2S compatibility targets."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Literal
from urllib.parse import urlsplit

from .config import (
    DEFAULT_A2S_SOURCE_NAME,
    get_a2s_targets_payload,
    get_server_targets_payload,
)


ServerGame = Literal["hll", "hllv"]
PUBLIC_ALL_SERVER_KEYS = frozenset({"", "all", "all-servers"})


class PublicAggregateScopeKind(str, Enum):
    """Product-level aggregate groups, resolved before repository/SQL access."""

    CLASSIC_HLL = "classic-hll"
    EXPLICIT_TARGET = "explicit-target"


@dataclass(frozen=True, slots=True)
class ServerTarget:
    """Public, non-secret configuration for one CRCON-managed game server."""

    key: str
    display_name: str
    server_number: int
    game: ServerGame
    crcon_base_url: str
    enabled: bool = True
    capabilities: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        key = self.key.strip()
        display_name = self.display_name.strip()
        base_url = self.crcon_base_url.strip().rstrip("/")
        if not key or not display_name:
            raise ValueError("ServerTarget key and display_name are required.")
        if self.server_number <= 0:
            raise ValueError("ServerTarget server_number must be positive.")
        if self.game not in {"hll", "hllv"}:
            raise ValueError("ServerTarget game must be 'hll' or 'hllv'.")
        parsed = urlsplit(base_url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "ServerTarget crcon_base_url must be an unauthenticated HTTP(S) origin."
            )
        object.__setattr__(self, "key", key)
        object.__setattr__(self, "display_name", display_name)
        object.__setattr__(self, "crcon_base_url", base_url)
        object.__setattr__(self, "capabilities", frozenset(self.capabilities))


@dataclass(frozen=True, slots=True)
class PublicAggregateScope:
    """A same-game target selection for the public comunidadhll.es site."""

    kind: PublicAggregateScopeKind
    targets: tuple[ServerTarget, ...]

    def __post_init__(self) -> None:
        if len({target.game for target in self.targets}) > 1:
            raise ValueError("Public aggregate scopes cannot mix games.")


def resolve_public_aggregate_scope(
    targets: tuple[ServerTarget, ...], server_id: str | None
) -> PublicAggregateScope | None:
    """Resolve public `all` to enabled classic HLL; keep explicit targets separate."""
    enabled = tuple(target for target in targets if target.enabled)
    normalized = str(server_id or "").strip().lower()
    if normalized in PUBLIC_ALL_SERVER_KEYS:
        return PublicAggregateScope(
            kind=PublicAggregateScopeKind.CLASSIC_HLL,
            targets=tuple(target for target in enabled if target.game == "hll"),
        )
    target = next((target for target in enabled if target.key.lower() == normalized), None)
    if target is None:
        return None
    return PublicAggregateScope(
        kind=PublicAggregateScopeKind.EXPLICIT_TARGET,
        targets=(target,),
    )


class ServerTargetRegistry:
    """Immutable lookup registry supporting any configured number of targets."""

    def __init__(self, targets: tuple[ServerTarget, ...]) -> None:
        by_key: dict[str, ServerTarget] = {}
        for target in targets:
            if target.key in by_key:
                raise ValueError(f"Duplicate ServerTarget key: {target.key}.")
            by_key[target.key] = target
        self._targets = targets
        self._by_key = by_key

    def all(self, *, enabled_only: bool = True) -> tuple[ServerTarget, ...]:
        if not enabled_only:
            return self._targets
        return tuple(target for target in self._targets if target.enabled)

    def get(self, key: str) -> ServerTarget | None:
        return self._by_key.get(str(key or "").strip())


def load_server_targets() -> ServerTargetRegistry:
    """Load the non-secret canonical registry from `HLL_SERVER_TARGETS`."""
    raw_payload = get_server_targets_payload()
    if raw_payload is None:
        return ServerTargetRegistry(())
    try:
        parsed = json.loads(raw_payload)
    except json.JSONDecodeError as error:
        raise ValueError("HLL_SERVER_TARGETS must be valid JSON.") from error
    if not isinstance(parsed, list):
        raise ValueError("HLL_SERVER_TARGETS must be a JSON array.")
    targets = tuple(
        _coerce_server_target(item) for item in parsed if isinstance(item, dict)
    )
    return ServerTargetRegistry(targets)


def _coerce_server_target(raw_target: dict[str, object]) -> ServerTarget:
    raw_capabilities = raw_target.get("capabilities", [])
    if not isinstance(raw_capabilities, list) or any(
        not isinstance(value, str) for value in raw_capabilities
    ):
        raise ValueError("ServerTarget capabilities must be a JSON string array.")
    raw_enabled = raw_target.get("enabled", True)
    if not isinstance(raw_enabled, bool):
        raise ValueError("ServerTarget enabled must be a JSON boolean.")
    return ServerTarget(
        key=str(raw_target.get("key") or ""),
        display_name=str(raw_target.get("display_name") or ""),
        server_number=int(raw_target.get("server_number") or 0),
        game=str(raw_target.get("game") or ""),  # type: ignore[arg-type]
        crcon_base_url=str(raw_target.get("crcon_base_url") or ""),
        enabled=raw_enabled,
        capabilities=frozenset(value.strip() for value in raw_capabilities if value.strip()),
    )


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
    """Legacy A2S transport configuration; identity is its external server key."""

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
