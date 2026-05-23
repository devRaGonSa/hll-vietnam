"""Safe external profile fields derived from captured player identifiers."""

from __future__ import annotations

import re


_STEAM_ID64_RE = re.compile(r"^\d{17}$")
_EPIC_ID_RE = re.compile(r"^[0-9a-f]{32}$", re.IGNORECASE)


def build_external_player_profile_fields(
    *,
    player_id: object = None,
    steam_id: object = None,
) -> dict[str, object]:
    """Expose external profile links only when a captured identifier is safe."""

    steam_id_64 = normalize_steam_id_64(steam_id) or normalize_steam_id_64(player_id)
    if steam_id_64:
        return {
            "steam_id_64": steam_id_64,
            "platform": "steam",
            "external_profile_links": {
                "steam": f"https://steamcommunity.com/profiles/{steam_id_64}",
                "hellor": f"https://hellor.pro/player/{steam_id_64}",
                "hll_records": f"https://hllrecords.com/profiles/{steam_id_64}",
                "helo": f"https://helo-system.de/statistics/players/{steam_id_64}?series=2024",
            },
        }

    epic_id = normalize_epic_id(player_id)
    if epic_id:
        return {
            "epic_id": epic_id,
            "platform": "epic",
            "external_profile_links": {
                "hellor": f"https://hellor.pro/player/{epic_id}",
                "hll_records": f"https://hllrecords.com/profiles/{epic_id}",
            },
        }

    return {
        "platform": infer_player_platform(player_id=player_id, steam_id=steam_id),
        "external_profile_links": {},
    }


def normalize_steam_id_64(value: object) -> str | None:
    normalized = str(value or "").strip()
    return normalized if _STEAM_ID64_RE.fullmatch(normalized) else None


def normalize_epic_id(value: object) -> str | None:
    normalized = str(value or "").strip()
    return normalized.lower() if _EPIC_ID_RE.fullmatch(normalized) else None


def infer_player_platform(*, player_id: object = None, steam_id: object = None) -> str:
    normalized_player_id = str(player_id or "").strip()
    if normalize_steam_id_64(steam_id) or normalize_steam_id_64(normalized_player_id):
        return "steam"
    if normalize_epic_id(normalized_player_id):
        return "epic"
    return "unknown"
