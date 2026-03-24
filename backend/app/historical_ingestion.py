"""Historical CRCON ingestion bootstrap and incremental refresh."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Iterable

from .config import (
    get_historical_crcon_detail_workers,
    get_historical_crcon_page_size,
)
from .data_sources import HistoricalDataSource, get_historical_data_source
from .historical_snapshots import generate_and_persist_historical_snapshots
from .historical_storage import (
    finalize_backfill_progress,
    finalize_ingestion_run,
    get_backfill_resume_page,
    get_refresh_cutoff_for_server,
    initialize_historical_storage,
    list_historical_coverage_report,
    list_historical_servers,
    mark_backfill_progress_page_completed,
    mark_backfill_progress_started,
    start_ingestion_run,
    upsert_historical_match,
)


@dataclass(slots=True)
class IngestionStats:
    """Mutable counters for one ingestion execution."""

    pages_processed: int = 0
    matches_seen: int = 0
    matches_inserted: int = 0
    matches_updated: int = 0
    player_rows_inserted: int = 0
    player_rows_updated: int = 0

    def apply(self, delta: dict[str, int]) -> None:
        self.matches_inserted += delta.get("matches_inserted", 0)
        self.matches_updated += delta.get("matches_updated", 0)
        self.player_rows_inserted += delta.get("player_rows_inserted", 0)
        self.player_rows_updated += delta.get("player_rows_updated", 0)


def run_bootstrap(
    *,
    server_slug: str | None = None,
    max_pages: int | None = None,
    page_size: int | None = None,
    start_page: int | None = None,
    detail_workers: int | None = None,
    rebuild_snapshots: bool = True,
) -> dict[str, object]:
    """Run a first full historical import against one or all configured servers."""
    return _run_ingestion(
        mode="bootstrap",
        server_slug=server_slug,
        max_pages=max_pages,
        page_size=page_size,
        start_page=start_page,
        detail_workers=detail_workers,
        incremental=False,
        rebuild_snapshots=rebuild_snapshots,
    )


def run_incremental_refresh(
    *,
    server_slug: str | None = None,
    max_pages: int | None = None,
    page_size: int | None = None,
    start_page: int | None = None,
    detail_workers: int | None = None,
    rebuild_snapshots: bool = True,
) -> dict[str, object]:
    """Refresh recent historical pages without replaying the whole archive."""
    return _run_ingestion(
        mode="incremental",
        server_slug=server_slug,
        max_pages=max_pages,
        page_size=page_size,
        start_page=start_page,
        detail_workers=detail_workers,
        incremental=True,
        rebuild_snapshots=rebuild_snapshots,
    )


def _run_ingestion(
    *,
    mode: str,
    server_slug: str | None,
    max_pages: int | None,
    page_size: int | None,
    start_page: int | None,
    detail_workers: int | None,
    incremental: bool,
    rebuild_snapshots: bool,
) -> dict[str, object]:
    initialize_historical_storage()
    stats = IngestionStats()
    data_source = get_historical_data_source()
    selected_servers = _select_servers(server_slug)
    processed_servers: list[dict[str, object]] = []
    active_runs: dict[str, int] = {}

    try:
        for server in selected_servers:
            run_id = start_ingestion_run(mode=mode, target_server_slug=str(server["slug"]))
            active_runs[str(server["slug"])] = run_id
            mark_backfill_progress_started(
                server_slug=str(server["slug"]),
                mode=mode,
                run_id=run_id,
            )
            cutoff = (
                get_refresh_cutoff_for_server(str(server["slug"]))
                if incremental
                else None
            )
            resolved_start_page = _resolve_start_page(
                start_page=start_page,
                server_slug=str(server["slug"]),
                mode=mode,
            )
            server_stats = _ingest_server(
                server=server,
                mode=mode,
                run_id=run_id,
                stats=stats,
                data_source=data_source,
                max_pages=max_pages,
                page_size=page_size,
                start_page=resolved_start_page,
                detail_workers=detail_workers,
                cutoff=cutoff,
            )
            processed_servers.append(server_stats)
            finalize_ingestion_run(
                run_id,
                status="success",
                pages_processed=server_stats["pages_processed"],
                matches_seen=server_stats["matches_seen"],
                matches_inserted=server_stats["matches_inserted"],
                matches_updated=server_stats["matches_updated"],
                player_rows_inserted=server_stats["player_rows_inserted"],
                player_rows_updated=server_stats["player_rows_updated"],
                notes=f"public_name={server_stats['public_name']}",
            )
            finalize_backfill_progress(
                server_slug=str(server["slug"]),
                mode=mode,
                run_id=run_id,
                status="success",
                archive_exhausted=bool(server_stats["archive_exhausted"]),
            )
            active_runs.pop(str(server["slug"]), None)
        if rebuild_snapshots:
            snapshot_result = generate_and_persist_historical_snapshots(server_key=server_slug)
        else:
            snapshot_result = {
                "status": "skipped",
                "reason": "snapshot-rebuild-disabled",
                "generation_policy": "handled-by-caller",
            }
    except Exception as exc:
        for active_server_slug, run_id in active_runs.items():
            finalize_ingestion_run(
                run_id,
                status="failed",
                pages_processed=stats.pages_processed,
                matches_seen=stats.matches_seen,
                matches_inserted=stats.matches_inserted,
                matches_updated=stats.matches_updated,
                player_rows_inserted=stats.player_rows_inserted,
                player_rows_updated=stats.player_rows_updated,
                notes=str(exc),
            )
            finalize_backfill_progress(
                server_slug=active_server_slug,
                mode=mode,
                run_id=run_id,
                status="failed",
                error_message=str(exc),
            )
        raise

    return {
        "status": "ok",
        "mode": mode,
        "source_provider": data_source.source_kind,
        "page_size": page_size or get_historical_crcon_page_size(),
        "start_page": start_page,
        "detail_workers": detail_workers or get_historical_crcon_detail_workers(),
        "servers": processed_servers,
        "coverage": list_historical_coverage_report(server_slug=server_slug),
        "snapshot_result": snapshot_result,
        "totals": {
            "pages_processed": stats.pages_processed,
            "matches_seen": stats.matches_seen,
            "matches_inserted": stats.matches_inserted,
            "matches_updated": stats.matches_updated,
            "player_rows_inserted": stats.player_rows_inserted,
            "player_rows_updated": stats.player_rows_updated,
        },
    }


def _ingest_server(
    *,
    server: dict[str, object],
    mode: str,
    run_id: int,
    stats: IngestionStats,
    data_source: HistoricalDataSource,
    max_pages: int | None,
    page_size: int | None,
    start_page: int,
    detail_workers: int | None,
    cutoff: str | None,
) -> dict[str, object]:
    resolved_page_size = page_size or get_historical_crcon_page_size()
    resolved_detail_workers = detail_workers or get_historical_crcon_detail_workers()
    page_limit = max_pages or 1000000
    start_page = max(1, start_page)
    local_stats = IngestionStats()
    public_info = data_source.fetch_public_info(base_url=str(server["scoreboard_base_url"]))
    discovered_total_matches: int | None = None
    last_page_processed: int | None = None
    archive_exhausted = False

    for page_number in range(start_page, start_page + page_limit):
        payload = data_source.fetch_match_page(
            base_url=str(server["scoreboard_base_url"]),
            page=page_number,
            limit=resolved_page_size,
        )
        if discovered_total_matches is None:
            discovered_total_matches = _coerce_int(payload.get("total"))
        page_matches = _coerce_match_list(payload.get("maps"))
        if not page_matches:
            archive_exhausted = True
            break

        local_stats.pages_processed += 1
        stats.pages_processed += 1
        last_page_processed = page_number
        stop_after_page = False
        match_ids_to_fetch: list[str] = []

        for match_summary in page_matches:
            local_stats.matches_seen += 1
            stats.matches_seen += 1

            reference_timestamp = _pick_match_timestamp(match_summary)
            if cutoff and reference_timestamp and reference_timestamp < cutoff:
                stop_after_page = True
                continue

            match_id = _stringify(match_summary.get("id"))
            if match_id:
                match_ids_to_fetch.append(match_id)

        for detail_payload in data_source.fetch_match_details(
            base_url=str(server["scoreboard_base_url"]),
            match_ids=match_ids_to_fetch,
            max_workers=resolved_detail_workers,
        ):
            delta = upsert_historical_match(
                server_slug=str(server["slug"]),
                match_payload=detail_payload,
            )
            local_stats.apply(delta)
            stats.apply(delta)

        mark_backfill_progress_page_completed(
            server_slug=str(server["slug"]),
            mode=mode,
            page_number=page_number,
            page_size=resolved_page_size,
            run_id=run_id,
            discovered_total_matches=discovered_total_matches,
        )

        if stop_after_page:
            break

    return {
        "server_slug": server["slug"],
        "public_name": _extract_public_name(public_info),
        "server_number": public_info.get("server_number") or server.get("server_number"),
        "source_provider": data_source.source_kind,
        "pages_processed": local_stats.pages_processed,
        "matches_seen": local_stats.matches_seen,
        "discovered_total_matches": discovered_total_matches,
        "matches_inserted": local_stats.matches_inserted,
        "matches_updated": local_stats.matches_updated,
        "player_rows_inserted": local_stats.player_rows_inserted,
        "player_rows_updated": local_stats.player_rows_updated,
        "start_page": start_page,
        "last_page_processed": last_page_processed,
        "cutoff": cutoff,
        "archive_exhausted": archive_exhausted,
    }


def _resolve_start_page(
    *,
    start_page: int | None,
    server_slug: str,
    mode: str,
) -> int:
    if start_page is not None:
        return max(1, start_page)
    if mode != "bootstrap":
        return 1
    return get_backfill_resume_page(server_slug, mode=mode)


def _select_servers(server_slug: str | None) -> list[dict[str, object]]:
    servers = list_historical_servers()
    if server_slug is None:
        return servers

    normalized = server_slug.strip()
    selected = [server for server in servers if server["slug"] == normalized]
    if not selected:
        raise ValueError(f"Unknown historical server slug: {server_slug}")
    return selected


def _coerce_match_list(payload: object) -> list[dict[str, object]]:
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _pick_match_timestamp(match_payload: dict[str, object]) -> str | None:
    for key in ("end", "start", "creation_time"):
        value = match_payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_public_name(public_info: dict[str, object]) -> str | None:
    name_value = public_info.get("name")
    if isinstance(name_value, str):
        return name_value
    if isinstance(name_value, dict):
        raw_name = name_value.get("name")
        return raw_name.strip() if isinstance(raw_name, str) and raw_name.strip() else None
    return None


def _stringify(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for manual historical ingestion runs."""
    parser = argparse.ArgumentParser(
        description="Historical CRCON ingestion for HLL Vietnam.",
    )
    parser.add_argument(
        "mode",
        choices=("bootstrap", "refresh"),
        help="bootstrap imports the archive, refresh only recent pages",
    )
    parser.add_argument(
        "--server",
        dest="server_slug",
        help="optional historical server slug",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        help="optional page cap for local validation",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        help="override CRCON page size",
    )
    parser.add_argument(
        "--start-page",
        type=int,
        help="override the resume page; bootstrap uses persisted progress when omitted",
    )
    parser.add_argument(
        "--detail-workers",
        type=int,
        help="parallel worker count for per-match detail requests",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    """Run the historical ingestion CLI."""
    parser = build_arg_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.mode == "bootstrap":
        result = run_bootstrap(
            server_slug=args.server_slug,
            max_pages=args.max_pages,
            page_size=args.page_size,
            start_page=args.start_page,
            detail_workers=args.detail_workers,
        )
    else:
        result = run_incremental_refresh(
            server_slug=args.server_slug,
            max_pages=args.max_pages,
            page_size=args.page_size,
            start_page=args.start_page,
            detail_workers=args.detail_workers,
        )

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
