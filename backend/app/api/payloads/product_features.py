"""Undecided MVP, player-event and Elo/MMR public compatibility payloads."""

from __future__ import annotations

from ...historical_snapshots import (
    DEFAULT_MONTHLY_SNAPSHOT_WINDOW,
    SNAPSHOT_TYPE_MONTHLY_MVP,
    SNAPSHOT_TYPE_MONTHLY_MVP_V2,
    SNAPSHOT_TYPE_PLAYER_EVENT_DEATH_BY,
    SNAPSHOT_TYPE_PLAYER_EVENT_DUELS,
    SNAPSHOT_TYPE_PLAYER_EVENT_MOST_KILLED,
    SNAPSHOT_TYPE_PLAYER_EVENT_TEAMKILLS,
    SNAPSHOT_TYPE_PLAYER_EVENT_WEAPON_KILLS,
)
from ...historical_storage import ALL_SERVERS_SLUG
from .common import (
    _build_historical_snapshot_metadata,
    _get_historical_snapshot_record,
    _resolve_historical_fallback_policy,
)

def build_monthly_mvp_payload(
    *,
    limit: int = 10,
    server_id: str | None = None,
) -> dict[str, object]:
    """Return the precomputed monthly MVP payload through the stable API surface."""
    snapshot_payload = build_monthly_mvp_snapshot_payload(
        limit=limit,
        server_id=server_id,
    )
    data = snapshot_payload["data"]
    return {
        "status": "ok",
        "data": {
            **data,
            "title": _build_monthly_mvp_title(
                is_all_servers=server_id == ALL_SERVERS_SLUG,
                snapshot=False,
            ),
            "context": "historical-monthly-mvp",
            "source": "historical-precomputed-snapshots",
            **_resolve_historical_fallback_policy(
                fallback_reason="rcon-historical-read-model-does-not-support-monthly-mvp-yet",
            ),
        },
    }


def build_player_event_payload(
    *,
    limit: int = 10,
    server_id: str | None = None,
    view: str = "most-killed",
) -> dict[str, object]:
    """Return one V2 player-event payload through the stable API surface."""
    snapshot_payload = build_player_event_snapshot_payload(
        limit=limit,
        server_id=server_id,
        view=view,
    )
    data = snapshot_payload["data"]
    return {
        "status": "ok",
        "data": {
            **data,
            "title": _build_player_event_title(
                view=view,
                is_all_servers=server_id == ALL_SERVERS_SLUG,
                snapshot=False,
            ),
            "context": "historical-player-events",
            "source": "historical-precomputed-player-event-snapshots",
            **_resolve_historical_fallback_policy(
                fallback_reason="rcon-historical-read-model-does-not-support-player-events-yet",
            ),
        },
    }


def build_monthly_mvp_v2_payload(
    *,
    limit: int = 10,
    server_id: str | None = None,
) -> dict[str, object]:
    """Return the precomputed monthly MVP V2 payload through the stable API surface."""
    snapshot_payload = build_monthly_mvp_v2_snapshot_payload(
        limit=limit,
        server_id=server_id,
    )
    data = snapshot_payload["data"]
    return {
        "status": "ok",
        "data": {
            **data,
            "title": _build_monthly_mvp_v2_title(
                is_all_servers=server_id == ALL_SERVERS_SLUG,
                snapshot=False,
            ),
            "context": "historical-monthly-mvp-v2",
            "source": "historical-precomputed-snapshots",
            **_resolve_historical_fallback_policy(
                fallback_reason="rcon-historical-read-model-does-not-support-monthly-mvp-v2-yet",
            ),
        },
    }


