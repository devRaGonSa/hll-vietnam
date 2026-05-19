"""Parser for Hell Let Loose RCON admin log messages."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Literal


RconAdminLogEventType = Literal[
    "match_start",
    "match_end",
    "kill",
    "team_switch",
    "connected",
    "disconnected",
    "chat",
    "kick",
    "ban",
    "message",
    "unknown",
]


_PREFIX_RE = re.compile(
    r"^\[(?P<relative>.+?)\s+\((?P<server_time>\d+)\)\]\s+(?P<body>.*)$",
    re.DOTALL,
)

MATCH_START_RE = re.compile(
    r"^MATCH START\s+(?P<map_name>.+?)\s+(?P<game_mode>[A-Za-z]+)\s*$",
    re.DOTALL,
)

MATCH_END_RE = re.compile(
    r"^MATCH ENDED\s+`(?P<map_name>.+?)`\s+ALLIED\s+\((?P<allied_score>\d+)\s*-\s*(?P<axis_score>\d+)\)\s+AXIS\s*$",
    re.DOTALL,
)

KILL_RE = re.compile(
    r"^KILL:\s+"
    r"(?P<killer_name>.+?)"
    r"\((?P<killer_team>Allies|Axis|None)/(?P<killer_id>[^)]*)\)"
    r"\s+->\s+"
    r"(?P<victim_name>.+?)"
    r"\((?P<victim_team>Allies|Axis|None)/(?P<victim_id>[^)]*)\)"
    r"\s+with\s+(?P<weapon>.+?)\s*$",
    re.DOTALL,
)

TEAM_SWITCH_RE = re.compile(
    r"^TEAMSWITCH\s+(?P<player_name>.+?)\s+\((?P<from_team>[^>]*)\s+>\s+(?P<to_team>[^)]*)\)\s*$",
    re.DOTALL,
)

CONNECTED_RE = re.compile(
    r"^CONNECTED\s+(?P<player_name>.+?)\s+\((?P<player_id>[^)]*)\)\s*$",
    re.DOTALL,
)

DISCONNECTED_RE = re.compile(
    r"^DISCONNECTED\s+(?P<player_name>.+?)\s+\((?P<player_id>[^)]*)\)\s*$",
    re.DOTALL,
)

CHAT_RE = re.compile(
    r"^CHAT\[(?P<scope>[^\]]+)\]\[(?P<player_name>.+?)\((?P<team>Allies|Axis|None)/(?P<player_id>[^)]*)\)\]:\s*(?P<content>.*)$",
    re.DOTALL,
)

KICK_RE = re.compile(
    r"^KICK:\s+\[(?P<player_name>.+?)\]\s+has been kicked\.\s+\[(?P<reason>.*)\]\s*$",
    re.DOTALL,
)

MESSAGE_RE = re.compile(
    r"^MESSAGE:\s+player\s+\[(?P<player_name>.+?)\((?P<player_id>[^)]*)\)\],\s+content\s+\[(?P<content>.*)\]\s*$",
    re.DOTALL,
)


@dataclass(frozen=True, slots=True)
class ParsedRconAdminLogEvent:
    event_type: RconAdminLogEventType
    raw_message: str
    relative_time: str | None = None
    server_time: int | None = None
    map_name: str | None = None
    game_mode: str | None = None
    allied_score: int | None = None
    axis_score: int | None = None
    winner: str | None = None
    killer_name: str | None = None
    killer_team: str | None = None
    killer_id: str | None = None
    victim_name: str | None = None
    victim_team: str | None = None
    victim_id: str | None = None
    weapon: str | None = None
    player_name: str | None = None
    player_id: str | None = None
    from_team: str | None = None
    to_team: str | None = None
    chat_scope: str | None = None
    chat_team: str | None = None
    content: str | None = None
    reason: str | None = None


def parse_rcon_admin_log_message(message: str) -> ParsedRconAdminLogEvent:
    raw_message = str(message or "")
    prefix_match = _PREFIX_RE.match(raw_message)
    relative_time = None
    server_time = None
    body = raw_message

    if prefix_match:
        relative_time = prefix_match.group("relative")
        server_time = _coerce_int(prefix_match.group("server_time"))
        body = prefix_match.group("body")

    parser_payload = {
        "raw_message": raw_message,
        "relative_time": relative_time,
        "server_time": server_time,
    }

    if match := MATCH_START_RE.match(body):
        return ParsedRconAdminLogEvent(
            event_type="match_start",
            map_name=_clean(match.group("map_name")),
            game_mode=_clean(match.group("game_mode")),
            **parser_payload,
        )

    if match := MATCH_END_RE.match(body):
        allied_score = _coerce_int(match.group("allied_score"))
        axis_score = _coerce_int(match.group("axis_score"))
        return ParsedRconAdminLogEvent(
            event_type="match_end",
            map_name=_clean(match.group("map_name")),
            allied_score=allied_score,
            axis_score=axis_score,
            winner=_resolve_winner(allied_score, axis_score),
            **parser_payload,
        )

    if match := KILL_RE.match(body):
        return ParsedRconAdminLogEvent(
            event_type="kill",
            killer_name=_clean(match.group("killer_name")),
            killer_team=_clean(match.group("killer_team")),
            killer_id=_clean(match.group("killer_id")),
            victim_name=_clean(match.group("victim_name")),
            victim_team=_clean(match.group("victim_team")),
            victim_id=_clean(match.group("victim_id")),
            weapon=_clean(match.group("weapon")),
            **parser_payload,
        )

    if match := TEAM_SWITCH_RE.match(body):
        return ParsedRconAdminLogEvent(
            event_type="team_switch",
            player_name=_clean(match.group("player_name")),
            from_team=_clean(match.group("from_team")),
            to_team=_clean(match.group("to_team")),
            **parser_payload,
        )

    if match := CONNECTED_RE.match(body):
        return ParsedRconAdminLogEvent(
            event_type="connected",
            player_name=_clean(match.group("player_name")),
            player_id=_clean(match.group("player_id")),
            **parser_payload,
        )

    if match := DISCONNECTED_RE.match(body):
        return ParsedRconAdminLogEvent(
            event_type="disconnected",
            player_name=_clean(match.group("player_name")),
            player_id=_clean(match.group("player_id")),
            **parser_payload,
        )

    if match := CHAT_RE.match(body):
        return ParsedRconAdminLogEvent(
            event_type="chat",
            player_name=_clean(match.group("player_name")),
            player_id=_clean(match.group("player_id")),
            chat_scope=_clean(match.group("scope")),
            chat_team=_clean(match.group("team")),
            content=_clean(match.group("content")),
            **parser_payload,
        )

    if match := KICK_RE.match(body):
        return ParsedRconAdminLogEvent(
            event_type="kick",
            player_name=_clean(match.group("player_name")),
            reason=_clean(match.group("reason")),
            **parser_payload,
        )

    if body.upper().startswith("BAN"):
        return ParsedRconAdminLogEvent(event_type="ban", content=_clean(body), **parser_payload)

    if match := MESSAGE_RE.match(body):
        return ParsedRconAdminLogEvent(
            event_type="message",
            player_name=_clean(match.group("player_name")),
            player_id=_clean(match.group("player_id")),
            content=_clean(match.group("content")),
            **parser_payload,
        )

    return ParsedRconAdminLogEvent(event_type="unknown", content=_clean(body), **parser_payload)


def parse_rcon_admin_log_entry(entry: dict[str, object]) -> dict[str, object]:
    parsed = parse_rcon_admin_log_message(str(entry.get("message") or ""))
    payload = asdict(parsed)
    payload["timestamp"] = entry.get("timestamp")
    return payload


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _coerce_int(value: object) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _resolve_winner(allied_score: int | None, axis_score: int | None) -> str | None:
    if allied_score is None or axis_score is None:
        return None
    if allied_score > axis_score:
        return "allied"
    if axis_score > allied_score:
        return "axis"
    return "draw"
