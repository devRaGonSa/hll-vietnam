"""Historical scoreboard ingestion for the real Comunidad Hispana servers."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from .config import get_historical_scoreboard_sources
from .historical_storage import persist_historical_capture


PUBLIC_INFO_PATH = "/api/get_public_info"
LIVE_GAME_STATS_PATH = "/api/get_live_game_stats"
DEFAULT_HTTP_TIMEOUT_SECONDS = 10


def collect_historical_stats(
    *,
    persist: bool = False,
    db_path: Path | None = None,
) -> dict[str, object]:
    """Collect the current historical-ready match state from both scoreboards."""
    captures: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []

    for source in get_historical_scoreboard_sources():
        try:
            capture = collect_server_historical_stats(source)
            if persist:
                capture["storage"] = persist_historical_capture(capture, db_path=db_path)
            captures.append(capture)
        except Exception as error:  # noqa: BLE001 - keep ingestion failures isolated
            errors.append(
                {
                    "external_server_id": source["external_server_id"],
                    "scoreboard_base_url": source["scoreboard_base_url"],
                    "message": str(error),
                }
            )

    return {
        "status": "ok",
        "captures": captures,
        "capture_count": len(captures),
        "errors": errors,
    }


def collect_server_historical_stats(source: dict[str, str]) -> dict[str, object]:
    """Collect one scoreboard snapshot with match and player metrics."""
    public_info_payload = _fetch_scoreboard_json(
        source["scoreboard_base_url"],
        PUBLIC_INFO_PATH,
    )
    live_game_stats_payload = _fetch_scoreboard_json(
        source["scoreboard_base_url"],
        LIVE_GAME_STATS_PATH,
    )

    public_info = dict(public_info_payload.get("result") or {})
    live_game_stats = dict(live_game_stats_payload.get("result") or {})
    captured_at = _coerce_timestamp(live_game_stats.get("snapshot_timestamp"))

    return {
        "external_server_id": source["external_server_id"],
        "display_name": source["display_name"],
        "scoreboard_base_url": source["scoreboard_base_url"],
        "captured_at": captured_at,
        "server_name": _extract_server_name(public_info, source["display_name"]),
        "match": _build_match_record(source, public_info, live_game_stats, captured_at),
        "players": _build_player_records(live_game_stats, captured_at),
    }


def _fetch_scoreboard_json(base_url: str, path: str) -> dict[str, object]:
    request = Request(
        f"{base_url}{path}",
        headers={
            "Accept": "application/json",
            "User-Agent": "HLLVietnamBackend/0.1",
        },
    )
    with urlopen(request, timeout=DEFAULT_HTTP_TIMEOUT_SECONDS) as response:
        payload = json.loads(response.read().decode("utf-8"))

    error = payload.get("error")
    if error not in (None, [], [None]):
        raise RuntimeError(f"Scoreboard endpoint {path} returned error: {error}")

    result = payload.get("result")
    if not isinstance(result, dict):
        raise RuntimeError(f"Scoreboard endpoint {path} did not return a result object.")

    return payload


def _extract_server_name(public_info: dict[str, object], fallback_name: str) -> str:
    server_name = public_info.get("name")
    if isinstance(server_name, dict):
        resolved_name = str(server_name.get("name") or "").strip()
        if resolved_name:
            return resolved_name

    return fallback_name


def _build_match_record(
    source: dict[str, str],
    public_info: dict[str, object],
    live_game_stats: dict[str, object],
    captured_at: str,
) -> dict[str, object]:
    current_map_container = dict(public_info.get("current_map") or {})
    current_map = dict(current_map_container.get("map") or {})
    start_epoch = current_map_container.get("start")
    started_at = _coerce_timestamp(start_epoch)
    match_slug = str(current_map.get("id") or "unknown-match").strip() or "unknown-match"
    source_match_ref = f"{source['external_server_id']}:{int(start_epoch or 0)}:{match_slug}"

    duration_seconds = None
    captured_at_dt = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
    started_at_dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    if captured_at_dt >= started_at_dt:
        duration_seconds = int((captured_at_dt - started_at_dt).total_seconds())

    return {
        "source_match_ref": source_match_ref,
        "started_at": started_at,
        "ended_at": None,
        "duration_seconds": duration_seconds,
        "map_slug": match_slug,
        "map_name": str(current_map.get("pretty_name") or "Mapa no disponible"),
        "mode_name": str(current_map.get("game_mode") or "unknown"),
        "server_name": _extract_server_name(public_info, source["display_name"]),
    }


def _build_player_records(
    live_game_stats: dict[str, object],
    captured_at: str,
) -> list[dict[str, object]]:
    player_rows = live_game_stats.get("stats")
    if not isinstance(player_rows, list):
        return []

    players: list[dict[str, object]] = []
    for row in player_rows:
        if not isinstance(row, dict):
            continue

        player_name = str(row.get("player") or "").strip()
        player_ref = str(row.get("player_id") or "").strip()
        if not player_name or not player_ref:
            continue

        players.append(
            {
                "source_player_ref": player_ref,
                "canonical_name": player_name,
                "last_seen_name": player_name,
                "kills": _coerce_int(row.get("kills"), default=0),
                "deaths": _coerce_int(row.get("deaths")),
                "time_seconds": _coerce_int(row.get("time_seconds")),
                "captured_at": captured_at,
            }
        )

    return players


def _coerce_timestamp(value: object) -> str:
    if isinstance(value, (int, float)):
        resolved = datetime.fromtimestamp(value, tz=timezone.utc)
        return resolved.isoformat().replace("+00:00", "Z")

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _coerce_int(value: object, *, default: int | None = None) -> int | None:
    if value is None:
        return default

    try:
        return max(0, int(float(value)))
    except (TypeError, ValueError):
        return default


def main() -> None:
    """Allow manual historical ingestion execution during development."""
    parser = argparse.ArgumentParser(
        description="Collect scoreboard-backed historical data for Comunidad Hispana.",
    )
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Collect data without persisting it to the local SQLite database.",
    )
    args = parser.parse_args()

    payload = collect_historical_stats(persist=not args.no_persist)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