def build_monthly_mvp_snapshot_payload(
    *,
    limit: int = 10,
    server_id: str | None = None,
) -> dict[str, object]:
    """Return one precomputed monthly MVP snapshot."""
    snapshot = _get_historical_snapshot_record(
        server_key=server_id,
        snapshot_type=SNAPSHOT_TYPE_MONTHLY_MVP,
        window=DEFAULT_MONTHLY_SNAPSHOT_WINDOW,
    )
    payload = snapshot.get("payload") if snapshot else {}
    items = payload.get("items") if isinstance(payload, dict) else None
    sliced_items = list(items[:limit]) if isinstance(items, list) else []
    return {
        "status": "ok",
        "data": {
            "title": _build_monthly_mvp_title(
                is_all_servers=server_id == ALL_SERVERS_SLUG,
                snapshot=True,
            ),
            "context": "historical-monthly-mvp-snapshot",
            "source": "historical-precomputed-snapshots",
            "server_slug": server_id,
            "timeframe": "monthly",
            "metric": "mvp",
            "found": snapshot is not None,
            **_build_historical_snapshot_metadata(snapshot),
            "month_key": payload.get("month_key") if isinstance(payload, dict) else None,
            "window_days": payload.get("window_days") if isinstance(payload, dict) else None,
            "window_start": payload.get("window_start") if isinstance(payload, dict) else None,
            "window_end": payload.get("window_end") if isinstance(payload, dict) else None,
            "window_kind": payload.get("window_kind") if isinstance(payload, dict) else None,
            "window_label": payload.get("window_label") if isinstance(payload, dict) else None,
            "uses_fallback": bool(payload.get("uses_fallback")) if isinstance(payload, dict) else False,
            "selection_reason": payload.get("selection_reason") if isinstance(payload, dict) else None,
            "current_month_start": payload.get("current_month_start") if isinstance(payload, dict) else None,
            "current_month_closed_matches": (
                payload.get("current_month_closed_matches") if isinstance(payload, dict) else None
            ),
            "previous_month_closed_matches": (
                payload.get("previous_month_closed_matches") if isinstance(payload, dict) else None
            ),
            "sufficient_sample": payload.get("sufficient_sample") if isinstance(payload, dict) else None,
            "eligibility": payload.get("eligibility") if isinstance(payload, dict) else None,
            "ranking_version": payload.get("ranking_version") if isinstance(payload, dict) else None,
            "eligible_players_count": (
                payload.get("eligible_players_count") if isinstance(payload, dict) else 0
            ),
            "snapshot_limit": payload.get("limit") if isinstance(payload, dict) else None,
            "limit": limit,
            **_resolve_historical_fallback_policy(
                fallback_reason="rcon-historical-read-model-does-not-support-historical-snapshots-yet",
            ),
            "items": sliced_items,
        },
    }


def build_monthly_mvp_v2_snapshot_payload(
    *,
    limit: int = 10,
    server_id: str | None = None,
) -> dict[str, object]:
    """Return one precomputed monthly MVP V2 snapshot."""
    snapshot = _get_historical_snapshot_record(
        server_key=server_id,
        snapshot_type=SNAPSHOT_TYPE_MONTHLY_MVP_V2,
        window=DEFAULT_MONTHLY_SNAPSHOT_WINDOW,
    )
    payload = snapshot.get("payload") if snapshot else {}
    items = payload.get("items") if isinstance(payload, dict) else None
    sliced_items = list(items[:limit]) if isinstance(items, list) else []
    found = bool(payload.get("found")) if isinstance(payload, dict) else False
    return {
        "status": "ok",
        "data": {
            "title": _build_monthly_mvp_v2_title(
                is_all_servers=server_id == ALL_SERVERS_SLUG,
                snapshot=True,
            ),
            "context": "historical-monthly-mvp-v2-snapshot",
            "source": "historical-precomputed-snapshots",
            "server_slug": server_id,
            "timeframe": "monthly",
            "metric": "mvp-v2",
            "found": snapshot is not None and found,
            **_build_historical_snapshot_metadata(snapshot),
            "month_key": payload.get("month_key") if isinstance(payload, dict) else None,
            "window_days": payload.get("window_days") if isinstance(payload, dict) else None,
            "window_start": payload.get("window_start") if isinstance(payload, dict) else None,
            "window_end": payload.get("window_end") if isinstance(payload, dict) else None,
            "window_kind": payload.get("window_kind") if isinstance(payload, dict) else None,
            "window_label": payload.get("window_label") if isinstance(payload, dict) else None,
            "uses_fallback": bool(payload.get("uses_fallback")) if isinstance(payload, dict) else False,
            "selection_reason": payload.get("selection_reason") if isinstance(payload, dict) else None,
            "current_month_start": payload.get("current_month_start") if isinstance(payload, dict) else None,
            "current_month_closed_matches": (
                payload.get("current_month_closed_matches") if isinstance(payload, dict) else None
            ),
            "previous_month_closed_matches": (
                payload.get("previous_month_closed_matches") if isinstance(payload, dict) else None
            ),
            "sufficient_sample": payload.get("sufficient_sample") if isinstance(payload, dict) else None,
            "eligibility": payload.get("eligibility") if isinstance(payload, dict) else None,
            "ranking_version": payload.get("ranking_version") if isinstance(payload, dict) else None,
            "event_coverage": payload.get("event_coverage") if isinstance(payload, dict) else None,
            "eligible_players_count": (
                payload.get("eligible_players_count") if isinstance(payload, dict) else 0
            ),
            "snapshot_limit": payload.get("limit") if isinstance(payload, dict) else None,
            "limit": limit,
            **_resolve_historical_fallback_policy(
                fallback_reason="rcon-historical-read-model-does-not-support-historical-snapshots-yet",
            ),
            "items": sliced_items,
        },
    }


