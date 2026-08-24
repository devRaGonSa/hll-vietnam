"""Authenticated CRCON player-history search with legacy-compatible output."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock
from typing import Any

from ..config import get_crcon_api_timeout_seconds, get_crcon_current_match_bindings
from ..server_targets import (
    ServerTarget,
    load_server_targets,
    resolve_public_aggregate_scope,
)
from ..crcon.api import CrconApiClient
from ..crcon.dto import CrconPlayerHistoryEntry
from ..crcon.models import (
    CrconApiAuthenticationError,
    CrconApiError,
    CrconPlayerHistoryState,
)


@dataclass(frozen=True, slots=True)
class PlayerSearchBinding:
    target: ServerTarget
    api_headers: Mapping[str, str]


ApiFactory = Callable[[PlayerSearchBinding], Any]


class PlayerSearchService:
    """Query every selected target explicitly and merge only compatible IDs."""

    def __init__(
        self,
        *,
        bindings: Mapping[str, PlayerSearchBinding],
        api_factory: ApiFactory,
    ) -> None:
        self._bindings = dict(bindings)
        self._api_factory = api_factory

    def search(
        self,
        *,
        query: str,
        server_id: str | None,
        limit: int,
    ) -> dict[str, object]:
        normalized_query = str(query or "").strip()
        if not normalized_query:
            raise ValueError("Query cannot be empty.")
        if isinstance(limit, bool) or limit < 1 or limit > 100:
            raise ValueError("Player search limit must be between 1 and 100.")

        selected = self._resolve(server_id)
        if selected is None:
            return self._payload(
                query=normalized_query,
                server_id=server_id,
                limit=limit,
                state=CrconPlayerHistoryState.UNAVAILABLE,
                reason="target-not-configured",
                target_states=(),
                items=[],
            )
        if not selected:
            return self._payload(
                query=normalized_query,
                server_id=server_id,
                limit=limit,
                state=CrconPlayerHistoryState.UNAVAILABLE,
                reason="no-enabled-crcon-player-history-targets",
                target_states=(),
                items=[],
            )

        rows: list[tuple[PlayerSearchBinding, CrconPlayerHistoryEntry]] = []
        target_states: list[dict[str, str | None]] = []
        for binding in selected:
            state, reason, found = self._search_target(
                binding, query=normalized_query, limit=limit
            )
            target_states.append(
                {
                    "server_id": binding.target.key,
                    "game": binding.target.game,
                    "state": state.value,
                    "reason": reason,
                }
            )
            rows.extend((binding, row) for row in found)

        state = _overall_state(target_states)
        items = _merge_rows(rows, query=normalized_query, limit=limit)
        failed_targets = sum(
            row["state"] != CrconPlayerHistoryState.SUPPORTED.value
            for row in target_states
        )
        reason = None
        if rows and failed_targets:
            reason = "partial-target-coverage"
        elif state is not CrconPlayerHistoryState.SUPPORTED:
            reason = next(
                (str(row["reason"]) for row in target_states if row.get("reason")),
                None,
            )
        return self._payload(
            query=normalized_query,
            server_id=(selected[0].target.key if len(selected) == 1 else None),
            limit=limit,
            state=state,
            reason=reason,
            target_states=tuple(target_states),
            items=items,
        )

    def _resolve(
        self, server_id: str | None
    ) -> tuple[PlayerSearchBinding, ...] | None:
        selection = resolve_public_aggregate_scope(
            tuple(binding.target for binding in self._bindings.values()), server_id
        )
        if selection is None:
            return None
        return tuple(self._bindings[target.key] for target in selection.targets)

    def _search_target(
        self,
        binding: PlayerSearchBinding,
        *,
        query: str,
        limit: int,
    ) -> tuple[CrconPlayerHistoryState, str | None, tuple[CrconPlayerHistoryEntry, ...]]:
        if binding.target.game == "hllv":
            return (
                CrconPlayerHistoryState.UNVERIFIED_HLLV,
                "get-players-history-not-verified-for-hllv",
                (),
            )
        if not _has_bearer_auth(binding.api_headers):
            return (
                CrconPlayerHistoryState.AUTH_REQUIRED,
                "api.can_view_player_history-bearer-required",
                (),
            )
        try:
            client = self._api_factory(binding)
            page = client.get_players_history(
                player_name=query,
                page=1,
                page_size=limit,
                exact_name_match=False,
            )
            players = page.players
            if not players:
                # This is a bounded exact-value fallback, not format inference.
                id_page = client.get_players_history(
                    player_id=query,
                    page=1,
                    page_size=limit,
                )
                players = tuple(
                    row for row in id_page.players if str(row.identity.player_id) == query
                )
        except CrconApiAuthenticationError:
            return (
                CrconPlayerHistoryState.AUTH_REQUIRED,
                "api-authentication-or-permission-rejected",
                (),
            )
        except (CrconApiError, OSError, TimeoutError):
            return (
                CrconPlayerHistoryState.UNAVAILABLE,
                "crcon-player-history-unavailable",
                (),
            )
        return CrconPlayerHistoryState.SUPPORTED, None, players

    @staticmethod
    def _payload(
        *,
        query: str,
        server_id: str | None,
        limit: int,
        state: CrconPlayerHistoryState,
        reason: str | None,
        target_states: tuple[dict[str, str | None], ...],
        items: list[dict[str, object]],
    ) -> dict[str, object]:
        return {
            "source": "crcon-api-get-players-history",
            "aggregate_state": (
                "AVAILABLE"
                if state is CrconPlayerHistoryState.SUPPORTED
                else "UNAVAILABLE"
            ),
            "player_history_state": state.value,
            "state_reason": reason,
            "query": query,
            "server_id": server_id,
            "limit": limit,
            "item_count": len(items),
            "target_states": list(target_states),
            "items": items,
        }


def _has_bearer_auth(headers: Mapping[str, str]) -> bool:
    value = next(
        (
            str(raw_value).strip()
            for key, raw_value in headers.items()
            if str(key).strip().lower() == "authorization"
        ),
        "",
    )
    parts = value.split(maxsplit=1)
    return len(parts) == 2 and parts[0].upper().rstrip(":") == "BEARER" and bool(parts[1])


def _overall_state(
    rows: list[dict[str, str | None]],
) -> CrconPlayerHistoryState:
    states = {str(row["state"]) for row in rows}
    if CrconPlayerHistoryState.UNVERIFIED_HLLV.value in states:
        return CrconPlayerHistoryState.UNVERIFIED_HLLV
    if CrconPlayerHistoryState.SUPPORTED.value in states:
        return CrconPlayerHistoryState.SUPPORTED
    if CrconPlayerHistoryState.AUTH_REQUIRED.value in states:
        return CrconPlayerHistoryState.AUTH_REQUIRED
    return CrconPlayerHistoryState.UNAVAILABLE


def _merge_rows(
    rows: list[tuple[PlayerSearchBinding, CrconPlayerHistoryEntry]],
    *,
    query: str,
    limit: int,
) -> list[dict[str, object]]:
    merged: dict[tuple[str, str], dict[str, object]] = {}
    for binding, row in rows:
        player_id = str(row.identity.player_id)
        key = (binding.target.game, player_id)
        item = merged.get(key)
        if item is None:
            item = {
                "player_id": player_id,
                "player_name": row.identity.display_name,
                "game": binding.target.game,
                "_aliases": list(row.names),
                "first_seen_at": _iso(row.first_seen_at),
                "last_seen_at": _iso(row.last_seen_at),
                "matches_considered": None,
                "matches_considered_status": "not-provided-by-player-history-api",
                "servers_seen": [binding.target.key],
            }
            merged[key] = item
            continue
        item["servers_seen"] = list(
            dict.fromkeys([*item["servers_seen"], binding.target.key])  # type: ignore[arg-type]
        )
        item["_aliases"] = list(
            dict.fromkeys([*item["_aliases"], *row.names])  # type: ignore[arg-type]
        )
        item["first_seen_at"] = _earliest_iso(
            item.get("first_seen_at"), _iso(row.first_seen_at)
        )
        item["last_seen_at"] = _latest_iso(
            item.get("last_seen_at"), _iso(row.last_seen_at)
        )
    folded = query.casefold()

    def sort_key(item: dict[str, object]) -> tuple[object, ...]:
        names = [str(item.get("player_name") or ""), *item.get("_aliases", [])]  # type: ignore[arg-type]
        normalized_names = [name.casefold() for name in names]
        exact = folded in normalized_names
        contains = any(folded in name for name in normalized_names)
        return (
            not exact,
            not contains,
            -_iso_timestamp(item.get("last_seen_at")),
            str(item["game"]),
            str(item["player_id"]),
        )

    result = sorted(merged.values(), key=sort_key)[:limit]
    for item in result:
        item.pop("_aliases", None)
    return result


def _iso(value: datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z") if value else None


def _earliest_iso(left: object, right: str | None) -> str | None:
    values = [str(value) for value in (left, right) if value]
    return min(values) if values else None


def _latest_iso(left: object, right: str | None) -> str | None:
    values = [str(value) for value in (left, right) if value]
    return max(values) if values else None


def _iso_timestamp(value: object) -> float:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return float("-inf")


def _load_player_search_bindings() -> dict[str, PlayerSearchBinding]:
    configs = get_crcon_current_match_bindings()
    configs_by_slug = {str(row["server_slug"]): row for row in configs}
    targets = load_server_targets().all(enabled_only=True)
    if not targets:
        targets = tuple(
            ServerTarget(
                key=slug,
                display_name=str(config.get("display_name") or slug),
                server_number=int(config["server_number"]),
                game=str(config.get("game") or "hll"),  # type: ignore[arg-type]
                crcon_base_url=str(config["api_base_url"]),
                enabled=bool(config.get("enabled", True)),
                capabilities=frozenset(config.get("capabilities") or ()),
            )
            for slug, config in configs_by_slug.items()
            if bool(config.get("enabled", True))
        )
    bindings: dict[str, PlayerSearchBinding] = {}
    for target in targets:
        config = configs_by_slug.get(target.key)
        aligned = bool(
            config
            and str(config["api_base_url"]).rstrip("/") == target.crcon_base_url
            and int(config["server_number"]) == target.server_number
            and str(config.get("game") or "hll") == target.game
        )
        bindings[target.key] = PlayerSearchBinding(
            target=target,
            api_headers=(dict(config.get("api_headers") or {}) if aligned else {}),
        )
    return bindings


_runtime_lock = Lock()
_runtime_fingerprint: str | None = None
_runtime_service: PlayerSearchService | None = None


def get_crcon_player_search_service() -> PlayerSearchService:
    """Reuse one process-local API service without publishing its credentials."""
    bindings = _load_player_search_bindings()
    fingerprint_data = [
        {
            "key": binding.target.key,
            "number": binding.target.server_number,
            "game": binding.target.game,
            "origin": binding.target.crcon_base_url,
            "headers": sorted(binding.api_headers.items()),
        }
        for binding in bindings.values()
    ]
    fingerprint = hashlib.sha256(
        json.dumps(fingerprint_data, sort_keys=True).encode("utf-8")
    ).hexdigest()
    global _runtime_fingerprint, _runtime_service
    with _runtime_lock:
        if _runtime_service is None or _runtime_fingerprint != fingerprint:
            timeout = get_crcon_api_timeout_seconds()
            _runtime_service = PlayerSearchService(
                bindings=bindings,
                api_factory=lambda binding: CrconApiClient(
                    base_url=binding.target.crcon_base_url,
                    timeout_seconds=timeout,
                    headers=binding.api_headers,
                ),
            )
            _runtime_fingerprint = fingerprint
        return _runtime_service
