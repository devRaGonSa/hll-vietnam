"""Report safe scoreboard links for existing materialized RCON matches."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from pathlib import Path

from .rcon_admin_log_materialization import list_materialized_rcon_matches
from .rcon_historical_read_model import build_materialized_scoreboard_correlation_input
from .rcon_scoreboard_correlation import resolve_rcon_scoreboard_correlation


DEFAULT_LIMIT = 500


def relink_materialized_matches(
    *,
    server_key: str | None = None,
    limit: int = DEFAULT_LIMIT,
    db_path: Path | None = None,
) -> dict[str, object]:
    """Scan existing matches against trusted candidates used by the detail read model."""
    matches = list_materialized_rcon_matches(
        target_key=server_key,
        only_ended=True,
        limit=limit,
        db_path=db_path,
    )
    report: dict[str, object] = {
        "matches_scanned": len(matches),
        "candidates_scanned": 0,
        "matches_linked": 0,
        "matches_skipped_no_candidate": 0,
        "matches_skipped_ambiguous": 0,
        "errors": [],
    }
    for match in matches:
        try:
            resolution = resolve_rcon_scoreboard_correlation(
                **build_materialized_scoreboard_correlation_input(match),
                db_path=db_path,
            )
        except Exception as exc:
            report["errors"].append(
                {"match_key": match.get("match_key"), "message": str(exc)}
            )
            continue
        report["candidates_scanned"] += int(resolution.get("candidate_count") or 0)
        if resolution.get("match_url"):
            report["matches_linked"] += 1
        elif resolution.get("reason") == "ambiguous-candidate":
            report["matches_skipped_ambiguous"] += 1
        else:
            report["matches_skipped_no_candidate"] += 1
    return report


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Resolve trusted scoreboard links for materialized RCON matches."
    )
    parser.add_argument("--server", dest="server_key")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--db-path", type=Path, default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)
    report = relink_materialized_matches(
        server_key=args.server_key,
        limit=max(1, args.limit),
        db_path=args.db_path,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not report["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