def build_player_event_snapshot_payload(
    *,
    limit: int = 10,
    server_id: str | None = None,
    view: str = "most-killed",
) -> dict[str, object]:
    """Return one precomputed V2 player-event snapshot."""
    snapshot_type = _resolve_player_event_snapshot_type(view)
    snapshot = _get_historical_snapshot_record(
        server_key=server_id,
        snapshot_type=snapshot_type,
        window=DEFAULT_MONTHLY_SNAPSHOT_WINDOW,
    )
    payload = snapshot.get("payload") if snapshot else {}
    items = payload.get("items") if isinstance(payload, dict) else None
    sliced_items = list(items[:limit]) if isinstance(items, list) else []
    found = bool(payload.get("found")) if isinstance(payload, dict) else False
    return {
        "status": "ok",
        "data": {
            "title": _build_player_event_title(
                view=view,
                is_all_servers=server_id == ALL_SERVERS_SLUG,
                snapshot=True,
            ),
            "context": "historical-player-events-snapshot",
            "source": "historical-precomputed-player-event-snapshots",
            "server_slug": server_id,
            "timeframe": "monthly",
            "metric": view,
            "found": snapshot is not None and found,
            **_build_historical_snapshot_metadata(snapshot),
            "period": payload.get("period") if isinstance(payload, dict) else "monthly",
            "month_key": payload.get("month_key") if isinstance(payload, dict) else None,
            "snapshot_limit": payload.get("limit") if isinstance(payload, dict) else None,
            "limit": limit,
            **_resolve_historical_fallback_policy(
                fallback_reason="rcon-historical-read-model-does-not-support-historical-snapshots-yet",
            ),
            "items": sliced_items,
        },
    }


def build_elo_mmr_leaderboard_payload(
    *,
    limit: int = 10,
    server_id: str | None = None,
) -> dict[str, object]:
    """Return the current Elo/MMR monthly leaderboard."""
    engine = _load_elo_mmr_engine()
    if engine is None:
        return _build_elo_mmr_unavailable_payload(
            context="historical-elo-mmr-leaderboard",
            title=(
                "Leaderboard mensual Elo/MMR global"
                if server_id == ALL_SERVERS_SLUG
                else "Leaderboard mensual Elo/MMR por servidor"
            ),
            server_id=server_id,
            limit=limit,
            extra={"items": []},
            operation="elo-mmr-leaderboard",
        )

    list_elo_mmr_leaderboard_payload = engine[1]
    payload = list_elo_mmr_leaderboard_payload(server_id=server_id, limit=limit)
    is_all_servers = server_id == ALL_SERVERS_SLUG
    accuracy_contract = _build_elo_accuracy_contract(payload.get("capabilities_summary"))
    return {
        "status": "ok",
        "data": {
            "title": (
                "Leaderboard mensual Elo/MMR global"
                if is_all_servers
                else "Leaderboard mensual Elo/MMR por servidor"
            ),
            "context": "historical-elo-mmr-leaderboard",
            "source": "elo-mmr-persisted-read-model",
            "server_slug": server_id,
            "month_key": payload.get("month_key"),
            "found": bool(payload.get("found")),
            "generated_at": payload.get("generated_at"),
            "limit": limit,
            **(payload.get("source_policy") or _resolve_historical_fallback_policy(
                operation="elo-mmr-leaderboard",
                fallback_reason="elo-mmr-source-policy-missing",
            )),
            "capabilities_summary": payload.get("capabilities_summary"),
            "accuracy_contract": accuracy_contract,
            "model_contract": _build_elo_model_contract(accuracy_contract),
            "items": [
                _enrich_elo_leaderboard_item(item, accuracy_contract=accuracy_contract)
                for item in (payload.get("items") or [])
                if isinstance(item, dict)
            ],
        },
    }


