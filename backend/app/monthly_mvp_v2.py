"""Monthly MVP V2 scoring helpers."""

from __future__ import annotations

import math
from typing import Mapping


MONTHLY_MVP_V2_VERSION = "v2"
MONTHLY_MVP_V2_MIN_MATCHES = 6
MONTHLY_MVP_V2_MIN_TIME_SECONDS = 21600
MONTHLY_MVP_V2_FULL_PARTICIPATION_SECONDS = 28800
MONTHLY_MVP_V2_ADVANCED_CONFIDENCE_KILLS = 35
MONTHLY_MVP_V2_TEAMKILL_PENALTY_CAP = 8.0
MONTHLY_MVP_V2_TEAMKILL_PENALTY_PER_KILL = 0.75


def build_monthly_mvp_v2_rankings(
    aggregated_rows: list[Mapping[str, object]],
    *,
    limit: int,
) -> dict[str, object]:
    """Transform aggregated monthly totals plus V2 event signals into rankings."""
    eligible_rows = [
        _build_eligible_player_summary(row)
        for row in aggregated_rows
        if _is_eligible_player_row(row)
    ]

    if not eligible_rows:
        return {
            "ranking_version": MONTHLY_MVP_V2_VERSION,
            "eligibility": _build_eligibility_metadata(),
            "eligible_players_count": 0,
            "items": [],
        }

    max_total_kills = max(item["totals"]["kills"] for item in eligible_rows)
    max_total_support = max(item["totals"]["support"] for item in eligible_rows)
    max_kpm = max(item["derived"]["kpm"] for item in eligible_rows)
    max_kda = max(item["derived"]["kda"] for item in eligible_rows)
    max_rivalry_edge = max(item["advanced"]["rivalry_edge_raw"] for item in eligible_rows)
    max_duel_control = max(item["advanced"]["duel_control_raw"] for item in eligible_rows)

    for item in eligible_rows:
        component_scores = {
            "kills_score": _log_normalized_score(item["totals"]["kills"], max_total_kills),
            "support_score": _log_normalized_score(item["totals"]["support"], max_total_support),
            "kpm_score": _log_normalized_score(item["derived"]["kpm"], max_kpm),
            "kda_score": _log_normalized_score(item["derived"]["kda"], max_kda),
            "participation_score": round(
                100
                * min(
                    1.0,
                    item["totals"]["time_seconds"] / MONTHLY_MVP_V2_FULL_PARTICIPATION_SECONDS,
                ),
                3,
            ),
            "rivalry_edge_score": _log_normalized_score(
                item["advanced"]["rivalry_edge_raw"],
                max_rivalry_edge,
            ),
            "duel_control_score": _log_normalized_score(
                item["advanced"]["duel_control_raw"],
                max_duel_control,
            ),
        }
        advanced_confidence = round(
            min(
                1.0,
                item["totals"]["kills"] / MONTHLY_MVP_V2_ADVANCED_CONFIDENCE_KILLS,
            ),
            3,
        )
        teamkill_penalty_v2 = round(
            min(
                MONTHLY_MVP_V2_TEAMKILL_PENALTY_CAP,
                item["totals"]["teamkills"] * MONTHLY_MVP_V2_TEAMKILL_PENALTY_PER_KILL,
            ),
            3,
        )
        item["component_scores"] = component_scores
        item["advanced_confidence"] = advanced_confidence
        item["teamkill_penalty_v2"] = teamkill_penalty_v2
        item["mvp_v2_score"] = round(
            (0.30 * component_scores["kills_score"])
            + (0.18 * component_scores["support_score"])
            + (0.18 * component_scores["kpm_score"])
            + (0.12 * component_scores["kda_score"])
            + (0.10 * component_scores["participation_score"])
            + advanced_confidence
            * (
                (0.07 * component_scores["rivalry_edge_score"])
                + (0.05 * component_scores["duel_control_score"])
            )
            - teamkill_penalty_v2,
            3,
        )

    ranked_items = sorted(
        eligible_rows,
        key=lambda item: (
            -item["mvp_v2_score"],
            -item["advanced_confidence"],
            -item["component_scores"]["participation_score"],
            -item["component_scores"]["kills_score"],
            -item["component_scores"]["rivalry_edge_score"],
            item["totals"]["teamkills"],
            str(item["player"]["name"]).casefold(),
            str(item["player"]["stable_player_key"]),
        ),
    )
    for position, item in enumerate(ranked_items[:limit], start=1):
        item["ranking_position"] = position

    return {
        "ranking_version": MONTHLY_MVP_V2_VERSION,
        "eligibility": _build_eligibility_metadata(),
        "eligible_players_count": len(eligible_rows),
        "items": ranked_items[:limit],
    }


