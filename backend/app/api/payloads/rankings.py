"""Ranking, leaderboard and aggregate-summary public payloads."""

from __future__ import annotations

from ...config import get_historical_aggregate_source, get_historical_data_source_kind
from ...data_sources import SOURCE_KIND_RCON, build_source_attempt, build_source_policy
from ...historical_snapshots import (
    DEFAULT_MONTHLY_SNAPSHOT_WINDOW,
    DEFAULT_SNAPSHOT_WINDOW,
    DEFAULT_WEEKLY_SNAPSHOT_WINDOW,
    SNAPSHOT_TYPE_MONTHLY_LEADERBOARD,
    SNAPSHOT_TYPE_SERVER_SUMMARY,
    SNAPSHOT_TYPE_WEEKLY_LEADERBOARD,
)
from ...historical_storage import (
    ALL_SERVERS_SLUG,
    list_monthly_leaderboard,
    list_weekly_leaderboard,
    list_weekly_top_kills,
)
from ...rcon_annual_rankings import get_annual_ranking_snapshot
from ...rcon_historical_leaderboards import (
    get_latest_ranking_snapshot,
    is_ranking_runtime_fallback_enabled,
    list_rcon_materialized_leaderboard,
)
from ...services.historical_aggregates import get_historical_aggregate_service
from ..serializers import (
    coerce_public_metric_value as _coerce_public_metric_value,
    normalize_global_ranking_items as _normalize_global_ranking_items,
    normalize_public_server_id as _normalize_public_server_id,
    serialize_public_server_id as _serialize_public_server_id,
    utc_timestamp_now as _utc_timestamp_now,
)
from .common import (
    _build_historical_snapshot_metadata,
    _get_historical_snapshot_record,
    _resolve_historical_fallback_policy,
)

def build_weekly_top_kills_payload(
    *,
    limit: int = 10,
    server_id: str | None = None,
) -> dict[str, object]:
    """Return weekly top kills grouped by real community server."""
    result = list_weekly_top_kills(limit=limit, server_id=server_id)
    return {
        "status": "ok",
        "data": {
            "title": "Top kills semanales por servidor",
            "context": "historical-top-kills",
            "metric": "kills",
            "summary_basis": "closed-matches-last-7-days",
            "window_days": 7,
            "window_start": result["window_start"],
            "window_end": result["window_end"],
            "limit": limit,
            **_resolve_historical_fallback_policy(
                fallback_reason="rcon-historical-read-model-does-not-support-weekly-top-kills",
            ),
            "items": result["items"],
        },
    }


def build_historical_leaderboard_payload(
    *,
    limit: int = 10,
    server_id: str | None = None,
    metric: str = "kills",
    timeframe: str = "weekly",
) -> dict[str, object]:
    """Return one historical leaderboard for the requested timeframe and metric."""
    normalized_timeframe = timeframe.strip().lower() if isinstance(timeframe, str) else "weekly"
    if normalized_timeframe == "monthly":
        result = list_monthly_leaderboard(limit=limit, server_id=server_id, metric=metric)
        summary_basis = "closed-matches-calendar-month"
        context = "historical-monthly-leaderboard"
    else:
        normalized_timeframe = "weekly"
        result = list_weekly_leaderboard(limit=limit, server_id=server_id, metric=metric)
        summary_basis = "closed-matches-calendar-week"
        context = "historical-weekly-leaderboard"

    is_all_servers = server_id == ALL_SERVERS_SLUG
    return {
        "status": "ok",
        "data": {
            "title": _build_leaderboard_title(
                metric=metric,
                timeframe=normalized_timeframe,
                is_all_servers=is_all_servers,
            ),
            "context": context,
            "timeframe": normalized_timeframe,
            "metric": metric,
            "summary_basis": summary_basis,
            "window_days": result.get("window_days", 7),
            "window_start": result["window_start"],
            "window_end": result["window_end"],
            "window_kind": result.get("window_kind"),
            "window_label": result.get("window_label"),
            "uses_fallback": bool(result.get("uses_fallback")),
            "selection_reason": result.get("selection_reason"),
            "current_week_start": result.get("current_week_start"),
            "current_week_closed_matches": result.get("current_week_closed_matches"),
            "previous_week_closed_matches": result.get("previous_week_closed_matches"),
            "current_month_start": result.get("current_month_start"),
            "current_month_closed_matches": result.get("current_month_closed_matches"),
            "previous_month_closed_matches": result.get("previous_month_closed_matches"),
            "sufficient_sample": result.get("sufficient_sample"),
            "limit": limit,
            **_resolve_historical_fallback_policy(
                fallback_reason="rcon-historical-read-model-does-not-support-competitive-leaderboards",
            ),
            "items": result["items"],
        },
    }