def build_elo_mmr_player_payload(
    *,
    player_id: str,
    server_id: str | None = None,
) -> dict[str, object]:
    """Return one Elo/MMR player profile."""
    engine = _load_elo_mmr_engine()
    if engine is None:
        return _build_elo_mmr_unavailable_payload(
            context="historical-elo-mmr-player",
            title="Perfil Elo/MMR de jugador",
            server_id=server_id,
            extra={
                "player_id": player_id,
                "found": False,
                "profile": None,
            },
            operation="elo-mmr-player",
        )

    get_elo_mmr_player_payload, list_elo_mmr_leaderboard_payload = engine
    profile = get_elo_mmr_player_payload(player_id=player_id, server_id=server_id)
    source_policy = list_elo_mmr_leaderboard_payload(server_id=server_id, limit=1).get("source_policy")
    accuracy_contract = _build_elo_player_accuracy_contract(profile)
    return {
        "status": "ok",
        "data": {
            "title": "Perfil Elo/MMR de jugador",
            "context": "historical-elo-mmr-player",
            "source": "elo-mmr-persisted-read-model",
            "player_id": player_id,
            "server_slug": server_id,
            "found": profile is not None,
            **(source_policy or _resolve_historical_fallback_policy(
                operation="elo-mmr-player",
                fallback_reason="elo-mmr-player-source-policy-missing",
            )),
            "accuracy_contract": accuracy_contract,
            "model_contract": _build_elo_model_contract(accuracy_contract),
            "profile": _enrich_elo_profile(profile, accuracy_contract=accuracy_contract),
        },
    }


def _load_elo_mmr_engine():
    try:
        from ...elo_mmr_engine import (  # noqa: PLC0415 - lazy boundary for paused Elo/MMR
            get_elo_mmr_player_payload,
            list_elo_mmr_leaderboard_payload,
        )
    except ImportError:
        return None
    return get_elo_mmr_player_payload, list_elo_mmr_leaderboard_payload


