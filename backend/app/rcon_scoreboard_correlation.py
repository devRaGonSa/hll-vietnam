"""Correlate RCON competitive windows with trusted persisted scoreboard matches."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .config import get_storage_path, use_postgres_rcon_storage
from .normalizers import normalize_map_name
from .scoreboard_origins import resolve_trusted_scoreboard_match_url
from .sqlite_utils import connect_sqlite_readonly


MIN_CONFIDENCE_SCORE = 5
MAX_CANDIDATES = 200


def resolve_rcon_scoreboard_match_url(
    *,
    server_slug: object,
    map_name: object,
    started_at: object,
    ended_at: object,
    duration_seconds: object = None,
    player_count: object = None,
    peak_players: object = None,
    allied_score: object = None,
    axis_score: object = None,
    db_path: Path | None = None,
) -> str | None:
    """Return a trusted scoreboard URL for an RCON window only on strong evidence."""
    normalized_server_slug = str(server_slug or "").strip()
    normalized_map = normalize_map_name(map_name)
    rcon_start = _parse_timestamp(started_at)
    rcon_end = _parse_timestamp(ended_at)
    if not normalized_server_slug or not normalized_map or not rcon_start or not rcon_end:
        return None
    if rcon_end < rcon_start:
        rcon_start, rcon_end = rcon_end, rcon_start

    candidates = _list_persisted_scoreboard_candidates(
        server_slug=normalized_server_slug,
        db_path=db_path or get_storage_path(),
    )
    scored_candidates = [
        scored
        for candidate in candidates
        if (scored := _score_candidate(
            candidate,
            normalized_map=normalized_map,
            rcon_start=rcon_start,
            rcon_end=rcon_end,
            duration_seconds=_coerce_int(duration_seconds),
            player_count=_coerce_int(player_count),
            peak_players=_coerce_int(peak_players),
            allied_score=_coerce_int(allied_score),
            axis_score=_coerce_int(axis_score),
        ))
        is not None
    ]
    if not scored_candidates:
        return None

    scored_candidates.sort(key=lambda item: item["score"], reverse=True)
    best = scored_candidates[0]
    if int(best["score"]) < MIN_CONFIDENCE_SCORE:
        return None
    if len(scored_candidates) > 1 and int(scored_candidates[1]["score"]) >= int(best["score"]):
        return None
    return str(best["match_url"])


def _list_persisted_scoreboard_candidates(
    *,
    server_slug: str,
    db_path: Path,
) -> list[dict[str, object]]:
    if use_postgres_rcon_storage():
        from .postgres_rcon_storage import list_scoreboard_candidates

        postgres_candidates = list_scoreboard_candidates(
            server_slug=server_slug,
            limit=MAX_CANDIDATES,
        )
        if postgres_candidates:
            return postgres_candidates

    try:
        with connect_sqlite_readonly(db_path) as connection:
            rows = connection.execute(
                """
                SELECT
                    historical_matches.external_match_id,
                    historical_matches.started_at,
                    historical_matches.ended_at,
                    historical_matches.map_name,
                    historical_matches.map_pretty_name,
                    historical_matches.allied_score,
                    historical_matches.axis_score,
                    historical_matches.raw_payload_ref,
                    historical_servers.slug AS server_slug,
                    COUNT(historical_player_match_stats.id) AS player_count
                FROM historical_matches
                INNER JOIN historical_servers
                    ON historical_servers.id = historical_matches.historical_server_id
                LEFT JOIN historical_player_match_stats
                    ON historical_player_match_stats.historical_match_id = historical_matches.id
                WHERE historical_servers.slug = ?
                  AND historical_matches.raw_payload_ref IS NOT NULL
                GROUP BY historical_matches.id
                ORDER BY COALESCE(historical_matches.ended_at, historical_matches.started_at) DESC
                LIMIT ?
                """,
                (server_slug, MAX_CANDIDATES),
            ).fetchall()
    except sqlite3.Error:
        return []

    items: list[dict[str, object]] = []
    for row in rows:
        match_url = resolve_trusted_scoreboard_match_url(
            row["raw_payload_ref"],
            row["server_slug"],
        )
        if not match_url:
            continue
        items.append(
            {
                "external_match_id": row["external_match_id"],
                "started_at": row["started_at"],
                "ended_at": row["ended_at"],
                "map_name": row["map_name"],
                "map_pretty_name": row["map_pretty_name"],
                "allied_score": row["allied_score"],
                "axis_score": row["axis_score"],
                "player_count": row["player_count"],
                "match_url": match_url,
            }
        )
    if items and use_postgres_rcon_storage():
        from .postgres_rcon_storage import upsert_scoreboard_candidates

        upsert_scoreboard_candidates(server_slug=server_slug, candidates=items)
    return items


def _score_candidate(
    candidate: dict[str, object],
    *,
    normalized_map: str,
    rcon_start: datetime,
    rcon_end: datetime,
    duration_seconds: int | None,
    player_count: int | None,
    peak_players: int | None,
    allied_score: int | None,
    axis_score: int | None,
) -> dict[str, object] | None:
    candidate_map = normalize_map_name(
        candidate.get("map_pretty_name") or candidate.get("map_name")
    )
    if candidate_map != normalized_map:
        return None

    candidate_start = _parse_timestamp(candidate.get("started_at"))
    candidate_end = _parse_timestamp(candidate.get("ended_at"))
    if not candidate_start or not candidate_end:
        return None
    if candidate_end < candidate_start:
        candidate_start, candidate_end = candidate_end, candidate_start

    score = 0
    overlap_seconds = _overlap_seconds(rcon_start, rcon_end, candidate_start, candidate_end)
    rcon_midpoint = rcon_start + (rcon_end - rcon_start) / 2
    if overlap_seconds > 0:
        score += 3
    if candidate_start <= rcon_midpoint <= candidate_end:
        score += 2

    closest_edge_distance = min(
        abs((rcon_start - candidate_start).total_seconds()),
        abs((rcon_start - candidate_end).total_seconds()),
        abs((rcon_end - candidate_start).total_seconds()),
        abs((rcon_end - candidate_end).total_seconds()),
    )
    if closest_edge_distance <= 1800:
        score += 2
    elif closest_edge_distance <= 3600:
        score += 1

    candidate_duration = int((candidate_end - candidate_start).total_seconds())
    if duration_seconds and candidate_duration > 0:
        if abs(candidate_duration - duration_seconds) <= 1800:
            score += 1
        elif overlap_seconds > 0 and duration_seconds <= candidate_duration:
            score += 1

    candidate_allied_score = _coerce_int(candidate.get("allied_score"))
    candidate_axis_score = _coerce_int(candidate.get("axis_score"))
    if (
        allied_score is not None
        and axis_score is not None
        and candidate_allied_score is not None
        and candidate_axis_score is not None
    ):
        if candidate_allied_score == allied_score and candidate_axis_score == axis_score:
            score += 2
        elif sorted((candidate_allied_score, candidate_axis_score)) == sorted((allied_score, axis_score)):
            score += 1

    candidate_players = _coerce_int(candidate.get("player_count"))
    reference_players = peak_players or player_count
    if candidate_players and reference_players:
        if abs(candidate_players - reference_players) <= 20:
            score += 1
        elif candidate_players >= int(reference_players * 0.75):
            score += 1

    if score <= 0:
        return None
    return {
        "score": score,
        "match_url": candidate["match_url"],
    }


def _overlap_seconds(
    first_start: datetime,
    first_end: datetime,
    second_start: datetime,
    second_end: datetime,
) -> int:
    return max(0, int((min(first_end, second_end) - max(first_start, second_start)).total_seconds()))


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _coerce_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None
