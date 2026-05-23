"""JSON diagnostics for missing materialized RCON scoreboard links."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from pathlib import Path

from .rcon_admin_log_materialization import get_materialized_rcon_match_detail
from .rcon_historical_read_model import build_materialized_scoreboard_correlation_input
from .rcon_scoreboard_correlation import diagnose_rcon_scoreboard_correlation


def inspect_materialized_match_correlation(
    *,
    server_key: str,
    match_key: str,
    db_path: Path | None = None,
) -> dict[str, object]:
    """Return safe scoreboard correlation diagnostics for one materialized match."""
    materialized = get_materialized_rcon_match_detail(
        server_key=server_key,
        match_key=match_key,
        db_path=db_path,
    )
    if materialized is None:
        return {
            "rcon_match_key": match_key,
            "server": server_key,
            "candidate_count": 0,
            "top_candidates": [],
            "selected_candidate": None,
            "final_reason": "rcon-match-not-found",
        }

    match = materialized["match"]
    correlation_input = build_materialized_scoreboard_correlation_input(match)
    correlation = diagnose_rcon_scoreboard_correlation(
        **correlation_input,
        db_path=db_path,
    )
    return {
        "rcon_match_key": match.get("match_key"),
        "server": match.get("external_server_id") or match.get("target_key"),
        "map": match.get("map_pretty_name") or match.get("map_name"),
        "started_at": match.get("started_at"),
        "ended_at": match.get("ended_at"),
        "closed_at": match.get("ended_at") or match.get("started_at"),
        "duration_seconds": correlation_input.get("duration_seconds"),
        "score": {
            "allied_score": match.get("allied_score"),
            "axis_score": match.get("axis_score"),
            "winner": match.get("winner"),
        },
        **correlation,
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Explain scoreboard candidate correlation for one RCON match."
    )
    parser.add_argument("--server", required=True)
    parser.add_argument("--match", dest="match_key", required=True)
    parser.add_argument("--db-path", type=Path, default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)
    print(
        json.dumps(
            inspect_materialized_match_correlation(
                server_key=args.server,
                match_key=args.match_key,
                db_path=args.db_path,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