def _build_elo_mmr_unavailable_payload(
    *,
    context: str,
    title: str,
    server_id: str | None,
    operation: str,
    limit: int | None = None,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    accuracy_contract = _build_elo_accuracy_contract(None)
    data = {
        "title": title,
        "context": context,
        "source": "elo-mmr-paused",
        "server_slug": server_id,
        "available": False,
        "unavailable_reason": "elo-mmr-engine-import-unavailable",
        **_resolve_historical_fallback_policy(
            operation=operation,
            fallback_reason="elo-mmr-operationally-paused",
        ),
        "capabilities_summary": None,
        "accuracy_contract": accuracy_contract,
        "model_contract": _build_elo_model_contract(accuracy_contract),
    }
    if limit is not None:
        data["limit"] = limit
    if extra:
        data.update(extra)
    return {
        "status": "ok",
        "data": data,
    }


def _build_elo_player_accuracy_contract(profile: dict[str, object] | None) -> dict[str, object]:
    if not isinstance(profile, dict):
        return _build_elo_accuracy_contract(None)
    monthly_ranking = profile.get("monthly_ranking")
    if isinstance(monthly_ranking, dict) and isinstance(monthly_ranking.get("capabilities"), dict):
        return _build_elo_accuracy_contract(monthly_ranking.get("capabilities"))
    persistent_rating = profile.get("persistent_rating")
    if isinstance(persistent_rating, dict) and isinstance(persistent_rating.get("capabilities"), dict):
        return _build_elo_accuracy_contract(persistent_rating.get("capabilities"))
    return _build_elo_accuracy_contract(None)


def _build_elo_accuracy_contract(summary: dict[str, object] | None) -> dict[str, object]:
    capabilities = summary if isinstance(summary, dict) else {}
    signals = capabilities.get("signals")
    normalized_signals = [signal for signal in signals if isinstance(signal, dict)] if isinstance(signals, list) else []
    component_status = {
        str(signal.get("name") or "").strip(): signal.get("status")
        for signal in normalized_signals
        if str(signal.get("name") or "").strip()
    }
    return {
        "accuracy_mode": capabilities.get("accuracy_mode") or "unknown",
        "exact_ratio": capabilities.get("exact_ratio"),
        "approximate_ratio": capabilities.get("approximate_ratio"),
        "not_available_ratio": capabilities.get("unavailable_ratio"),
        "component_status": component_status,
        "blocked_components": [
            name for name, status in component_status.items() if status == "not_available"
        ],
        "explanation": {
            "exact": "computed from persisted repository signals without proxy substitution",
            "approximate": "computed with explicit proxies because the ideal telemetry is not stored yet",
            "not_available": "not computable yet with the current repository telemetry",
        },
    }


def _build_elo_model_contract(accuracy_contract: dict[str, object]) -> dict[str, object]:
    blocked_components = accuracy_contract.get("blocked_components")
    return {
        "persistent_rating": {
            "meaning": "long-lived competitive rating rebuilt from persisted matches for the selected scope",
            "primary_field": "persistent_rating.mmr",
        },
        "monthly_rank_score": {
            "meaning": "monthly leaderboard ordering score that combines rating movement, match quality, activity and confidence",
            "primary_field": "monthly_rank_score",
        },
        "elo_core": {
            "meaning": "competitive rating movement driven by expected-vs-actual outcome against opponent rating pressure",
            "fields": ["components.elo_core_gain"],
        },
        "performance_modifiers": {
            "meaning": "bounded HLL-specific adjustments layered on top of the competitive Elo core",
            "fields": [
                "components.performance_modifier_gain",
                "components.proxy_modifier_gain",
            ],
        },
        "proxy_boundary": {
            "meaning": "subset of modifier logic that still depends on approximate signals such as role, objective, schedule or discipline proxies",
            "blocked_by_telemetry": blocked_components if isinstance(blocked_components, list) else [],
        },
    }


def _enrich_elo_leaderboard_item(
    item: dict[str, object],
    *,
    accuracy_contract: dict[str, object],
) -> dict[str, object]:
    enriched = dict(item)
    components = item.get("components") if isinstance(item.get("components"), dict) else {}
    persistent_rating = item.get("persistent_rating") if isinstance(item.get("persistent_rating"), dict) else {}
    delta_breakdown = _resolve_elo_delta_sources(
        components,
        persistent_rating=persistent_rating,
    )
    enriched["rating_breakdown"] = {
        "persistent_rating": {
            "mmr": persistent_rating.get("mmr"),
            "baseline_mmr": persistent_rating.get("baseline_mmr"),
            "net_mmr_gain": persistent_rating.get("mmr_gain"),
        },
        "monthly_ranking": {
            "score": item.get("monthly_rank_score"),
            "valid_matches": item.get("valid_matches"),
            "confidence": components.get("confidence"),
        },
        "delta_sources": delta_breakdown["values"],
        "materialization": delta_breakdown["materialization"],
        "telemetry_boundary": {
            "approximate_ratio": accuracy_contract.get("approximate_ratio"),
            "blocked_components": accuracy_contract.get("blocked_components") or [],
        },
    }
    return enriched


def _enrich_elo_profile(
    profile: dict[str, object] | None,
    *,
    accuracy_contract: dict[str, object],
) -> dict[str, object] | None:
    if not isinstance(profile, dict):
        return profile
    enriched = dict(profile)
    monthly_ranking = dict(profile.get("monthly_ranking")) if isinstance(profile.get("monthly_ranking"), dict) else None
    if monthly_ranking is not None:
        components = monthly_ranking.get("components") if isinstance(monthly_ranking.get("components"), dict) else {}
        delta_breakdown = _resolve_elo_delta_sources(
            components,
            persistent_rating={
                "mmr_gain": monthly_ranking.get("mmr_gain"),
                "baseline_mmr": monthly_ranking.get("baseline_mmr"),
                "mmr": monthly_ranking.get("current_mmr"),
            },
        )
        monthly_ranking["rating_breakdown"] = {
            "monthly_rank_score": monthly_ranking.get("monthly_rank_score"),
            "current_mmr": monthly_ranking.get("current_mmr"),
            "baseline_mmr": monthly_ranking.get("baseline_mmr"),
            "net_mmr_gain": monthly_ranking.get("mmr_gain"),
            "elo_core_gain": delta_breakdown["values"]["elo_core_gain"],
            "performance_modifier_gain": delta_breakdown["values"]["performance_modifier_gain"],
            "proxy_modifier_gain": delta_breakdown["values"]["proxy_modifier_gain"],
            "confidence": components.get("confidence"),
            "avg_participation_ratio": components.get("avg_participation_ratio"),
            "materialization": delta_breakdown["materialization"],
        }
        enriched["monthly_ranking"] = monthly_ranking
    persistent_rating = dict(profile.get("persistent_rating")) if isinstance(profile.get("persistent_rating"), dict) else None
    if persistent_rating is not None:
        persistent_rating["meaning"] = "persistent competitive rating for the selected scope"
        enriched["persistent_rating"] = persistent_rating
    enriched["telemetry_boundary"] = {
        "accuracy_mode": accuracy_contract.get("accuracy_mode"),
        "blocked_components": accuracy_contract.get("blocked_components") or [],
    }
    return enriched


def _resolve_elo_delta_sources(
    components: dict[str, object],
    *,
    persistent_rating: dict[str, object] | None,
) -> dict[str, object]:
    elo_core_gain = _coerce_optional_float(components.get("elo_core_gain"))
    performance_modifier_gain = _coerce_optional_float(components.get("performance_modifier_gain"))
    proxy_modifier_gain = _coerce_optional_float(components.get("proxy_modifier_gain"))
    if (
        elo_core_gain is not None
        or performance_modifier_gain is not None
        or proxy_modifier_gain is not None
    ):
        return {
            "values": {
                "elo_core_gain": elo_core_gain,
                "performance_modifier_gain": performance_modifier_gain,
                "proxy_modifier_gain": proxy_modifier_gain,
            },
            "materialization": {
                "status": "v3-materialized",
                "reason": "persisted-monthly-ranking-includes-v3-delta-sources",
                "delta_sources_accuracy": "exact-or-proxy-as-persisted",
            },
        }

    legacy_net_gain = _coerce_optional_float(components.get("mmr_gain_raw"))
    if legacy_net_gain is None and isinstance(persistent_rating, dict):
        legacy_net_gain = _coerce_optional_float(persistent_rating.get("mmr_gain"))
    if legacy_net_gain is None:
        return {
            "values": {
                "elo_core_gain": None,
                "performance_modifier_gain": None,
                "proxy_modifier_gain": None,
            },
            "materialization": {
                "status": "v3-delta-sources-unavailable",
                "reason": (
                    "persisted-monthly-ranking-predates-v3-delta-split-and-has-no-compatible-net-gain"
                ),
                "delta_sources_accuracy": "not_available",
            },
        }

    return {
        "values": {
            "elo_core_gain": legacy_net_gain,
            "performance_modifier_gain": 0.0,
            "proxy_modifier_gain": 0.0,
        },
        "materialization": {
            "status": "legacy-compatibility-approximation",
            "reason": (
                "persisted-monthly-ranking-predates-v3-delta-split-api-approximates-delta-sources-"
                "from-legacy-net-mmr-gain"
            ),
            "delta_sources_accuracy": "approximate",
        },
    }


def _coerce_optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 3)
    except (TypeError, ValueError):
        return None


