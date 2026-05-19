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


@dataclass(frozen=True, slots=True)
class ParsedRconPlayerProfileSnapshot:
    player_name: str
    player_id: str
    source_server_time: int | None
    event_timestamp: object
    first_seen: str | None
    sessions: int | None
    matches_played: int | None
    play_time: str | None
    total_kills: int | None
    total_deaths: int | None
    teamkills_done: int | None
    teamkills_received: int | None
    kd_ratio: float | None
    favorite_weapons: dict[str, int]
    victims: dict[str, int]
    nemesis: dict[str, int]
    averages: dict[str, object]
    sanctions: dict[str, object]
    raw_content: str


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


def parse_rcon_player_profile_snapshot(
    parsed_event: ParsedRconAdminLogEvent | dict[str, object],
    *,
    event_timestamp: object = None,
) -> ParsedRconPlayerProfileSnapshot | None:
    """Extract long-term player profile data from bot-generated MESSAGE content."""
    if isinstance(parsed_event, ParsedRconAdminLogEvent):
        event_type = parsed_event.event_type
        player_name = parsed_event.player_name
        player_id = parsed_event.player_id
        server_time = parsed_event.server_time
        content = parsed_event.content
    else:
        event_type = parsed_event.get("event_type")
        player_name = parsed_event.get("player_name")
        player_id = parsed_event.get("player_id")
        server_time = parsed_event.get("server_time")
        content = parsed_event.get("content")
        event_timestamp = event_timestamp if event_timestamp is not None else parsed_event.get("timestamp")

    source_server_time = _coerce_int(server_time)
    if event_type != "message" or not player_name or not player_id or not content:
        return None
    if source_server_time is None:
        return None

    raw_content = str(content)
    lines = [_clean_profile_line(line) for line in raw_content.splitlines()]
    lines = [line for line in lines if line]
    if not _looks_like_profile_message(lines):
        return None

    sections = _profile_sections(lines)
    flat_values = _profile_key_values(lines)
    total_kills, teamkills_done = _parse_total_with_teamkills(flat_values, "bajas")
    total_deaths, teamkills_received = _parse_total_with_teamkills(flat_values, "muertes")

    return ParsedRconPlayerProfileSnapshot(
        player_name=str(player_name),
        player_id=str(player_id),
        source_server_time=source_server_time,
        event_timestamp=event_timestamp,
        first_seen=_first_value(flat_values, "first seen", "visto por primera vez", "primer visto"),
        sessions=_first_int(flat_values, "sessions", "sesiones"),
        matches_played=_first_int(flat_values, "matches played", "partidas jugadas", "partidas"),
        play_time=_first_value(flat_values, "play time", "tiempo jugado", "tiempo de juego"),
        total_kills=total_kills,
        total_deaths=total_deaths,
        teamkills_done=teamkills_done,
        teamkills_received=teamkills_received,
        kd_ratio=_first_float(flat_values, "k/d", "kd"),
        favorite_weapons=_int_mapping(sections, "armas favoritas", "favorite weapons"),
        victims=_int_mapping(sections, "victimas", "víctimas", "vã­ctimas", "victims"),
        nemesis=_int_mapping(sections, "nemesis", "némesis", "nã©mesis"),
        averages=_object_mapping(sections, "promedios", "averages"),
        sanctions=_object_mapping(sections, "sanciones", "sanctions"),
        raw_content=raw_content,
    )


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


def _coerce_float(value: object) -> float | None:
    if value is None:
        return None
    normalized = str(value).strip().replace(",", ".")
    match = re.search(r"-?\d+(?:\.\d+)?", normalized)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _resolve_winner(allied_score: int | None, axis_score: int | None) -> str | None:
    if allied_score is None or axis_score is None:
        return None
    if allied_score > axis_score:
        return "allied"
    if axis_score > allied_score:
        return "axis"
    return "draw"


def _clean_profile_line(value: str) -> str:
    cleaned = value.strip().strip("─-").strip()
    return cleaned.strip("▒").strip()


def _looks_like_profile_message(lines: list[str]) -> bool:
    labels = {_normalize_profile_label(line.split(":", 1)[0]) for line in lines if ":" in line}
    section_labels = {_normalize_profile_label(line) for line in lines if ":" not in line}
    required = {"bajas", "muertes"}
    known_sections = {
        "totales",
        "victimas",
        "vã­ctimas",
        "nemesis",
        "nã©mesis",
        "armas favoritas",
        "promedios",
        "sanciones",
    }
    return required.issubset(labels) and bool(section_labels & known_sections)


def _profile_sections(lines: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = "root"
    for line in lines:
        if ":" not in line:
            current = _normalize_profile_label(line)
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return sections


def _profile_key_values(lines: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in lines:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[_normalize_profile_label(key)] = value.strip()
    return values


def _normalize_profile_label(value: object) -> str:
    return (
        str(value or "")
        .strip()
        .lower()
        .replace("\u00ad", "")
        .replace("í", "i")
        .replace("é", "e")
        .replace("ã­", "i")
        .replace("ã©", "e")
    )


def _first_value(values: dict[str, str], *keys: str) -> str | None:
    for key in keys:
        value = values.get(_normalize_profile_label(key))
        if value:
            return value
    return None


def _first_int(values: dict[str, str], *keys: str) -> int | None:
    return _coerce_int_from_text(_first_value(values, *keys))


def _first_float(values: dict[str, str], *keys: str) -> float | None:
    return _coerce_float(_first_value(values, *keys))


def _parse_total_with_teamkills(values: dict[str, str], key: str) -> tuple[int | None, int | None]:
    raw_value = _first_value(values, key)
    if not raw_value:
        return None, None
    return _coerce_int_from_text(raw_value), _coerce_int_from_text(_inside_parentheses(raw_value))


def _inside_parentheses(value: str) -> str | None:
    match = re.search(r"\((.*?)\)", value)
    return match.group(1) if match else None


def _int_mapping(sections: dict[str, list[str]], *section_names: str) -> dict[str, int]:
    mapped: dict[str, int] = {}
    for line in _section_lines(sections, *section_names):
        key, value = line.split(":", 1)
        parsed = _coerce_int_from_text(value)
        if parsed is not None:
            mapped[key.strip()] = parsed
    return mapped


def _object_mapping(sections: dict[str, list[str]], *section_names: str) -> dict[str, object]:
    mapped: dict[str, object] = {}
    for line in _section_lines(sections, *section_names):
        key, value = line.split(":", 1)
        cleaned = value.strip()
        mapped[key.strip()] = _coerce_float(cleaned) if re.search(r"\d", cleaned) else cleaned
    return mapped


def _section_lines(sections: dict[str, list[str]], *section_names: str) -> list[str]:
    lines: list[str] = []
    wanted = {_normalize_profile_label(name) for name in section_names}
    for section_name, section_lines in sections.items():
        if _normalize_profile_label(section_name) in wanted:
            lines.extend(section_lines)
    return lines


def _coerce_int_from_text(value: object) -> int | None:
    if value is None:
        return None
    match = re.search(r"-?\d+", str(value))
    return _coerce_int(match.group(0)) if match else None
