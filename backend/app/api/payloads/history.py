"""Historical match browsing and summary compatibility payloads."""

from __future__ import annotations

from ...config import (
    get_historical_data_source_kind,
    get_historical_match_source,
    get_live_data_source_kind,
)
from ...data_sources import (
    LIVE_SOURCE_A2S,
    SOURCE_KIND_PUBLIC_SCOREBOARD,
    SOURCE_KIND_RCON,
    build_historical_runtime_source_policy,
    build_source_attempt,
    build_source_policy,
    get_rcon_historical_read_model,
)
from ...historical_snapshots import DEFAULT_SNAPSHOT_WINDOW, SNAPSHOT_TYPE_RECENT_MATCHES
from ...historical_storage import (
    ALL_SERVERS_SLUG,
    get_historical_match_detail,
    list_historical_server_summaries,
    list_recent_historical_matches,
)
from ...rcon_historical_read_model import get_rcon_historical_match_detail
from ...services.history import build_crcon_match_detail_payload, build_crcon_recent_matches_payload
from .common import (
    _build_historical_snapshot_metadata,
    _get_historical_snapshot_record,
    _resolve_historical_fallback_policy,
)
from .rankings import build_historical_server_summary_snapshot_payload

def build_recent_historical_matches_payload(
    *,
    limit: int = 20,
    server_slug: str | None = None,
    page: int = 1,
) -> dict[str, object]:
    """Return recent historical matches from persisted CRCON data."""
    if get_historical_match_source() == "crcon":
        return build_crcon_recent_matches_payload(
            limit=limit,
            server_slug=server_slug,
            page=page,
        )
    if server_slug:
        return _build_recent_historical_matches_legacy_snapshot_payload(
            limit=limit,
            server_slug=server_slug,
        )

    if get_historical_data_source_kind() == "rcon":
        data_source = get_rcon_historical_read_model()
        if data_source is not None:
            capabilities = data_source.describe_capabilities()
            try:
                items = data_source.list_recent_activity(server_key=server_slug, limit=limit)
            except Exception as error:  # noqa: BLE001 - explicit runtime fallback boundary
                items = []
                rcon_source_policy = build_historical_runtime_source_policy(
                    operation="historical-recent-matches",
                    rcon_status="error",
                    fallback_reason="rcon-historical-read-model-request-failed",
                    rcon_message=str(error),
                )
            else:
                rcon_source_policy = build_historical_runtime_source_policy(
                    operation="historical-recent-matches",
                    rcon_status=(
                        "success"
                        if data_source.has_recent_activity_coverage(items)
                        else "empty"
                    ),
                    fallback_reason="rcon-historical-read-model-has-no-recent-activity",
                )

            if not bool(rcon_source_policy.get("fallback_used")):
                if 0 < len(items) < limit and not _recent_items_include_rcon_results(items):
                    fallback_items = [
                        _with_recent_result_source(item, "public-scoreboard-fallback")
                        for item in list_recent_historical_matches(
                            limit=limit,
                            server_slug=server_slug,
                        )
                    ]
                    merged_items = _merge_recent_match_items(
                        primary_items=items,
                        fallback_items=fallback_items,
                        limit=limit,
                    )
                    if len(merged_items) > len(items):
                        return {
                            "status": "ok",
                            "data": {
                                "title": "Actividad competitiva reciente capturada por RCON",
                                "context": "historical-recent-matches",
                                "source": "hybrid-rcon-plus-public-scoreboard",
                                "historical_data_source": "rcon",
                                "supported": True,
                                "coverage_basis": "rcon-competitive-windows-plus-public-scoreboard-fallback",
                                "limit": limit,
                                "server_slug": server_slug,
                                **build_source_policy(
                                    primary_source=SOURCE_KIND_RCON,
                                    selected_source="hybrid-rcon-plus-public-scoreboard",
                                    fallback_used=True,
                                    fallback_reason=(
                                        "rcon-historical-recent-matches-did-not-reach-requested-limit"
                                    ),
                                    source_attempts=[
                                        build_source_attempt(
                                            source=SOURCE_KIND_RCON,
                                            role="primary",
                                            status="success",
                                            reason="historical-recent-matches-served-by-rcon",
                                        ),
                                        build_source_attempt(
                                            source=SOURCE_KIND_PUBLIC_SCOREBOARD,
                                            role="fallback",
                                            status="success",
                                            reason="historical-recent-matches-completed-from-public-scoreboard",
                                            message=(
                                                f"RCON returned {len(items)} items, completed to "
                                                f"{len(merged_items)} of requested {limit}."
                                            ),
                                        ),
                                    ],
                                ),
                                "items": merged_items,
                                "capabilities": capabilities,
                            },
                        }
                return {
                    "status": "ok",
                    "data": {
                        "title": "Actividad competitiva reciente capturada por RCON",
                        "context": "historical-recent-matches",
                        "source": "rcon-historical-competitive-read-model",
                        "historical_data_source": "rcon",
                        "supported": True,
                        "coverage_basis": "rcon-competitive-windows",
                        "limit": limit,
                        "server_slug": server_slug,
                        **rcon_source_policy,
                        "items": items,
                        "capabilities": capabilities,
                    },
                }
    items = [
        _with_recent_result_source(item, "public-scoreboard-fallback")
        for item in list_recent_historical_matches(limit=limit, server_slug=server_slug)
    ]
    return {
        "status": "ok",
        "data": {
            "title": "Partidas recientes por servidor",
            "context": "historical-recent-matches",
            "source": "historical-crcon-storage",
            "limit": limit,
            "server_slug": server_slug,
            **(
                rcon_source_policy
                if get_historical_data_source_kind() == "rcon"
                and "rcon_source_policy" in locals()
                else _resolve_historical_fallback_policy(
                    fallback_reason="rcon-historical-read-model-has-no-recent-activity",
                )
            ),
            "items": items,
        },
    }


