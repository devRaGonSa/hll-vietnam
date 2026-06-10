#!/usr/bin/env python3
"""Audit public HTTP requests exposed by the HLL Vietnam application."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT_SECONDS = 25.0
KNOWN_MATCH_ID = "comunidad-hispana-01:1781023156:1781028555:purpleheartlanewarfare"
KNOWN_PLAYER_SEARCH = "Medu"

RANKING_METRICS = (
    "kills",
    "deaths",
    "teamkills",
    "matches_considered",
    "kd_ratio",
    "kills_per_match",
)
RANKING_SCOPES = ("all", "comunidad-hispana-01", "comunidad-hispana-02")
HISTORICAL_SCOPES = ("all-servers", "comunidad-hispana-01", "comunidad-hispana-02")
HISTORICAL_LEGACY_METRICS = ("kills", "deaths", "support", "matches_over_100_kills")
PLAYER_EVENT_VIEWS = ("most-killed", "death-by", "duels", "weapon-kills", "teamkills")


@dataclass(frozen=True)
class ProbeSpec:
    id: str
    kind: str
    context: str
    method: str
    path: str
    parameters: str


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure public HLL Vietnam frontend/backend request surfaces."
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Base URL to audit. Default: {DEFAULT_BASE_URL}",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Per-request timeout in seconds. Default: {DEFAULT_TIMEOUT_SECONDS}",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="JSON output path. Default: tmp/public_request_audit.json.",
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Repository root for static discovery metadata. Default: auto/cwd.",
    )
    parser.add_argument(
        "--max-probes",
        type=int,
        default=0,
        help="Optional cap for smoke runs. 0 means all probes.",
    )
    args = parser.parse_args()

    base_url = normalize_base_url(args.base_url)
    repo_root = resolve_repo_root(args.repo_root)
    output_path = resolve_output_path(args.output)

    specs = build_probe_specs()
    if args.max_probes and args.max_probes > 0:
        specs = specs[: args.max_probes]

    results: list[dict[str, Any]] = []
    dynamic_player_id: str | None = None
    index = 0
    while index < len(specs):
        spec = specs[index]
        result = run_probe(base_url=base_url, spec=spec, timeout_seconds=args.timeout)
        results.append(result)
        print_result_row(result)

        if spec.id == "stats-player-search-medu" and dynamic_player_id is None:
            dynamic_player_id = extract_first_player_id(result.get("json"))
            if dynamic_player_id:
                specs.extend(build_player_dependent_specs(dynamic_player_id))

        index += 1

    payload = {
        "audit": {
            "base_url": base_url,
            "timeout_seconds": args.timeout,
            "generated_at_epoch": time.time(),
            "probe_count": len(results),
        },
        "summary": summarize_results(results),
        "discovery": discover_static_requests(repo_root),
        "results": strip_json_payloads(results),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

    print()
    print_summary(payload["summary"])
    print(f"Saved JSON results to {output_path}")
    return 0


def build_probe_specs() -> list[ProbeSpec]:
    specs: list[ProbeSpec] = []
    seen: set[str] = set()

    def add(
        id_: str,
        path: str,
        *,
        kind: str = "backend-api",
        context: str = "backend",
        parameters: str = "",
    ) -> None:
        if id_ in seen:
            return
        seen.add(id_)
        specs.append(
            ProbeSpec(
                id=id_,
                kind=kind,
                context=context,
                method="GET",
                path=path,
                parameters=parameters,
            )
        )

    add("health", "/health", context="health", parameters="none")
    add("api-community", "/api/community", context="home", parameters="none")
    add("api-trailer", "/api/trailer", context="home", parameters="none")
    add("api-discord", "/api/discord", context="home", parameters="none")
    add("api-servers", "/api/servers", context="home", parameters="none")
    add("api-servers-latest", "/api/servers/latest", context="home", parameters="none")
    add("api-servers-history", "/api/servers/history?limit=20", context="server-history", parameters="limit=20")
    for server in ("comunidad-hispana-01", "comunidad-hispana-02"):
        add(
            f"api-servers-{server}-history",
            f"/api/servers/{server}/history?limit=20",
            context="server-history",
            parameters="server path, limit=20",
        )

    for timeframe in ("weekly", "monthly", "annual"):
        for server in RANKING_SCOPES:
            for metric in RANKING_METRICS:
                params = {
                    "timeframe": timeframe,
                    "server_id": server,
                    "metric": metric,
                    "limit": "20",
                }
                if timeframe == "annual":
                    params["year"] = "2026"
                query = "&".join(f"{key}={quote(value)}" for key, value in params.items())
                add(
                    f"ranking-{timeframe}-{server}-{metric}",
                    f"/api/ranking?{query}",
                    context="ranking.html",
                    parameters="timeframe, server_id, metric, limit, year for annual",
                )

    add(
        "ranking-weekly-all-servers-alias",
        "/api/ranking?timeframe=weekly&server_id=all-servers&metric=kills&limit=20",
        context="ranking.html",
        parameters="server_id=all-servers alias",
    )
    add(
        "stats-player-search-medu",
        f"/api/stats/players/search?q={quote(KNOWN_PLAYER_SEARCH)}&server_id=all&limit=10",
        context="stats.html",
        parameters="q=Medu, server_id=all, limit=10",
    )
    add(
        "stats-annual-ranking",
        "/api/stats/rankings/annual?year=2026&server_id=all&metric=kills&limit=20",
        context="stats.html",
        parameters="year=2026, server_id=all, metric=kills, limit=20",
    )

    for server in ("comunidad-hispana-01", "comunidad-hispana-02"):
        add(
            f"current-match-{server}",
            f"/api/current-match?server={server}",
            context="partida-actual.html",
            parameters="server",
        )
        add(
            f"current-match-kills-{server}",
            f"/api/current-match/kills?server={server}&limit=30",
            context="partida-actual.html",
            parameters="server, limit=30",
        )
        add(
            f"current-match-players-{server}",
            f"/api/current-match/players?server={server}",
            context="partida-actual.html",
            parameters="server",
        )

    for server in HISTORICAL_SCOPES:
        add(
            f"historical-server-summary-{server}",
            f"/api/historical/server-summary?server={server}",
            context="historico.html legacy",
            parameters="server",
        )
        add(
            f"historical-recent-matches-{server}",
            f"/api/historical/recent-matches?server={server}&limit=20",
            context="historico.html legacy",
            parameters="server, limit=20",
        )
        add(
            f"snapshot-server-summary-{server}",
            f"/api/historical/snapshots/server-summary?server={server}",
            context="historico.html",
            parameters="server",
        )
        add(
            f"snapshot-recent-matches-{server}",
            f"/api/historical/snapshots/recent-matches?server={server}&limit=100",
            context="historico.html",
            parameters="server, limit=100",
        )
        add(
            f"weekly-top-kills-{server}",
            f"/api/historical/weekly-top-kills?server={server}&limit=10",
            context="historical legacy API",
            parameters="server, limit=10",
        )

        for timeframe in ("weekly", "monthly"):
            for metric in HISTORICAL_LEGACY_METRICS:
                add(
                    f"historical-leaderboard-{timeframe}-{server}-{metric}",
                    (
                        "/api/historical/leaderboard?"
                        f"server={server}&timeframe={timeframe}&metric={metric}&limit=10"
                    ),
                    context="historical legacy API",
                    parameters="server, timeframe, metric, limit=10",
                )
                add(
                    f"snapshot-leaderboard-{timeframe}-{server}-{metric}",
                    (
                        "/api/historical/snapshots/leaderboard?"
                        f"server={server}&timeframe={timeframe}&metric={metric}&limit=10"
                    ),
                    context="historico.html",
                    parameters="server, timeframe, metric, limit=10",
                )

        add(
            f"historical-weekly-leaderboard-{server}",
            f"/api/historical/weekly-leaderboard?server={server}&metric=kills&limit=10",
            context="historical legacy API",
            parameters="server, metric=kills, limit=10",
        )
        add(
            f"historical-monthly-leaderboard-{server}",
            f"/api/historical/monthly-leaderboard?server={server}&metric=kills&limit=10",
            context="historical legacy API",
            parameters="server, metric=kills, limit=10",
        )
        add(
            f"snapshot-weekly-leaderboard-{server}",
            f"/api/historical/snapshots/weekly-leaderboard?server={server}&metric=kills&limit=10",
            context="historico.html",
            parameters="server, metric=kills, limit=10",
        )
        add(
            f"snapshot-monthly-leaderboard-{server}",
            f"/api/historical/snapshots/monthly-leaderboard?server={server}&metric=kills&limit=10",
            context="historico.html",
            parameters="server, metric=kills, limit=10",
        )
        add(
            f"monthly-mvp-{server}",
            f"/api/historical/monthly-mvp?server={server}&limit=10",
            context="historical public API",
            parameters="server, limit=10",
        )
        add(
            f"monthly-mvp-v2-{server}",
            f"/api/historical/monthly-mvp-v2?server={server}&limit=10",
            context="historical public API",
            parameters="server, limit=10",
        )
        add(
            f"snapshot-monthly-mvp-{server}",
            f"/api/historical/snapshots/monthly-mvp?server={server}&limit=10",
            context="historical snapshots",
            parameters="server, limit=10",
        )
        add(
            f"snapshot-monthly-mvp-v2-{server}",
            f"/api/historical/snapshots/monthly-mvp-v2?server={server}&limit=10",
            context="historical snapshots",
            parameters="server, limit=10",
        )
        for view in PLAYER_EVENT_VIEWS:
            add(
                f"player-events-{server}-{view}",
                f"/api/historical/player-events?server={server}&view={view}&limit=10",
                context="historical public API",
                parameters="server, view, limit=10",
            )
            add(
                f"snapshot-player-events-{server}-{view}",
                f"/api/historical/snapshots/player-events?server={server}&view={view}&limit=10",
                context="historical snapshots",
                parameters="server, view, limit=10",
            )

    add(
        "historical-match-detail-known",
        (
            "/api/historical/matches/detail?"
            "server=comunidad-hispana-01&match="
            f"{quote(KNOWN_MATCH_ID, safe='')}"
        ),
        context="historico-partida.html",
        parameters="server, match",
    )

    add(
        "elo-mmr-leaderboard-paused",
        "/api/historical/elo-mmr/leaderboard?server=all-servers&limit=10",
        context="paused public API",
        parameters="server, limit=10",
    )
    return specs


def build_player_dependent_specs(player_id: str) -> list[ProbeSpec]:
    quoted_player = quote(player_id, safe="")
    return [
        ProbeSpec(
            id="stats-player-profile-weekly",
            kind="backend-api",
            context="stats.html",
            method="GET",
            path=f"/api/stats/players/{quoted_player}?timeframe=weekly&server_id=all",
            parameters="player_id from search, timeframe=weekly, server_id=all",
        ),
        ProbeSpec(
            id="stats-player-profile-monthly",
            kind="backend-api",
            context="stats.html",
            method="GET",
            path=f"/api/stats/players/{quoted_player}?timeframe=monthly&server_id=all",
            parameters="player_id from search, timeframe=monthly, server_id=all",
        ),
        ProbeSpec(
            id="historical-player-profile",
            kind="backend-api",
            context="historical public API",
            method="GET",
            path=f"/api/historical/player-profile?player={quoted_player}",
            parameters="player from search",
        ),
        ProbeSpec(
            id="elo-mmr-player-paused",
            kind="backend-api",
            context="paused public API",
            method="GET",
            path=f"/api/historical/elo-mmr/player?server=all-servers&player={quoted_player}",
            parameters="player from search, server=all-servers",
        ),
    ]


def run_probe(*, base_url: str, spec: ProbeSpec, timeout_seconds: float) -> dict[str, Any]:
    url = f"{base_url}{spec.path}"
    started = time.perf_counter()
    status_code: int | None = None
    body = b""
    error: str | None = None
    headers: dict[str, str] = {}

    try:
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "HLL-Vietnam-Public-Request-Audit/1.0",
            },
            method=spec.method,
        )
        with urlopen(request, timeout=timeout_seconds) as response:
            status_code = int(response.status)
            headers = {key.lower(): value for key, value in response.headers.items()}
            body = response.read()
    except HTTPError as exc:
        status_code = int(exc.code)
        headers = {key.lower(): value for key, value in exc.headers.items()}
        body = exc.read()
        error = f"HTTPError: {exc.code}"
    except URLError as exc:
        error = f"URLError: {exc.reason}"
    except TimeoutError:
        error = "TimeoutError"
    except Exception as exc:  # noqa: BLE001 - audit must continue
        error = f"{type(exc).__name__}: {exc}"

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    parsed_json = parse_json_body(body)
    summary = summarize_json(parsed_json)
    severity = classify_result(
        status_code=status_code,
        elapsed_ms=elapsed_ms,
        error=error,
        fallback_used=summary.get("fallback_used"),
        snapshot_status=summary.get("snapshot_status"),
    )
    return {
        **asdict(spec),
        "url": url,
        "status_code": status_code,
        "elapsed_ms": elapsed_ms,
        "response_size_bytes": len(body),
        "content_type": headers.get("content-type"),
        "json_status": summary.get("json_status"),
        "data_source": summary.get("data_source"),
        "fallback_used": summary.get("fallback_used"),
        "fallback_reason": summary.get("fallback_reason"),
        "snapshot_status": summary.get("snapshot_status"),
        "item_count": summary.get("item_count"),
        "found": summary.get("found"),
        "severity": severity,
        "error": error,
        "json": parsed_json,
    }


def parse_json_body(body: bytes) -> Any:
    if not body:
        return None
    try:
        return json.loads(body.decode("utf-8"))
    except Exception:
        return None


def summarize_json(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    source_payload = data.get("source") if isinstance(data.get("source"), dict) else {}
    items = data.get("items")
    if isinstance(items, list):
        item_count = len(items)
    elif isinstance(data.get("item"), dict):
        item_count = 1
    elif isinstance(data.get("profile"), dict):
        item_count = 1
    else:
        item_count = None
    return {
        "json_status": payload.get("status"),
        "data_source": data.get("source")
        if isinstance(data.get("source"), str)
        else source_payload.get("read_model") or source_payload.get("primary_source"),
        "fallback_used": data.get("fallback_used")
        if "fallback_used" in data
        else source_payload.get("fallback_used"),
        "fallback_reason": data.get("fallback_reason")
        if "fallback_reason" in data
        else source_payload.get("fallback_reason"),
        "snapshot_status": data.get("snapshot_status"),
        "item_count": item_count,
        "found": data.get("found"),
    }


def classify_result(
    *,
    status_code: int | None,
    elapsed_ms: float,
    error: str | None,
    fallback_used: Any,
    snapshot_status: Any,
) -> str:
    if error or status_code is None or status_code >= 500 or elapsed_ms >= 10000:
        return "CRITICAL"
    if status_code >= 400 or elapsed_ms >= 2500 or fallback_used is True:
        return "WARNING"
    if str(snapshot_status or "").lower() == "missing":
        return "WARNING"
    return "OK"


def extract_first_player_id(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    data = payload.get("data")
    if not isinstance(data, dict):
        return None
    items = data.get("items")
    if not isinstance(items, list):
        return None
    for item in items:
        if isinstance(item, dict) and str(item.get("player_id") or "").strip():
            return str(item["player_id"]).strip()
    return None


def discover_static_requests(repo_root: Path) -> dict[str, Any]:
    backend_paths: set[str] = set()
    frontend_literals: set[str] = set()
    fetch_occurrences: list[dict[str, Any]] = []
    localhost_refs: list[dict[str, Any]] = []

    routes_path = repo_root / "backend" / "app" / "routes.py"
    if routes_path.exists():
        text = routes_path.read_text(encoding="utf-8")
        for value in re.findall(r"['\"](/(?:api/[^'\"]+|health))['\"]", text):
            backend_paths.add(value)

    frontend_root = repo_root / "frontend"
    if frontend_root.exists():
        for path in sorted(frontend_root.rglob("*")):
            if path.suffix.lower() not in {".html", ".js"}:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for value in re.findall(r"/api/[A-Za-z0-9_./?=&%${}()+:,\\-]+|/health", text):
                frontend_literals.add(value)
            for line_number, line in enumerate(text.splitlines(), start=1):
                if "fetch(" in line:
                    fetch_occurrences.append(
                        {
                            "file": str(path.relative_to(repo_root)),
                            "line": line_number,
                            "text": line.strip(),
                        }
                    )
                if "127.0.0.1" in line or "localhost" in line:
                    localhost_refs.append(
                        {
                            "file": str(path.relative_to(repo_root)),
                            "line": line_number,
                            "text": line.strip(),
                        }
                    )

    return {
        "repo_root": str(repo_root),
        "backend_route_paths": sorted(backend_paths),
        "frontend_api_literals": sorted(frontend_literals),
        "frontend_fetch_occurrences": fetch_occurrences,
        "frontend_localhost_references": localhost_refs,
    }


def summarize_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    severity_counts = {"OK": 0, "WARNING": 0, "CRITICAL": 0}
    status_counts: dict[str, int] = {}
    launched = 0
    for result in results:
        launched += 1
        severity = str(result.get("severity") or "WARNING")
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
        status_key = str(result.get("status_code"))
        status_counts[status_key] = status_counts.get(status_key, 0) + 1
    slowest = sorted(
        (
            {
                "id": result.get("id"),
                "path": result.get("path"),
                "elapsed_ms": result.get("elapsed_ms"),
                "status_code": result.get("status_code"),
                "severity": result.get("severity"),
            }
            for result in results
        ),
        key=lambda item: float(item.get("elapsed_ms") or 0),
        reverse=True,
    )[:10]
    return {
        "launched": launched,
        "severity_counts": severity_counts,
        "status_counts": status_counts,
        "slowest": slowest,
    }


def strip_json_payloads(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stripped = []
    for result in results:
        item = dict(result)
        item.pop("json", None)
        stripped.append(item)
    return stripped


def print_result_row(result: dict[str, Any]) -> None:
    status = result.get("status_code")
    elapsed = result.get("elapsed_ms")
    severity = result.get("severity")
    size = result.get("response_size_bytes")
    fallback = result.get("fallback_used")
    print(
        f"{severity:8} {str(status):>4} {elapsed:>9.2f} ms {size:>9} B "
        f"fallback={str(fallback):<5} {result['id']}"
    )


def print_summary(summary: dict[str, Any]) -> None:
    print("Summary")
    print(f"  launched: {summary['launched']}")
    print(f"  OK: {summary['severity_counts'].get('OK', 0)}")
    print(f"  WARNING: {summary['severity_counts'].get('WARNING', 0)}")
    print(f"  CRITICAL: {summary['severity_counts'].get('CRITICAL', 0)}")
    print("  slowest:")
    for item in summary.get("slowest", []):
        print(
            "    "
            f"{item.get('elapsed_ms')} ms {item.get('status_code')} "
            f"{item.get('severity')} {item.get('id')}"
        )


def normalize_base_url(value: str) -> str:
    return str(value or DEFAULT_BASE_URL).strip().rstrip("/")


def resolve_repo_root(raw_value: str | None) -> Path:
    if raw_value:
        return Path(raw_value).resolve()
    cwd = Path.cwd().resolve()
    if (cwd / "backend" / "app" / "routes.py").exists():
        return cwd
    script_path = Path(__file__).resolve()
    for candidate in (script_path.parent, *script_path.parents):
        if (candidate / "backend" / "app" / "routes.py").exists():
            return candidate
    return cwd


def resolve_output_path(raw_value: str | None) -> Path:
    if raw_value:
        return Path(raw_value)
    tmp_path = Path("tmp") / "public_request_audit.json"
    try:
        tmp_path.parent.mkdir(parents=True, exist_ok=True)
        return tmp_path
    except OSError:
        return Path("docs") / "public_request_audit_results.example.json"


if __name__ == "__main__":
    sys.exit(main())
