"""Backfill public scoreboard candidates for RCON match link correlation."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from typing import Iterable

from .historical_storage import initialize_historical_storage, list_historical_servers, upsert_historical_match
from .providers.public_scoreboard_provider import PublicScoreboardHistoricalDataSource
from .scoreboard_origins import list_trusted_public_scoreboard_origins

DEFAULT_MAX_PAGES = 20
DEFAULT_PAGE_SIZE = 100
DEFAULT_DETAIL_WORKERS = 4


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    start_at = _parse_timestamp(args.start_at, option_name="--from")
    end_at = _parse_timestamp(args.end_at, option_name="--to")
    if end_at <= start_at:
        parser.error("--to must be later than --from")
    server = _resolve_server(args.server_slug, parser)
    report = run_backfill(server=server, start_at=start_at, end_at=end_at, max_pages=args.max_pages, page_size=args.page_size, detail_workers=args.detail_workers)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not report["errors"] else 1


def run_backfill(*, server: dict[str, object], start_at: datetime, end_at: datetime, max_pages: int, page_size: int, detail_workers: int) -> dict[str, object]:
    initialize_historical_storage()
    provider = PublicScoreboardHistoricalDataSource()
    server_slug = str(server["slug"])
    base_url = str(server["scoreboard_base_url"])
    counters = {"pages_processed": 0, "candidates_seen": 0, "candidates_inserted": 0, "candidates_updated": 0, "player_rows_inserted": 0, "player_rows_updated": 0}
    errors: list[dict[str, object]] = []
    stopped_after_window = False
    for page in range(1, max_pages + 1):
        try:
            page_payload = provider.fetch_match_page(base_url=base_url, page=page, limit=page_size)
        except Exception as exc:
            errors.append({"stage": "fetch_match_page", "page": page, "message": str(exc)})
            break
        matches = _coerce_match_list(page_payload.get("maps"))
        if not matches:
            break
        counters["pages_processed"] += 1
        ids: list[str] = []
        for match in matches:
            counters["candidates_seen"] += 1
            ref_time = _parse_optional_timestamp(_pick_match_timestamp(match))
            if ref_time and ref_time < start_at:
                stopped_after_window = True
                continue
            if ref_time and ref_time >= end_at:
                continue
            match_id = _stringify(match.get("id"))
            if match_id:
                ids.append(match_id)
        if ids:
            try:
                details = provider.fetch_match_details(base_url=base_url, match_ids=ids, max_workers=detail_workers)
            except Exception as exc:
                errors.append({"stage": "fetch_match_details", "page": page, "message": str(exc)})
                details = []
            for detail in details:
                try:
                    delta = upsert_historical_match(server_slug=server_slug, match_payload=detail)
                except Exception as exc:
                    errors.append({"stage": "upsert_historical_match", "match_id": _stringify(detail.get("id")), "message": str(exc)})
                    continue
                counters["candidates_inserted"] += _coerce_int(delta.get("matches_inserted"))
                counters["candidates_updated"] += _coerce_int(delta.get("matches_updated"))
                counters["player_rows_inserted"] += _coerce_int(delta.get("player_rows_inserted"))
                counters["player_rows_updated"] += _coerce_int(delta.get("player_rows_updated"))
        if stopped_after_window:
            break
    return {"status": "ok" if not errors else "partial", "server": server_slug, "scoreboard_base_url": base_url, "requested_window": {"from": _format_timestamp(start_at), "to": _format_timestamp(end_at)}, "stopped_after_window": stopped_after_window, "skipped_unsafe_urls": 0, "errors": errors, **counters}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backfill public scoreboard match candidates for RCON link correlation.")
    parser.add_argument("--server", dest="server_slug", required=True)
    parser.add_argument("--from", dest="start_at", required=True)
    parser.add_argument("--to", dest="end_at", required=True)
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    parser.add_argument("--page-size", type=int, default=DEFAULT_PAGE_SIZE)
    parser.add_argument("--detail-workers", type=int, default=DEFAULT_DETAIL_WORKERS)
    return parser


def _resolve_server(server_slug: str, parser: argparse.ArgumentParser) -> dict[str, object]:
    trusted = {origin.slug for origin in list_trusted_public_scoreboard_origins()}
    if server_slug not in trusted:
        parser.error(f"unknown or untrusted server '{server_slug}'")
    for server in list_historical_servers():
        if server.get("slug") == server_slug:
            return server
    parser.error(f"trusted server '{server_slug}' is not present in historical storage")
    raise AssertionError("unreachable")


def _parse_timestamp(value: str, *, option_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{option_name} must be an ISO timestamp") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_optional_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return _parse_timestamp(value, option_name="timestamp")
    except argparse.ArgumentTypeError:
        return None


def _format_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _coerce_match_list(payload: object) -> list[dict[str, object]]:
    return [item for item in payload if isinstance(item, dict)] if isinstance(payload, list) else []


def _pick_match_timestamp(match: dict[str, object]) -> object:
    for key in ("end", "start", "creation_time"):
        value = match.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _stringify(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
