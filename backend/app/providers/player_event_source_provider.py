"""Player event adapter backed by public CRCON scoreboard match details."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass

from ..player_event_models import PlayerEventRecord


@dataclass(frozen=True, slots=True)
class _PlayerIdentity:
    stable_player_key: str
    display_name: str | None


@dataclass(frozen=True, slots=True)
class PublicScoreboardPlayerEventSource:
    """Normalize partial duel and weapon signals from CRCON match detail payloads."""

    source_kind: str = "public-scoreboard-match-summary"

    def extract_match_events(
        self,
        *,
        server_slug: str,
        match_payload: dict[str, object],
        source_ref: str | None = None,
    ) -> list[PlayerEventRecord]:
        match_id = _stringify(match_payload.get("id"))
        if not match_id:
            return []

        occurred_at = _pick_match_timestamp(match_payload)
        player_rows = _coerce_player_rows(match_payload.get("player_stats"))
        if not player_rows:
            return []

        identity_index = _build_identity_index(player_rows)
        events: list[PlayerEventRecord] = []

        for player_row in player_rows:
            actor = _build_player_identity(player_row)
            if actor is None:
                continue

            top_victim_name, top_victim_count = _extract_named_count(player_row.get("most_killed"))
            top_weapon_name, _ = _extract_named_count(player_row.get("weapons"))
            top_kill_type_name, _ = _extract_named_count(player_row.get("kills_by_type"))
            victim = _find_identity_by_name(identity_index, top_victim_name)
            if victim is not None and top_victim_count > 0:
                events.append(
                    _build_event(
                        event_type="player_kill_summary",
                        occurred_at=occurred_at,
                        server_slug=server_slug,
                        match_id=match_id,
                        source_kind=self.source_kind,
                        source_ref=source_ref,
                        raw_event_ref=f"match:{match_id}:player:{actor.stable_player_key}:most-killed",
                        killer=actor,
                        victim=victim,
                        weapon_name=top_weapon_name,
                        kill_category=top_kill_type_name,
                        is_teamkill=False,
                        event_value=top_victim_count,
                    )
                )

            top_killer_name, top_killer_count = _extract_named_count(player_row.get("death_by"))
            death_weapon_name, _ = _extract_named_count(player_row.get("death_by_weapons"))
            killer = _find_identity_by_name(identity_index, top_killer_name)
            if killer is not None and top_killer_count > 0:
                events.append(
                    _build_event(
                        event_type="player_death_summary",
                        occurred_at=occurred_at,
                        server_slug=server_slug,
                        match_id=match_id,
                        source_kind=self.source_kind,
                        source_ref=source_ref,
                        raw_event_ref=f"match:{match_id}:player:{actor.stable_player_key}:death-by",
                        killer=killer,
                        victim=actor,
                        weapon_name=death_weapon_name,
                        kill_category=None,
                        is_teamkill=False,
                        event_value=top_killer_count,
                    )
                )

            teamkills = _coerce_int(player_row.get("teamkills")) or 0
            if teamkills > 0:
                events.append(
                    _build_event(
                        event_type="player_teamkill_summary",
                        occurred_at=occurred_at,
                        server_slug=server_slug,
                        match_id=match_id,
                        source_kind=self.source_kind,
                        source_ref=source_ref,
                        raw_event_ref=f"match:{match_id}:player:{actor.stable_player_key}:teamkills",
                        killer=actor,
                        victim=None,
                        weapon_name=top_weapon_name,
                        kill_category=top_kill_type_name,
                        is_teamkill=True,
                        event_value=teamkills,
                    )
                )

        return events

    def describe_scope(self) -> dict[str, object]:
        return {
            "source_kind": self.source_kind,
            "supports_raw_kill_events": False,
            "captures": [
                "Top victim per player from most_killed",
                "Top killer per player from death_by",
                "Top weapon hints from weapons and death_by_weapons",
                "Aggregated teamkills per player and match",
            ],
            "limitations": [
                "The current source is match-summary data, not a true per-kill event feed.",
                "occurred_at uses the match end/start timestamp, not the exact kill timestamp.",
                "Only the strongest encounter and weapon signals available in the CRCON detail payload are normalized.",
                "Full killer->victim ledgers, complete weapon breakdowns, and exact per-event teamkills still require a dedicated raw event/log source.",
            ],
        }


def _build_identity_index(player_rows: list[dict[str, object]]) -> dict[str, _PlayerIdentity]:
    identity_index: dict[str, _PlayerIdentity] = {}
    for player_row in player_rows:
        identity = _build_player_identity(player_row)
        if identity is None or not identity.display_name:
            continue
        identity_index[_normalize_name(identity.display_name)] = identity
    return identity_index


def _build_player_identity(player_row: dict[str, object]) -> _PlayerIdentity | None:
    display_name = _stringify(player_row.get("player")) or _stringify(player_row.get("name"))
    source_player_id = _stringify(player_row.get("player_id")) or _stringify(player_row.get("id"))
    steam_id = _extract_steam_id(player_row.get("steaminfo"))
    stable_player_key = _build_stable_player_key(steam_id=steam_id, source_player_id=source_player_id)
    if stable_player_key is None:
        return None
    return _PlayerIdentity(
        stable_player_key=stable_player_key,
        display_name=display_name or stable_player_key,
    )


def _find_identity_by_name(
    identity_index: dict[str, _PlayerIdentity],
    player_name: str | None,
) -> _PlayerIdentity | None:
    if not player_name:
        return None
    return identity_index.get(_normalize_name(player_name))


def _build_event(
    *,
    event_type: str,
    occurred_at: str | None,
    server_slug: str,
    match_id: str,
    source_kind: str,
    source_ref: str | None,
    raw_event_ref: str,
    killer: _PlayerIdentity | None,
    victim: _PlayerIdentity | None,
    weapon_name: str | None,
    kill_category: str | None,
    is_teamkill: bool,
    event_value: int,
) -> PlayerEventRecord:
    event_id = _build_event_id(
        event_type=event_type,
        occurred_at=occurred_at,
        server_slug=server_slug,
        match_id=match_id,
        killer_player_key=killer.stable_player_key if killer else None,
        victim_player_key=victim.stable_player_key if victim else None,
        weapon_name=weapon_name,
        is_teamkill=is_teamkill,
        event_value=event_value,
    )
    return PlayerEventRecord(
        event_id=event_id,
        event_type=event_type,
        occurred_at=occurred_at,
        server_slug=server_slug,
        external_match_id=match_id,
        source_kind=source_kind,
        source_ref=source_ref,
        raw_event_ref=raw_event_ref,
        killer_player_key=killer.stable_player_key if killer else None,
        killer_display_name=killer.display_name if killer else None,
        victim_player_key=victim.stable_player_key if victim else None,
        victim_display_name=victim.display_name if victim else None,
        weapon_name=weapon_name,
        weapon_category=None,
        kill_category=kill_category,
        is_teamkill=is_teamkill,
        event_value=max(1, event_value),
    )


def _build_event_id(
    *,
    event_type: str,
    occurred_at: str | None,
    server_slug: str,
    match_id: str,
    killer_player_key: str | None,
    victim_player_key: str | None,
    weapon_name: str | None,
    is_teamkill: bool,
    event_value: int,
) -> str:
    raw_key = "|".join(
        [
            event_type,
            occurred_at or "",
            server_slug,
            match_id,
            killer_player_key or "",
            victim_player_key or "",
            weapon_name or "",
            "1" if is_teamkill else "0",
            str(event_value),
        ]
    )
    return hashlib.sha1(raw_key.encode("utf-8")).hexdigest()


def _pick_match_timestamp(match_payload: Mapping[str, object]) -> str | None:
    for key in ("end", "start", "creation_time"):
        value = _stringify(match_payload.get(key))
        if value:
            return value
    return None


def _extract_named_count(value: object) -> tuple[str | None, int]:
    if isinstance(value, str):
        return _stringify(value), 1
    if isinstance(value, Mapping):
        nested_name = None
        nested_player = value.get("player")
        if isinstance(nested_player, Mapping):
            nested_name = _stringify(nested_player.get("name")) or _stringify(nested_player.get("player"))
        name = (
            _stringify(value.get("name"))
            or _stringify(value.get("player"))
            or _stringify(value.get("victim"))
            or _stringify(value.get("killer"))
            or nested_name
        )
        count = (
            _coerce_int(value.get("count"))
            or _coerce_int(value.get("kills"))
            or _coerce_int(value.get("deaths"))
            or _coerce_int(value.get("value"))
            or _coerce_int(value.get("total"))
            or 1
        )
        return name, max(1, count)
    if isinstance(value, list):
        for item in value:
            name, count = _extract_named_count(item)
            if name:
                return name, count
    return None, 0


def _extract_steam_id(value: object) -> str | None:
    if isinstance(value, Mapping):
        profile = value.get("profile")
        if isinstance(profile, Mapping):
            steam_id = _stringify(profile.get("steamid"))
            if steam_id:
                return steam_id
        return _stringify(value.get("id"))
    return None


def _build_stable_player_key(
    *,
    steam_id: str | None,
    source_player_id: str | None,
) -> str | None:
    if steam_id:
        return f"steam:{steam_id}"
    if source_player_id:
        return f"crcon-player:{source_player_id}"
    return None


def _coerce_player_rows(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _normalize_name(value: str) -> str:
    return value.strip().casefold()


def _stringify(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