def _build_recent_historical_matches_legacy_snapshot_payload(
    *,
    limit: int,
    server_slug: str,
) -> dict[str, object]:
    snapshot_payload = build_recent_historical_matches_snapshot_payload(
        limit=limit,
        server_slug=server_slug,
    )
    data = dict(snapshot_payload.get("data") or {})
    data.update(
        {
            "title": "Partidas recientes por servidor",
            "context": "historical-recent-matches",
            "source": "historical-precomputed-snapshots",
            "historical_data_source": get_historical_data_source_kind(),
            "coverage_basis": "precomputed-recent-matches-snapshot",
            "legacy_endpoint_policy": "snapshot-read-only-fast-path",
        }
    )
    return {"status": snapshot_payload.get("status", "ok"), "data": data}


def build_historical_match_detail_payload(
    *,
    server_slug: str,
    match_id: str,
) -> dict[str, object]:
    """Return available detail for one historical match without inventing external URLs."""
    if get_historical_match_source() == "crcon":
        return build_crcon_match_detail_payload(
            server_slug=server_slug,
            match_id=match_id,
        )
    if get_historical_data_source_kind() == SOURCE_KIND_RCON:
        item = get_rcon_historical_match_detail(
            server_key=server_slug,
            match_id=match_id,
        )
        if item is not None:
            return {
                "status": "ok",
                "data": {
                    "title": "Detalle de partida historica",
                    "context": "historical-match-detail",
                    "source": "rcon-historical-competitive-read-model",
                    "found": True,
                    **build_source_policy(
                        primary_source=SOURCE_KIND_RCON,
                        selected_source=SOURCE_KIND_RCON,
                        source_attempts=[
                            build_source_attempt(
                                source=SOURCE_KIND_RCON,
                                role="primary",
                                status="success",
                                reason="historical-match-detail-served-by-rcon",
                            )
                        ],
                    ),
                    "item": item,
                },
            }
        return {
            "status": "ok",
            "data": {
                "title": "Detalle de partida historica",
                "context": "historical-match-detail",
                "source": "rcon-historical-competitive-read-model",
                "found": False,
                **build_source_policy(
                    primary_source=SOURCE_KIND_RCON,
                    selected_source=SOURCE_KIND_RCON,
                    fallback_used=False,
                    fallback_reason=None,
                    source_attempts=[
                        build_source_attempt(
                            source=SOURCE_KIND_RCON,
                            role="primary",
                            status="empty",
                            reason="historical-match-detail-read-model-missing",
                        )
                    ],
                ),
                "item": None,
            },
        }

    item = get_historical_match_detail(server_slug=server_slug, match_id=match_id)
    return {
        "status": "ok",
        "data": {
            "title": "Detalle de partida historica",
            "context": "historical-match-detail",
            "source": "historical-crcon-storage",
            "found": item is not None,
            **(
                _resolve_historical_fallback_policy(
                    fallback_reason="rcon-historical-read-model-has-no-match-detail"
                )
                if get_historical_data_source_kind() == SOURCE_KIND_RCON
                else build_source_policy(
                    primary_source=SOURCE_KIND_PUBLIC_SCOREBOARD,
                    selected_source=SOURCE_KIND_PUBLIC_SCOREBOARD,
                    source_attempts=[
                        build_source_attempt(
                            source=SOURCE_KIND_PUBLIC_SCOREBOARD,
                            role="primary",
                            status="success" if item is not None else "empty",
                            reason="historical-match-detail-served-by-public-scoreboard",
                        )
                    ],
                )
            ),
            "item": item,
        },
    }


