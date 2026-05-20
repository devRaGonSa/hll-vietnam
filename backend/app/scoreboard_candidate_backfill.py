"""Backfill public scoreboard candidates for RCON match link correlation.

This command intentionally reuses the existing historical public-scoreboard
archive ingestion path. The RCON materialized detail endpoint can only expose a
safe public match URL when a matching scoreboard row exists in historical_matches.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from typing import Iterable

from .historical_ingestion import run_incremental_refresh
from .scoreboard_origins import list_trusted_public_scoreboard_origins

DEFAULT_MAX_PAGES = 20
DEFAULT_PAGE_SIZE = 100
DEFAULT_DETAIL_WORKERS = 4


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    from_timestamp = _parse_timestamp(args.from_timestamp, option_name="--from")
    to_timestamp = _parse_timestamp(args.to_timestamp, option_name="--to")
    if to_timestamp <= from_timestamp:
        parser.error("--to must be later than --from")

    _validate_server(args.server_slug, parser)
    overlap_hours = _calculate_overlap_hours(from_timestamp)

    progress_events: list[dict[str, object]] = []

    def _capture_progress(payload: dict[str, object]) -> None:
        progress_events.append(payload)
        print(json.dumps(payload, ensure_ascii=False))

    result = run_incremental_refresh(
        server_slug=args.server_slug,
        max_pages=args.max_pages,
        page_size=args.page_size,
        detail_workers=args.detail_workers,
        overlap_hours=overlap_hours,
        rebuild_snapshots=False,
        progress_callback=_capture_progress,
    )

    totals = dict(result.get("totals") or {})
    report = {
        "status": result.get("status"),
        "server": args.server_slug,
        "requested_window": {
            "from": _format_timestamp(from_timestamp),
            "to": _format_timestamp(to_timestamp),
        },
        "ingestion_policy": {
            "overlap_hours": overlap_hours,
            "max_pages": args.max_pages,
            "page_size": args.page_size,
            "detail_workers": args.detail_workers,
            "implementation": "historical-ingestion-public-scoreboard-candidates",
        },
        "candidates_seen": _coerce_int(totals.get("matches_seen")),
        "candidates_inserted": _coerce_int(totals.get("matches_inserted")),
        "candidates_updated": _coerce_int(totals.get("matches_updated")),
        "player_rows_inserted": _coerce_int(totals.get("player_rows_inserted")),
        "player_rows_updated": _coerce_int(totals.get("player_rows_updated")),
        "skipped_unsafe_urls": 0,
        "errors": _extract_errors(progress_events, result),
        "raw_result": result,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if str(result.get("status")) == "ok" else 1


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Backfill public scoreboard match candidates for RCON link correlation.",
    )
    parser.add_argument(
        "--server",
        dest="server_slug",
        required=True,
        help="trusted historical server slug, e.g. comunidad-hispana-02",
    )
    parser.add_argument(
        "--from",
        dest="from_timestamp",
        required=True,
        help="inclusive UTC-ish ISO timestamp used as the lower backfill bound",
    )
    parser.add_argument(
        "--to",
        dest="to_timestamp",
        required=True,
        help="exclusive UTC-ish ISO timestamp kept in the report for traceability",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=DEFAULT_MAX_PAGES,
        help=f"maximum public-scoreboard pages to scan, default {DEFAULT_MAX_PAGES}",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=DEFAULT_PAGE_SIZE,
        help=f"public-scoreboard page size, default {DEFAULT_PAGE_SIZE}",
    )
    parser.add_argument(
        "--detail-workers",
        type=int,
        default=DEFAULT_DETAIL_WORKERS,
        help=f"parallel detail workers, default {DEFAULT_DETAIL_WORKERS}",
    )
    return parser


def _validate_server(server_slug: str, parser: argparse.ArgumentParser) -> None:
    trusted_slugs = {origin.slug for origin in list_trusted_public_scoreboard_origins()}
    if server_slug not in trusted_slugs:
        parser.error(
            f"unknown or untrusted server '{server_slug}'. "
            f"Allowed values: {', '.join(sorted(trusted_slugs))}"
        )


def _parse_timestamp(value: str, *, option_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"{option_name} must be an ISO timestamp, got {value!r}"
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _calculate_overlap_hours(from_timestamp: datetime) -> int:
    now = datetime.now(timezone.utc)
    delta_seconds = max(0, int((now - from_timestamp).total_seconds()))
    # Add one hour so the requested lower bound is safely included after integer rounding.
    return max(1, (delta_seconds // 3600) + 1)


def _format_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _coerce_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _extract_errors(
    progress_events: list[dict[str, object]],
    result: dict[str, object],
) -> list[dict[str, object]]:
    errors: list[dict[str, object]] = []
    if str(result.get("status")) != "ok":
        errors.append({"scope": "result", "message": str(result)})
    for event in progress_events:
        text = str(event.get("event") or "")
        if "error" in text or "failed" in text:
            errors.append(event)
    return errors


if __name__ == "__main__":
    raise SystemExit(main())
