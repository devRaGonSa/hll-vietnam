"""Derived duel and weapon aggregates computed from the raw player event ledger."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .config import get_storage_path
from .player_event_storage import initialize_player_event_storage


def list_most_killed(
    *,
    server_slug: str | None = None,
    month: str | None = None,
    external_match_id: str | None = None,
    limit: int = 10,
    db_path: Path | None = None,
) -> list[dict[str, object]]:
    """Return strongest killer -> victim summaries from the raw ledger."""
    return _query_pair_summary(
        event_type="player_kill_summary",
        server_slug=server_slug,
        month=month,
        external_match_id=external_match_id,
        limit=limit,
        db_path=db_path,
    )


def list_death_by(
    *,
    server_slug: str | None = None,
    month: str | None = None,
    external_match_id: str | None = None,
    limit: int = 10,
    db_path: Path | None = None,
) -> list[dict[str, object]]:
    """Return strongest killer -> victim summaries from the victim perspective."""
    return _query_pair_summary(
        event_type="player_death_summary",
        server_slug=server_slug,
        month=month,
        external_match_id=external_match_id,
        limit=limit,
        db_path=db_path,
    )


def list_net_duel_summaries(
    *,
    server_slug: str | None = None,
    month: str | None = None,
    external_match_id: str | None = None,
    limit: int = 10,
    db_path: Path | None = None,
) -> list[dict[str, object]]:
    """Return partial net duel summaries using the strongest encounter signals available."""
    resolved_path = initialize_player_event_storage(db_path=db_path)
    where_sql, params = _build_common_where(
        event_type="player_kill_summary",
        server_slug=server_slug,
        month=month,
        external_match_id=external_match_id,
    )
    with _connect(resolved_path) as connection:
        rows = connection.execute(
            f"""
            WITH duel_pairs AS (
                SELECT
                    CASE
                        WHEN COALESCE(killer_player_key, '') <= COALESCE(victim_player_key, '')
                        THEN killer_player_key
                        ELSE victim_player_key
                    END AS player_a_key,
                    CASE
                        WHEN COALESCE(killer_player_key, '') <= COALESCE(victim_player_key, '')
                        THEN killer_display_name
                        ELSE victim_display_name
                    END AS player_a_name,
                    CASE
                        WHEN COALESCE(killer_player_key, '') <= COALESCE(victim_player_key, '')
                        THEN victim_player_key
                        ELSE killer_player_key
                    END AS player_b_key,
                    CASE
                        WHEN COALESCE(killer_player_key, '') <= COALESCE(victim_player_key, '')
                        THEN victim_display_name
                        ELSE killer_display_name
                    END AS player_b_name,
                    CASE
                        WHEN COALESCE(killer_player_key, '') <= COALESCE(victim_player_key, '')
                        THEN event_value
                        ELSE -event_value
                    END AS net_value,
                    event_value
                FROM player_event_raw_ledger
                WHERE {where_sql}
                    AND killer_player_key IS NOT NULL
                    AND victim_player_key IS NOT NULL
            )
            SELECT
                player_a_key,
                player_a_name,
                player_b_key,
                player_b_name,
                COALESCE(SUM(event_value), 0) AS total_encounters,
                COALESCE(SUM(net_value), 0) AS net_duel_value
            FROM duel_pairs
            GROUP BY player_a_key, player_a_name, player_b_key, player_b_name
            ORDER BY ABS(net_duel_value) DESC, total_encounters DESC, player_a_name ASC, player_b_name ASC
            LIMIT ?
            """,
            [*params, limit],
        ).fetchall()
    return [dict(row) for row in rows]


def list_weapon_kills(
    *,
    server_slug: str | None = None,
    month: str | None = None,
    external_match_id: str | None = None,
    limit: int = 10,
    db_path: Path | None = None,
) -> list[dict[str, object]]:
    """Return partial weapon summaries derived from top kill events."""
    resolved_path = initialize_player_event_storage(db_path=db_path)
    where_sql, params = _build_common_where(
        event_type="player_kill_summary",
        server_slug=server_slug,
        month=month,
        external_match_id=external_match_id,
    )
    with _connect(resolved_path) as connection:
        rows = connection.execute(
            f"""
            SELECT
                killer_player_key,
                killer_display_name,
                COALESCE(weapon_name, 'unknown') AS weapon_name,
                COALESCE(SUM(event_value), 0) AS total_kills
            FROM player_event_raw_ledger
            WHERE {where_sql}
                AND killer_player_key IS NOT NULL
            GROUP BY killer_player_key, killer_display_name, COALESCE(weapon_name, 'unknown')
            ORDER BY total_kills DESC, killer_display_name ASC, weapon_name ASC
            LIMIT ?
            """,
            [*params, limit],
        ).fetchall()
    return [dict(row) for row in rows]


def list_teamkill_summaries(
    *,
    server_slug: str | None = None,
    month: str | None = None,
    external_match_id: str | None = None,
    limit: int = 10,
    db_path: Path | None = None,
) -> list[dict[str, object]]:
    """Return derived teamkill totals per player from the raw ledger."""
    resolved_path = initialize_player_event_storage(db_path=db_path)
    where_sql, params = _build_common_where(
        event_type="player_teamkill_summary",
        server_slug=server_slug,
        month=month,
        external_match_id=external_match_id,
    )
    with _connect(resolved_path) as connection:
        rows = connection.execute(
            f"""
            SELECT
                killer_player_key,
                killer_display_name,
                COALESCE(SUM(event_value), 0) AS total_teamkills
            FROM player_event_raw_ledger
            WHERE {where_sql}
                AND killer_player_key IS NOT NULL
            GROUP BY killer_player_key, killer_display_name
            ORDER BY total_teamkills DESC, killer_display_name ASC
            LIMIT ?
            """,
            [*params, limit],
        ).fetchall()
    return [dict(row) for row in rows]


def _query_pair_summary(
    *,
    event_type: str,
    server_slug: str | None,
    month: str | None,
    external_match_id: str | None,
    limit: int,
    db_path: Path | None,
) -> list[dict[str, object]]:
    resolved_path = initialize_player_event_storage(db_path=db_path)
    where_sql, params = _build_common_where(
        event_type=event_type,
        server_slug=server_slug,
        month=month,
        external_match_id=external_match_id,
    )
    with _connect(resolved_path) as connection:
        rows = connection.execute(
            f"""
            SELECT
                killer_player_key,
                killer_display_name,
                victim_player_key,
                victim_display_name,
                COALESCE(SUM(event_value), 0) AS total_kills
            FROM player_event_raw_ledger
            WHERE {where_sql}
                AND killer_player_key IS NOT NULL
                AND victim_player_key IS NOT NULL
            GROUP BY killer_player_key, killer_display_name, victim_player_key, victim_display_name
            ORDER BY total_kills DESC, killer_display_name ASC, victim_display_name ASC
            LIMIT ?
            """,
            [*params, limit],
        ).fetchall()
    return [dict(row) for row in rows]


def _build_common_where(
    *,
    event_type: str,
    server_slug: str | None,
    month: str | None,
    external_match_id: str | None,
) -> tuple[str, list[object]]:
    clauses = ["event_type = ?"]
    params: list[object] = [event_type]

    if server_slug and server_slug != "all-servers":
        clauses.append("server_slug = ?")
        params.append(server_slug.strip())
    if month:
        clauses.append("substr(COALESCE(occurred_at, ''), 1, 7) = ?")
        params.append(month.strip())
    if external_match_id:
        clauses.append("external_match_id = ?")
        params.append(external_match_id.strip())

    return " AND ".join(clauses), params


def _connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path or get_storage_path())
    connection.row_factory = sqlite3.Row
    return connection