def build_recent_historical_matches_snapshot_payload(
    *,
    limit: int = 20,
    server_slug: str | None = None,
    page: int = 1,
) -> dict[str, object]:
    """Return one precomputed recent-matches snapshot."""
    if get_historical_match_source() == "crcon":
        return build_crcon_recent_matches_payload(
            limit=limit,
            server_slug=server_slug,
            page=page,
        )
    snapshot = _get_historical_snapshot_record(
        server_key=server_slug,
        snapshot_type=SNAPSHOT_TYPE_RECENT_MATCHES,
        window=DEFAULT_SNAPSHOT_WINDOW,
    )
    payload = snapshot.get("payload") if snapshot else {}
    items = payload.get("items") if isinstance(payload, dict) else None
    sliced_items = list(items[:limit]) if isinstance(items, list) else []
    return {
        "status": "ok",
        "data": {
            "title": "Snapshot historico de partidas recientes por servidor",
            "context": "historical-recent-matches-snapshot",
            "source": "historical-precomputed-snapshots",
            "server_slug": server_slug,
            "found": snapshot is not None,
            **_build_historical_snapshot_metadata(snapshot),
            "snapshot_limit": payload.get("limit") if isinstance(payload, dict) else None,
            "limit": limit,
            **(
                build_source_policy(
                    primary_source=SOURCE_KIND_RCON,
                    selected_source=SOURCE_KIND_RCON,
                    source_attempts=[
                        build_source_attempt(
                            source=SOURCE_KIND_RCON,
                            role="primary",
                            status="success",
                            reason="recent-matches-snapshot-served-by-rcon-competitive-model",
                        )
                    ],
                )
                if get_historical_data_source_kind() == SOURCE_KIND_RCON and sliced_items
                else _resolve_historical_fallback_policy(
                    fallback_reason="rcon-historical-read-model-does-not-support-historical-snapshots-yet",
                )
            ),
            "items": sliced_items,
        },
    }


def build_historical_server_summary_payload(
    *,
    server_slug: str | None = None,
) -> dict[str, object]:
    """Return aggregated historical metrics per server."""
    if server_slug:
        return _build_historical_server_summary_legacy_snapshot_payload(
            server_slug=server_slug,
        )

    if get_historical_data_source_kind() == "rcon":
        data_source = get_rcon_historical_read_model()
        if data_source is not None:
            capabilities = data_source.describe_capabilities()
            try:
                items = data_source.list_server_summaries(server_key=server_slug)
            except Exception as error:  # noqa: BLE001 - explicit runtime fallback boundary
                items = []
                rcon_source_policy = build_historical_runtime_source_policy(
                    operation="historical-server-summary",
                    rcon_status="error",
                    fallback_reason="rcon-historical-read-model-request-failed",
                    rcon_message=str(error),
                )
            else:
                rcon_source_policy = build_historical_runtime_source_policy(
                    operation="historical-server-summary",
                    rcon_status=(
                        "success"
                        if data_source.has_server_summary_coverage(items)
                        else "empty"
                    ),
                    fallback_reason="rcon-historical-read-model-has-no-summary-coverage",
                )

            if not bool(rcon_source_policy.get("fallback_used")):
                return {
                    "status": "ok",
                    "data": {
                        "title": (
                            "Cobertura historica minima por RCON"
                            if server_slug != ALL_SERVERS_SLUG
                            else "Cobertura historica minima RCON agregada"
                        ),
                        "context": "historical-server-summary",
                        "source": "rcon-historical-competitive-read-model",
                        "historical_data_source": "rcon",
                        "summary_basis": "rcon-competitive-windows",
                        "server_slug": server_slug,
                        "supported": True,
                        **rcon_source_policy,
                        "items": items,
                        "capabilities": capabilities,
                    },
                }
    items = list_historical_server_summaries(server_slug=server_slug)
    return {
        "status": "ok",
        "data": {
            "title": (
                "Cobertura historica agregada de todos los servidores"
                if server_slug == ALL_SERVERS_SLUG
                else "Cobertura historica importada por servidor"
            ),
            "context": "historical-server-summary",
            "source": "historical-crcon-storage",
            "summary_basis": "persisted-import",
            "weekly_ranking_window_days": 7,
            "server_slug": server_slug,
            **(
                rcon_source_policy
                if get_historical_data_source_kind() == "rcon"
                and "rcon_source_policy" in locals()
                else _resolve_historical_fallback_policy(
                    fallback_reason="rcon-historical-read-model-has-no-summary-coverage",
                )
            ),
            "items": items,
        },
    }


