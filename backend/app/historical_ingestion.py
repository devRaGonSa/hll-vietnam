"""Historical CRCON ingestion bootstrap and incremental refresh."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import (
    get_historical_crcon_page_size,
    get_historical_crcon_request_timeout_seconds,
)
from .historical_storage import (
    finalize_ingestion_run,
    get_refresh_cutoff_for_server,
    initialize_historical_storage,
    list_historical_servers,
    start_ingestion_run,
    upsert_historical_match,
)


PUBLIC_INFO_ENDPOINT = "/api/get_public_info"
MATCH_LIST_ENDPOINT = "/api/get_scoreboard_maps"
MATCH_DETAIL_ENDPOINT = "/api/get_map_scoreboard"


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
) -> dict[str, object]:
    """Run a first full historical import against one or all configured servers."""
    return _run_ingestion(
        mode="bootstrap",
        server_slug=server_slug,
        max_pages=max_pages,
        page_size=page_size,
        incremental=False,
    )


def run_incremental_refresh(
    *,
    server_slug: str | None = None,
    max_pages: int | None = None,
    page_size: int | None = None,
) -> dict[str, object]:
    """Refresh recent historical pages without replaying the whole archive."""
    return _run_ingestion(
        mode="incremental",
        server_slug=server_slug,
        max_pages=max_pages,
        page_size=page_size,
        incremental=True,
    )


def _run_ingestion(
    *,
    mode: str,
    server_slug: str | None,
    max_pages: int | None,
    page_size: int | None,
    incremental: bool,
) -> dict[str, object]:
    initialize_historical_storage()
    stats = IngestionStats()
    selected_servers = _select_servers(server_slug)
    processed_servers: list[dict[str, object]] = []
    runs: list[int] = []

    try:
        for server in selected_servers:
            run_id = start_ingestion_run(mode=mode, target_server_slug=str(server["slug"]))
            runs.append(run_id)
            cutoff = (
                get_refresh_cutoff_for_server(str(server["slug"]))
                if incremental
                else None
            )
            server_stats = _ingest_server(
                server=server,
                stats=stats,
                max_pages=max_pages,
                page_size=page_size,
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
    except Exception as exc:
        for run_id in runs:
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
        raise

    return {
        "status": "ok",
        "mode": mode,
        "page_size": page_size or get_historical_crcon_page_size(),
        "servers": processed_servers,
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
    stats: IngestionStats,
    max_pages: int | None,
    page_size: int | None,
    cutoff: str | None,
) -> dict[str, object]:
    resolved_page_size = page_size or get_historical_crcon_page_size()
    page_limit = max_pages or 1000000
    local_stats = IngestionStats()
    public_info = _fetch_public_info(str(server["scoreboard_base_url"]))

    for page_number in range(1, page_limit + 1):
        payload = _fetch_match_page(
            str(server["scoreboard_base_url"]),
            page=page_number,
            limit=resolved_page_size,
        )
        page_matches = _coerce_match_list(payload.get("maps"))
        if not page_matches:
            break

        local_stats.pages_processed += 1
        stats.pages_processed += 1
        stop_after_page = False

        for match_summary in page_matches:
            local_stats.matches_seen += 1
            stats.matches_seen += 1

            reference_timestamp = _pick_match_timestamp(match_summary)
            if cutoff and reference_timestamp and reference_timestamp < cutoff:
                stop_after_page = True
                continue

            detail_payload = _fetch_match_detail(
                str(server["scoreboard_base_url"]),
                match_id=str(match_summary["id"]),
            )
            delta = upsert_historical_match(
                server_slug=str(server["slug"]),
                match_payload=detail_payload,
            )
            local_stats.apply(delta)
            stats.apply(delta)

        if stop_after_page:
            break

    return {
        "server_slug": server["slug"],
        "public_name": _extract_public_name(public_info),
        "server_number": public_info.get("server_number") or server.get("server_number"),
        "pages_processed": local_stats.pages_processed,
        "matches_seen": local_stats.matches_seen,
        "matches_inserted": local_stats.matches_inserted,
        "matches_updated": local_stats.matches_updated,
        "player_rows_inserted": local_stats.player_rows_inserted,
        "player_rows_updated": local_stats.player_rows_updated,
        "cutoff": cutoff,
    }


def _select_servers(server_slug: str | None) -> list[dict[str, object]]:
    servers = list_historical_servers()
    if server_slug is None:
        return servers

    normalized = server_slug.strip()
    selected = [server for server in servers if server["slug"] == normalized]
    if not selected:
        raise ValueError(f"Unknown historical server slug: {server_slug}")
    return selected


def _fetch_public_info(base_url: str) -> dict[str, object]:
    payload = _unwrap_result(_fetch_json(base_url, PUBLIC_INFO_ENDPOINT))
    if not isinstance(payload, dict):
        raise ValueError(f"Unexpected public info payload for {base_url}")
    return payload


def _fetch_match_page(base_url: str, *, page: int, limit: int) -> dict[str, object]:
    payload = _unwrap_result(_fetch_json(
        base_url,
        MATCH_LIST_ENDPOINT,
        {"page": page, "limit": limit},
    ))
    if not isinstance(payload, dict):
        raise ValueError(f"Unexpected match list payload for {base_url} page={page}")
    return payload


def _fetch_match_detail(base_url: str, *, match_id: str) -> dict[str, object]:
    payload = _unwrap_result(_fetch_json(
        base_url,
        MATCH_DETAIL_ENDPOINT,
        {"map_id": match_id},
    ))
    if not isinstance(payload, dict):
        raise ValueError(f"Unexpected match detail payload for {base_url} match={match_id}")
    return payload


def _fetch_json(
    base_url: str,
    endpoint: str,
    query: dict[str, object] | None = None,
) -> object:
    url = f"{base_url}{endpoint}"
    if query:
        url = f"{url}?{urlencode(query)}"

    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "HLL-Vietnam-Historical-Ingestion/0.1",
        },
    )
    try:
        with urlopen(
            request,
            timeout=get_historical_crcon_request_timeout_seconds(),
        ) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"Historical CRCON request failed: {url} ({exc.code})") from exc
    except URLError as exc:
        raise RuntimeError(f"Historical CRCON request failed: {url} ({exc.reason})") from exc


def _coerce_match_list(payload: object) -> list[dict[str, object]]:
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _unwrap_result(payload: object) -> object:
    if not isinstance(payload, dict):
        return payload
    if "result" not in payload:
        return payload
    return payload.get("result")


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
        )
    else:
        result = run_incremental_refresh(
            server_slug=args.server_slug,
            max_pages=args.max_pages,
            page_size=args.page_size,
        )

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