def build_annual_ranking_snapshot_payload(
    *,
    year: int,
    server_id: str | None = None,
    metric: str = "kills",
    limit: int = 20,
) -> dict[str, object]:
    """Return an annual ranking payload from precomputed snapshots."""
    if get_historical_aggregate_source() == "crcon":
        result = get_historical_aggregate_service().ranking(
            server_id=server_id,
            timeframe="annual",
            metric=metric,
            limit=limit,
            year=year,
        )
        return {"status": "ok", "data": {"year": year, **result}}

    result = get_annual_ranking_snapshot(
        year=year,
        server_key=server_id,
        metric=metric,
        limit=limit,
    )
    items = result.get("items") or []
    return {
        "status": "ok",
        "data": {
            "year": result.get("year"),
            "server_id": result.get("server_id"),
            "metric": result.get("metric"),
            "limit": result.get("limit"),
            "requested_limit": result.get("requested_limit"),
            "effective_limit": result.get("effective_limit"),
            "snapshot_limit": result.get("snapshot_limit"),
            "item_count": result.get("item_count"),
            "source": result.get("source"),
            "snapshot_status": result.get("snapshot_status"),
            "generated_at": result.get("generated_at"),
            "window_start": result.get("window_start"),
            "window_end": result.get("window_end"),
            "source_matches_count": int(result.get("source_matches_count") or 0),
            "items": [
                {
                    "ranking_position": int(item.get("ranking_position") or 0),
                    "player_id": item.get("player_id"),
                    "player_name": item.get("player_name"),
                    "metric_value": _coerce_public_metric_value(item.get("metric_value")),
                    "matches_considered": int(item.get("matches_considered") or 0),
                    "kills": int(item.get("kills") or 0),
                    "deaths": int(item.get("deaths") or 0),
                    "teamkills": int(item.get("teamkills") or 0),
                    "kd_ratio": float(item.get("kd_ratio") or 0.0),
                    "kills_per_match": (
                        float(item.get("kills_per_match"))
                        if item.get("kills_per_match") is not None
                        else (
                            round(
                                int(item.get("kills") or 0)
                                / int(item.get("matches_considered") or 0),
                                2,
                            )
                            if int(item.get("matches_considered") or 0) > 0
                            else 0.0
                        )
                    ),
                }
                for item in items
                if isinstance(item, dict)
            ],
        },
    }