def _is_eligible_player_row(row: Mapping[str, object]) -> bool:
    matches_count = int(row.get("matches_count") or 0)
    time_seconds = int(row.get("total_time_seconds") or 0)
    has_required_fields = all(
        row.get(field_name) is not None
        for field_name in ("total_kills", "total_deaths", "total_support", "total_time_seconds")
    )
    return (
        has_required_fields
        and matches_count >= MONTHLY_MVP_V2_MIN_MATCHES
        and time_seconds >= MONTHLY_MVP_V2_MIN_TIME_SECONDS
    )


def _build_eligible_player_summary(row: Mapping[str, object]) -> dict[str, object]:
    total_kills = int(row.get("total_kills") or 0)
    total_deaths = int(row.get("total_deaths") or 0)
    total_support = int(row.get("total_support") or 0)
    total_teamkills = int(row.get("total_teamkills") or 0)
    total_time_seconds = int(row.get("total_time_seconds") or 0)
    total_time_minutes = max(total_time_seconds / 60.0, 1.0)
    most_killed_count = int(row.get("most_killed_count") or 0)
    death_by_count = int(row.get("death_by_count") or 0)
    duel_control_raw = int(row.get("duel_control_raw") or 0)
    kpm = round(total_kills / total_time_minutes, 6)
    kda = round(total_kills / max(total_deaths, 1), 6)
    return {
        "server": {
            "slug": row.get("server_slug"),
            "name": row.get("server_name"),
        },
        "player": {
            "stable_player_key": row.get("stable_player_key"),
            "name": row.get("player_name"),
            "steam_id": row.get("steam_id"),
        },
        "matches_considered": int(row.get("matches_count") or 0),
        "totals": {
            "kills": total_kills,
            "deaths": total_deaths,
            "support": total_support,
            "teamkills": total_teamkills,
            "time_seconds": total_time_seconds,
            "time_minutes": round(total_time_seconds / 60.0, 2),
        },
        "derived": {
            "kpm": kpm,
            "kda": kda,
        },
        "advanced": {
            "most_killed_count": most_killed_count,
            "death_by_count": death_by_count,
            "rivalry_edge_raw": max(0, most_killed_count - death_by_count),
            "duel_control_raw": duel_control_raw,
        },
    }


def _log_normalized_score(value: float | int, max_value: float | int) -> float:
    if value <= 0 or max_value <= 0:
        return 0.0
    return round((100 * math.log1p(value)) / math.log1p(max_value), 3)


def _build_eligibility_metadata() -> dict[str, object]:
    return {
        "minimum_matches": MONTHLY_MVP_V2_MIN_MATCHES,
        "minimum_time_seconds": MONTHLY_MVP_V2_MIN_TIME_SECONDS,
        "minimum_time_hours": round(MONTHLY_MVP_V2_MIN_TIME_SECONDS / 3600, 1),
        "full_participation_seconds": MONTHLY_MVP_V2_FULL_PARTICIPATION_SECONDS,
        "full_participation_hours": round(
            MONTHLY_MVP_V2_FULL_PARTICIPATION_SECONDS / 3600,
            1,
        ),
        "advanced_confidence_kills": MONTHLY_MVP_V2_ADVANCED_CONFIDENCE_KILLS,
        "teamkill_penalty_per_kill": MONTHLY_MVP_V2_TEAMKILL_PENALTY_PER_KILL,
        "teamkill_penalty_cap": MONTHLY_MVP_V2_TEAMKILL_PENALTY_CAP,
    }