def _build_monthly_mvp_title(*, is_all_servers: bool, snapshot: bool = False) -> str:
    prefix = "Snapshot " if snapshot else ""
    scope_label = "global" if is_all_servers else "por servidor"
    return f"{prefix}Top MVP mensual {scope_label}"


def _build_monthly_mvp_v2_title(*, is_all_servers: bool, snapshot: bool = False) -> str:
    prefix = "Snapshot " if snapshot else ""
    scope_label = "global" if is_all_servers else "por servidor"
    return f"{prefix}Top MVP mensual V2 {scope_label}"


def _build_player_event_title(
    *,
    view: str,
    is_all_servers: bool,
    snapshot: bool = False,
) -> str:
    prefix = "Snapshot " if snapshot else ""
    scope_label = "global" if is_all_servers else "por servidor"
    title_by_view = {
        "most-killed": f"{prefix}Most killed mensual {scope_label}",
        "death-by": f"{prefix}Death by mensual {scope_label}",
        "duels": f"{prefix}Duelos netos mensuales {scope_label}",
        "weapon-kills": f"{prefix}Kills por arma mensuales {scope_label}",
        "teamkills": f"{prefix}Teamkills mensuales {scope_label}",
    }
    return title_by_view.get(view, f"{prefix}Metricas V2 mensuales {scope_label}")


def _resolve_player_event_snapshot_type(view: str) -> str:
    normalized_view = view.strip().lower() if isinstance(view, str) else "most-killed"
    snapshot_type_by_view = {
        "most-killed": SNAPSHOT_TYPE_PLAYER_EVENT_MOST_KILLED,
        "death-by": SNAPSHOT_TYPE_PLAYER_EVENT_DEATH_BY,
        "duels": SNAPSHOT_TYPE_PLAYER_EVENT_DUELS,
        "weapon-kills": SNAPSHOT_TYPE_PLAYER_EVENT_WEAPON_KILLS,
        "teamkills": SNAPSHOT_TYPE_PLAYER_EVENT_TEAMKILLS,
    }
    return snapshot_type_by_view.get(normalized_view, SNAPSHOT_TYPE_PLAYER_EVENT_MOST_KILLED)