def build_global_ranking_payload(
    *,
    timeframe: str = "weekly",
    server_id: str | None = None,
    metric: str = "kills",
    limit: int = 20,
    year: int | None = None,
) -> dict[str, object]:
    """Return the dedicated Ranking page payload without changing Stats contracts."""
    normalized_timeframe = str(timeframe or "weekly").strip().lower()
    normalized_server_id = _normalize_public_server_id(server_id)

    if get_historical_aggregate_source() == "crcon":
        result = get_historical_aggregate_service().ranking(
            server_id=normalized_server_id,
            timeframe=normalized_timeframe,
            metric=metric,
            limit=limit,
            year=year,
        )
        generated_at = result.get("generated_at")
        aggregate_state = result.get("aggregate_state")
        data = {
            **result,
            "page_kind": "global-ranking",
            "title": "Ranking global anual" if normalized_timeframe == "annual" else "Ranking global",
            "context": f"global-ranking-{normalized_timeframe}",
            "timeframe": normalized_timeframe,
            "server_id": result.get("server_id") or normalized_server_id,
            "metric": metric,
            "limit": limit,
            "year": year,
            "freshness": "live-query" if aggregate_state == "AVAILABLE" else "unavailable",
            "fallback_used": False,
            "source": {
                "primary_source": "crcon-postgres",
                "read_model": "crcon-read-only-aggregate",
                "generated_at": generated_at,
                "freshness": "live-query" if aggregate_state == "AVAILABLE" else "unavailable",
                "aggregate_state": aggregate_state,
            },
        }
        return {"status": "ok", "data": data}

    if normalized_timeframe == "annual":
        if year is None:
            raise ValueError("year is required when timeframe=annual")
        result = get_annual_ranking_snapshot(
            year=year,
            server_key=normalized_server_id,
            metric=metric,
            limit=limit,
        )
        return {
            "status": "ok",
            "data": {
                "page_kind": "global-ranking",
                "title": "Ranking global anual",
                "context": "global-ranking-annual",
                "timeframe": "annual",
                "server_id": _serialize_public_server_id(result.get("server_id")),
                "metric": result.get("metric"),
                "limit": int(result.get("limit") or 0),
                "requested_limit": int(result.get("requested_limit") or 0),
                "effective_limit": int(result.get("effective_limit") or 0),
                "year": int(result.get("year") or year),
                "window_start": result.get("window_start"),
                "window_end": result.get("window_end"),
                "window_kind": "annual-snapshot",
                "window_label": "Anual",
                "snapshot_status": result.get("snapshot_status"),
                "generated_at": result.get("generated_at"),
                "freshness": (
                    "snapshot" if result.get("snapshot_status") == "ready" else "missing"
                ),
                "fallback_used": False,
                "snapshot_limit": result.get("snapshot_limit"),
                "item_count": int(result.get("item_count") or 0),
                "source_matches_count": int(result.get("source_matches_count") or 0),
                "source": {
                    "primary_source": "rcon",
                    "read_model": "rcon-annual-ranking-snapshot",
                    "generated_at": result.get("generated_at"),
                    "freshness": (
                        "snapshot" if result.get("snapshot_status") == "ready" else "missing"
                    ),
                },
                "items": _normalize_global_ranking_items(result.get("items")),
            },
        }

    snapshot_result = get_latest_ranking_snapshot(
        server_key=normalized_server_id,
        timeframe=normalized_timeframe,
        metric=metric,
        limit=limit,
    )
    if snapshot_result.get("snapshot_status") == "ready":
        return {
            "status": "ok",
            "data": {
                "page_kind": "global-ranking",
                "title": "Ranking global",
                "context": f"global-ranking-{normalized_timeframe}",
                "timeframe": normalized_timeframe,
                "server_id": _serialize_public_server_id(snapshot_result.get("server_id")),
                "metric": snapshot_result.get("metric"),
                "limit": int(snapshot_result.get("limit") or 0),
                "requested_limit": int(snapshot_result.get("requested_limit") or limit),
                "effective_limit": int(snapshot_result.get("effective_limit") or 0),
                "window_start": snapshot_result.get("window_start"),
                "window_end": snapshot_result.get("window_end"),
                "window_kind": snapshot_result.get("window_kind"),
                "window_label": snapshot_result.get("window_label"),
                "snapshot_status": "ready",
                "generated_at": snapshot_result.get("generated_at"),
                "freshness": snapshot_result.get("freshness") or "fresh",
                "fallback_used": False,
                "source_matches_count": int(snapshot_result.get("source_matches_count") or 0),
                "source": {
                    "primary_source": "rcon",
                    "read_model": "ranking-snapshot",
                    "snapshot_source": snapshot_result.get("source"),
                    "generated_at": snapshot_result.get("generated_at"),
                    "freshness": snapshot_result.get("freshness") or "fresh",
                },
                "items": _normalize_global_ranking_items(snapshot_result.get("items")),
            },
        }

    runtime_fallback_enabled = is_ranking_runtime_fallback_enabled()
    if not runtime_fallback_enabled:
        return {
            "status": "ok",
            "data": {
                "page_kind": "global-ranking",
                "title": "Ranking global",
                "context": f"global-ranking-{normalized_timeframe}",
                "timeframe": normalized_timeframe,
                "server_id": _serialize_public_server_id(snapshot_result.get("server_id")),
                "metric": snapshot_result.get("metric"),
                "limit": int(snapshot_result.get("limit") or limit),
                "requested_limit": int(snapshot_result.get("requested_limit") or limit),
                "effective_limit": int(snapshot_result.get("effective_limit") or 0),
                "window_start": snapshot_result.get("window_start"),
                "window_end": snapshot_result.get("window_end"),
                "window_kind": snapshot_result.get("window_kind"),
                "window_label": snapshot_result.get("window_label"),
                "snapshot_status": "missing",
                "generated_at": None,
                "freshness": "missing",
                "fallback_used": False,
                "source_matches_count": 0,
                "source": {
                    "primary_source": "rcon",
                    "read_model": "ranking-snapshot",
                    "snapshot_source": snapshot_result.get("source"),
                    "generated_at": None,
                    "freshness": "missing",
                },
                "items": [],
            },
        }

    result = list_rcon_materialized_leaderboard(
        server_key=normalized_server_id,
        timeframe=normalized_timeframe,
        metric=metric,
        limit=limit,
    )
    return {
        "status": "ok",
        "data": {
            "page_kind": "global-ranking",
            "title": "Ranking global",
            "context": f"global-ranking-{normalized_timeframe}",
            "timeframe": normalized_timeframe,
            "server_id": _serialize_public_server_id(result.get("server_key")),
            "metric": result.get("metric"),
            "limit": int(result.get("limit") or limit),
            "requested_limit": int(limit),
            "effective_limit": int(result.get("limit") or limit),
            "window_start": result.get("window_start"),
            "window_end": result.get("window_end"),
            "window_kind": result.get("window_kind"),
            "window_label": result.get("window_label"),
            "selection_reason": result.get("selection_reason"),
            "snapshot_status": "missing",
            "generated_at": None,
            "freshness": "runtime",
            "fallback_used": True,
            "source": {
                "primary_source": "rcon",
                "read_model": "rcon-materialized-admin-log-leaderboard",
                "snapshot_source": "ranking-snapshot",
                "generated_at": _utc_timestamp_now(),
                "freshness": "runtime",
            },
            "items": _normalize_global_ranking_items(result.get("items")),
        },
    }


