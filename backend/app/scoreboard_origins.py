"""Trusted public scoreboard origins for active community servers."""

from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class TrustedScoreboardOrigin:
    """Public scoreboard origin trusted for one active community server."""

    slug: str
    display_name: str
    base_url: str
    server_number: int
    source_kind: str = "crcon-scoreboard-json"


TRUSTED_PUBLIC_SCOREBOARD_ORIGINS = (
    TrustedScoreboardOrigin(
        slug="comunidad-hispana-01",
        display_name="Comunidad Hispana #01",
        base_url="https://scoreboard.comunidadhll.es",
        server_number=1,
    ),
    TrustedScoreboardOrigin(
        slug="comunidad-hispana-02",
        display_name="Comunidad Hispana #02",
        base_url="https://scoreboard.comunidadhll.es:5443",
        server_number=2,
    ),
)

_TRUSTED_GAME_PATH_RE = re.compile(r"^/games/\d+/?$")


def list_trusted_public_scoreboard_origins() -> tuple[TrustedScoreboardOrigin, ...]:
    """Return trusted public scoreboard origins for active default servers."""
    return TRUSTED_PUBLIC_SCOREBOARD_ORIGINS


def get_trusted_public_scoreboard_origin(
    server_slug: object,
) -> TrustedScoreboardOrigin | None:
    """Return the trusted public scoreboard origin for one active server."""
    normalized_slug = str(server_slug or "").strip()
    if not normalized_slug:
        return None
    for origin in TRUSTED_PUBLIC_SCOREBOARD_ORIGINS:
        if origin.slug == normalized_slug:
            return origin
    return None


def resolve_trusted_scoreboard_match_url(
    raw_payload_ref: object,
    server_slug: object,
) -> str | None:
    """Return a match URL only when it belongs to the trusted server origin."""
    origin = get_trusted_public_scoreboard_origin(server_slug)
    candidate = str(raw_payload_ref or "").strip()
    if origin is None or not candidate:
        return None

    candidate_parts = urlparse(candidate)
    origin_parts = urlparse(origin.base_url)
    if candidate_parts.scheme not in {"http", "https"}:
        return None
    if candidate_parts.scheme != origin_parts.scheme:
        return None
    if candidate_parts.netloc != origin_parts.netloc:
        return None
    if candidate_parts.username or candidate_parts.password:
        return None
    if not _TRUSTED_GAME_PATH_RE.match(candidate_parts.path):
        return None
    if candidate_parts.params or candidate_parts.query or candidate_parts.fragment:
        return None
    return candidate