def _build_historical_server_summary_legacy_snapshot_payload(
    *,
    server_slug: str,
) -> dict[str, object]:
    snapshot_payload = build_historical_server_summary_snapshot_payload(
        server_slug=server_slug,
    )
    data = dict(snapshot_payload.get("data") or {})
    item = data.get("item") if isinstance(data.get("item"), dict) else None
    data.update(
        {
            "title": (
                "Cobertura historica agregada de todos los servidores"
                if server_slug == ALL_SERVERS_SLUG
                else "Cobertura historica importada por servidor"
            ),
            "context": "historical-server-summary",
            "source": "historical-precomputed-snapshots",
            "summary_basis": "precomputed-server-summary-snapshot",
            "weekly_ranking_window_days": 7,
            "legacy_endpoint_policy": "snapshot-read-only-fast-path",
            "items": [item] if item is not None else [],
        }
    )
    return {"status": snapshot_payload.get("status", "ok"), "data": data}


def _merge_recent_match_items(
    *,
    primary_items: list[dict[str, object]],
    fallback_items: list[dict[str, object]],
    limit: int,
) -> list[dict[str, object]]:
    merged: list[dict[str, object]] = []
    seen_keys: set[str] = set()
    for item in list(primary_items) + list(fallback_items):
        if not isinstance(item, dict):
            continue
        dedupe_key = _build_recent_match_dedupe_key(item)
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)
        merged.append(item)
    merged.sort(key=_recent_match_sort_key, reverse=True)
    return merged[:limit]


def _with_recent_result_source(
    item: dict[str, object],
    result_source: str,
) -> dict[str, object]:
    enriched = dict(item)
    enriched.setdefault("result_source", result_source)
    return enriched


def _recent_items_include_rcon_results(items: list[dict[str, object]]) -> bool:
    return any(
        item.get("result_source") in {"admin-log-match-ended", "rcon-session"}
        for item in items
        if isinstance(item, dict)
    )


def _build_recent_match_dedupe_key(item: dict[str, object]) -> str:
    server = item.get("server") if isinstance(item.get("server"), dict) else {}
    map_payload = item.get("map") if isinstance(item.get("map"), dict) else {}
    match_id = str(item.get("match_id") or "").strip()
    server_slug = str(server.get("slug") or server.get("external_server_id") or "").strip()
    map_name = str(map_payload.get("name") or map_payload.get("pretty_name") or "").strip().lower()
    closed_at = _truncate_recent_match_timestamp(
        item.get("closed_at") or item.get("ended_at")
    )
    started_at = _truncate_recent_match_timestamp(item.get("started_at"))
    if match_id and match_id.isdigit():
        return f"scoreboard:{server_slug}:{match_id}"
    return f"recent:{server_slug}:{map_name}:{started_at}:{closed_at}"


def _truncate_recent_match_timestamp(value: object) -> str:
    normalized = str(value or "").strip()
    return normalized[:16] if normalized else ""


def _recent_match_sort_key(item: dict[str, object]) -> tuple[str, str]:
    closed_at = str(item.get("closed_at") or item.get("ended_at") or "").strip()
    started_at = str(item.get("started_at") or "").strip()
    return (closed_at, started_at)