def build_weekly_leaderboard_payload(
    *,
    limit: int = 10,
    server_id: str | None = None,
    metric: str = "kills",
) -> dict[str, object]:
    """Return one weekly historical leaderboard for the requested metric."""
    return build_historical_leaderboard_payload(
        limit=limit,
        server_id=server_id,
        metric=metric,
        timeframe="weekly",
    )


def build_monthly_leaderboard_payload(
    *,
    limit: int = 10,
    server_id: str | None = None,
    metric: str = "kills",
) -> dict[str, object]:
    """Return one monthly historical leaderboard for the requested metric."""
    return build_historical_leaderboard_payload(
        limit=limit,
        server_id=server_id,
        metric=metric,
        timeframe="monthly",
    )


def build_historical_server_summary_snapshot_payload(
    *,
    server_slug: str | None = None,
) -> dict[str, object]:
    """Return one precomputed summary snapshot without recalculating aggregates."""
    if get_historical_aggregate_source() == "crcon":
        result = get_historical_aggregate_service().server_summary(
            server_id=server_slug
        )
        return {
            "status": "ok",
            "data": {
                "title": "Resumen histórico CRCON por servidor",
                "context": "historical-server-summary-crcon",
                **result,
            },
        }
    snapshot = _get_historical_snapshot_record(
        server_key=server_slug,
        snapshot_type=SNAPSHOT_TYPE_SERVER_SUMMARY,
        window=DEFAULT_SNAPSHOT_WINDOW,
    )
    payload = snapshot.get("payload") if snapshot else {}
    item = payload.get("item") if isinstance(payload, dict) else None
    return {
        "status": "ok",
        "data": {
            "title": "Snapshot historico de resumen por servidor",
            "context": "historical-server-summary-snapshot",
            "source": "historical-precomputed-snapshots",
            "server_slug": server_slug,
            "found": snapshot is not None and isinstance(item, dict),
            **(
                build_source_policy(
                    primary_source=SOURCE_KIND_RCON,
                    selected_source=SOURCE_KIND_RCON,
                    source_attempts=[
                        build_source_attempt(
                            source=SOURCE_KIND_RCON,
                            role="primary",
                            status="success",
                            reason="server-summary-snapshot-served-by-rcon-competitive-model",
                        )
                    ],
                )
                if get_historical_data_source_kind() == SOURCE_KIND_RCON and isinstance(item, dict)
                else _resolve_historical_fallback_policy(
                    fallback_reason="rcon-historical-read-model-does-not-support-historical-snapshots-yet",
                )
            ),
            **_build_historical_snapshot_metadata(snapshot),
            "item": item if isinstance(item, dict) else None,
        },
    }


