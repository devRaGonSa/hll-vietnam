"""CRCON-backed, process-local server-list service."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from threading import Lock
from typing import Protocol

from ..config import get_crcon_api_timeout_seconds, get_server_targets_payload
from ..crcon import CrconApiClient
from ..crcon.dto import CrconPublicInfo
from ..normalizers import normalize_map_name
from ..scoreboard_origins import get_trusted_public_scoreboard_origin
from ..server_targets import ServerTarget, ServerTargetRegistry, load_server_targets


SERVER_LIST_CACHE_TTL_SECONDS = 2.0


class PublicInfoClient(Protocol):
    def get_public_info(self) -> CrconPublicInfo: ...


ClientFactory = Callable[[ServerTarget], PublicInfoClient]
Clock = Callable[[], datetime]


@dataclass(frozen=True, slots=True)
class CrconServerItem:
    target: ServerTarget
    captured_at: datetime
    status: str
    public_info: CrconPublicInfo | None
    freshness: str = "fresh"
    stale: bool = False
    error_reason: str | None = None

    def to_frontend_dict(self) -> dict[str, object]:
        info = self.public_info
        origin = get_trusted_public_scoreboard_origin(self.target.key)
        current_map = None
        if info is not None:
            current_map = normalize_map_name(
                info.current_map.map_name or info.current_map.layer
            )
        return {
            "key": self.target.key,
            "slug": self.target.key,
            "server_slug": self.target.key,
            "external_server_id": self.target.key,
            "title": self.target.display_name,
            "display_name": self.target.display_name,
            "server_name": (
                info.server_name if info is not None and info.server_name else self.target.display_name
            ),
            "status": self.status,
            "online": self.status == "online",
            "players": info.player_count if info is not None else None,
            "max_players": info.max_player_count if info is not None else None,
            "current_map": current_map,
            "game_mode": info.current_map.mode if info is not None else None,
            "started_at": _iso(info.current_map.started_at) if info is not None else None,
            "allied_score": info.score.allied if info is not None else None,
            "axis_score": info.score.axis if info is not None else None,
            "allied_players": info.allied_count if info is not None else None,
            "axis_players": info.axis_count if info is not None else None,
            "remaining_match_time_seconds": (
                info.remaining_seconds if info is not None else None
            ),
            "server_number": self.target.server_number,
            "game": (
                str(info.game).strip().lower()
                if info is not None and info.game
                else self.target.game
            ),
            "region": None,
            "captured_at": _iso(self.captured_at),
            "source": "crcon",
            "source_name": "crcon-public-info",
            # This established frontend discriminator means "real live status".
            # The authoritative producer remains explicit in source/source_name.
            "snapshot_origin": "real-rcon",
            "producer": "crcon",
            "freshness": self.freshness,
            "is_stale": self.stale,
            "unavailable_reason": self.error_reason,
            "community_history_url": f"{origin.base_url}/games" if origin else None,
            "community_history_available": origin is not None,
            "host": None,
            "query_port": None,
            "game_port": None,
        }


@dataclass(frozen=True, slots=True)
class CrconServerListResult:
    items: tuple[CrconServerItem, ...]
    observed_at: datetime
    refresh_status: str
    errors: tuple[dict[str, object], ...]
    cache_hit: bool = False


class CrconServerListService:
    """Fetch enabled ServerTargets through get_public_info with short TTL and last-good."""

    def __init__(
        self,
        *,
        registry: ServerTargetRegistry,
        client_factory: ClientFactory,
        now: Clock = lambda: datetime.now(UTC),
        ttl_seconds: float = SERVER_LIST_CACHE_TTL_SECONDS,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive.")
        self._registry = registry
        self._client_factory = client_factory
        self._now = now
        self._ttl_seconds = ttl_seconds
        self._lock = Lock()
        self._cached: CrconServerListResult | None = None
        self._expires_at: datetime | None = None
        self._last_good: dict[str, CrconServerItem] = {}

    def get_server_list(self) -> CrconServerListResult:
        now = _utc(self._now())
        if self._cached is not None and self._expires_at is not None and now < self._expires_at:
            return replace(self._cached, cache_hit=True)
        with self._lock:
            now = _utc(self._now())
            if self._cached is not None and self._expires_at is not None and now < self._expires_at:
                return replace(self._cached, cache_hit=True)
            result = self._refresh(now)
            self._cached = result
            self._expires_at = datetime.fromtimestamp(
                now.timestamp() + self._ttl_seconds,
                tz=UTC,
            )
            return result

    def _refresh(self, observed_at: datetime) -> CrconServerListResult:
        items: list[CrconServerItem] = []
        errors: list[dict[str, object]] = []
        for target in self._registry.all(enabled_only=True):
            try:
                info = self._client_factory(target).get_public_info()
                item = CrconServerItem(
                    target=target,
                    captured_at=observed_at,
                    status="online",
                    public_info=info,
                )
                self._last_good[target.key] = item
            except Exception as error:  # noqa: BLE001 - public status must degrade per target
                reason = _error_reason(error)
                errors.append(
                    {
                        "target_key": target.key,
                        "source": "crcon",
                        "reason": reason,
                        "error_type": type(error).__name__,
                    }
                )
                last_good = self._last_good.get(target.key)
                if last_good is not None:
                    item = replace(
                        last_good,
                        status="stale",
                        freshness="stale",
                        stale=True,
                        error_reason=reason,
                    )
                else:
                    item = CrconServerItem(
                        target=target,
                        captured_at=observed_at,
                        status="unavailable",
                        public_info=None,
                        freshness="unavailable",
                        stale=True,
                        error_reason=reason,
                    )
            items.append(item)
        refresh_status = (
            "success" if not errors else "degraded" if any(item.public_info for item in items) else "failed"
        )
        return CrconServerListResult(
            items=tuple(items),
            observed_at=observed_at,
            refresh_status=refresh_status,
            errors=tuple(errors),
        )


_runtime_lock = Lock()
_runtime_fingerprint: str | None = None
_runtime_service: CrconServerListService | None = None


def get_crcon_server_list_service() -> CrconServerListService:
    """Build or reuse the process-local CRCON server-list service."""
    payload = get_server_targets_payload() or ""
    fingerprint = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    global _runtime_fingerprint, _runtime_service
    with _runtime_lock:
        if _runtime_service is not None and _runtime_fingerprint == fingerprint:
            return _runtime_service
        registry = load_server_targets()
        timeout = get_crcon_api_timeout_seconds()
        _runtime_service = CrconServerListService(
            registry=registry,
            client_factory=lambda target: CrconApiClient(
                base_url=target.crcon_base_url,
                timeout_seconds=timeout,
            ),
        )
        _runtime_fingerprint = fingerprint
        return _runtime_service


def build_crcon_server_list_payload(service: CrconServerListService) -> dict[str, object]:
    """Serialize CRCON DTOs into the stable public server-list envelope."""
    result = service.get_server_list()
    items = [item.to_frontend_dict() for item in result.items]
    snapshot_times = [
        item.captured_at for item in result.items if item.public_info is not None
    ]
    freshest_time = max(snapshot_times, default=None)
    freshest = _iso(freshest_time)
    snapshot_age_seconds = (
        max(0, int((result.observed_at - freshest_time).total_seconds()))
        if freshest_time is not None
        else None
    )
    all_fresh = bool(items) and all(item.get("freshness") == "fresh" for item in items)
    return {
        "status": "ok",
        "data": {
            "title": "Estado actual de servidores",
            "context": "current-hll-status",
            "source": "crcon",
            "last_snapshot_at": freshest,
            "snapshot_age_seconds": snapshot_age_seconds,
            "snapshot_age_minutes": (
                snapshot_age_seconds // 60 if snapshot_age_seconds is not None else None
            ),
            "max_snapshot_age_seconds": int(SERVER_LIST_CACHE_TTL_SECONDS),
            "is_stale": not all_fresh,
            "freshness": "fresh" if all_fresh else "stale",
            "refresh_attempted": not result.cache_hit,
            "refresh_status": "cached" if result.cache_hit else result.refresh_status,
            "refresh_errors": list(result.errors),
            "primary_source": "crcon",
            "selected_source": "crcon",
            "fallback_used": False,
            "fallback_reason": None,
            "source_attempts": [
                {
                    "source": "crcon",
                    "role": "primary",
                    "status": result.refresh_status,
                    "reason": result.errors[0]["reason"] if result.errors else None,
                    "message": None,
                }
            ],
            "items": items,
        },
    }


def _error_reason(error: Exception) -> str:
    message = str(error).lower()
    if isinstance(error, TimeoutError) or "timeout" in message or "timed out" in message:
        return "crcon-public-info-timeout"
    return "crcon-public-info-unavailable"


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _utc(value).isoformat().replace("+00:00", "Z")