def build_leaderboard_snapshot_payload(
    *,
    limit: int = 10,
    server_id: str | None = None,
    metric: str = "kills",
    timeframe: str = "weekly",
) -> dict[str, object]:
    """Return one precomputed leaderboard snapshot for the requested timeframe."""
    normalized_timeframe = timeframe.strip().lower() if isinstance(timeframe, str) else "weekly"
    if get_historical_aggregate_source() == "crcon":
        result = get_historical_aggregate_service().ranking(
            server_id=server_id,
            timeframe=normalized_timeframe,
            metric=metric,
            limit=limit,
        )
        return {
            "status": "ok",
            "data": {
                "title": _build_leaderboard_title(
                    metric=metric,
                    timeframe=normalized_timeframe,
                    is_all_servers=server_id in {None, ALL_SERVERS_SLUG},
                    snapshot=False,
                ),
                "context": f"historical-{normalized_timeframe}-leaderboard-crcon",
                **result,
            },
        }
    if normalized_timeframe == "monthly":
        snapshot_type = SNAPSHOT_TYPE_MONTHLY_LEADERBOARD
        window = DEFAULT_MONTHLY_SNAPSHOT_WINDOW
        context = "historical-monthly-leaderboard-snapshot"
    else:
        normalized_timeframe = "weekly"
        snapshot_type = SNAPSHOT_TYPE_WEEKLY_LEADERBOARD
        window = DEFAULT_WEEKLY_SNAPSHOT_WINDOW
        context = "historical-weekly-leaderboard-snapshot"

    snapshot = _get_historical_snapshot_record(
        server_key=server_id,
        snapshot_type=snapshot_type,
        metric=metric,
        window=window,
    )
    payload = snapshot.get("payload") if snapshot else {}
    items = payload.get("items") if isinstance(payload, dict) else None
    sliced_items = list(items[:limit]) if isinstance(items, list) else []
    is_all_servers = server_id == ALL_SERVERS_SLUG
    return {
        "status": "ok",
        "data": {
            "title": _build_leaderboard_title(
                metric=metric,
                timeframe=normalized_timeframe,
                is_all_servers=is_all_servers,
                snapshot=True,
            ),
            "context": context,
            "source": "historical-precomputed-snapshots",
            "server_slug": server_id,
            "timeframe": normalized_timeframe,
            "metric": metric,
            "found": snapshot is not None,
            **_build_historical_snapshot_metadata(snapshot),
            "window_days": payload.get("window_days") if isinstance(payload, dict) else 7,
            "window_start": payload.get("window_start") if isinstance(payload, dict) else None,
            "window_end": payload.get("window_end") if isinstance(payload, dict) else None,
            "window_kind": payload.get("window_kind") if isinstance(payload, dict) else None,
            "window_label": payload.get("window_label") if isinstance(payload, dict) else None,
            "uses_fallback": bool(payload.get("uses_fallback")) if isinstance(payload, dict) else False,
            "selection_reason": payload.get("selection_reason") if isinstance(payload, dict) else None,
            "current_week_start": payload.get("current_week_start") if isinstance(payload, dict) else None,
            "current_week_closed_matches": (
                payload.get("current_week_closed_matches") if isinstance(payload, dict) else None
            ),
            "previous_week_closed_matches": (
                payload.get("previous_week_closed_matches") if isinstance(payload, dict) else None
            ),
            "current_month_start": payload.get("current_month_start") if isinstance(payload, dict) else None,
            "current_month_closed_matches": (
                payload.get("current_month_closed_matches") if isinstance(payload, dict) else None
            ),
            "previous_month_closed_matches": (
                payload.get("previous_month_closed_matches") if isinstance(payload, dict) else None
            ),
            "sufficient_sample": payload.get("sufficient_sample") if isinstance(payload, dict) else None,
            "snapshot_limit": payload.get("limit") if isinstance(payload, dict) else None,
            "limit": limit,
            "runtime_enrichment": {
                "applied": False,
                "reason": "disabled-on-public-snapshot-path",
            },
            **_resolve_historical_fallback_policy(
                fallback_reason="rcon-historical-read-model-does-not-support-historical-snapshots-yet",
            ),
            "items": sliced_items,
        },
    }


def build_weekly_leaderboard_snapshot_payload(
    *,
    limit: int = 10,
    server_id: str | None = None,
    metric: str = "kills",
) -> dict[str, object]:
    """Return one precomputed weekly leaderboard snapshot."""
    return build_leaderboard_snapshot_payload(
        limit=limit,
        server_id=server_id,
        metric=metric,
        timeframe="weekly",
    )


def build_monthly_leaderboard_snapshot_payload(
    *,
    limit: int = 10,
    server_id: str | None = None,
    metric: str = "kills",
) -> dict[str, object]:
    """Return one precomputed monthly leaderboard snapshot."""
    return build_leaderboard_snapshot_payload(
        limit=limit,
        server_id=server_id,
        metric=metric,
        timeframe="monthly",
    )


def _build_leaderboard_title(
    *,
    metric: str,
    timeframe: str,
    is_all_servers: bool,
    snapshot: bool = False,
) -> str:
    timeframe_label = "mensual" if timeframe == "monthly" else "semanal"
    scope_label = "totales" if is_all_servers else "por servidor"
    prefix = "Snapshot " if snapshot else ""
    title_by_metric = {
        "kills": f"{prefix}Top kills {timeframe_label} {scope_label}",
        "deaths": f"{prefix}Top muertes {timeframe_label} {scope_label}",
        "support": f"{prefix}Top puntos de soporte {timeframe_label} {scope_label}",
        "matches_over_100_kills": f"{prefix}Top partidas de 100+ kills {timeframe_label} {scope_label}",
    }
    fallback_label = f"{prefix}Ranking {timeframe_label} por servidor".strip()
    return title_by_metric.get(metric, fallback_label)
