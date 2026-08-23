"""Stable API route resolver backed by explicit public-domain routers."""

from __future__ import annotations

from collections.abc import Callable
from urllib.parse import ParseResult, urlparse

from .common import RouteResult
from .current_match import resolve_current_match_route
from .history import resolve_history_route
from .players import resolve_players_route
from .product_features import resolve_product_features_route
from .rankings import resolve_rankings_route
from .servers import resolve_servers_route
from .static import resolve_static_route

DomainRouter = Callable[[ParseResult], RouteResult]

DOMAIN_ROUTERS: tuple[DomainRouter, ...] = (
    resolve_static_route,
    resolve_servers_route,
    resolve_current_match_route,
    resolve_players_route,
    resolve_rankings_route,
    resolve_history_route,
    resolve_product_features_route,
)


def resolve_get_payload(path: str) -> RouteResult:
    """Resolve one GET request through the deterministic domain registry."""
    parsed = urlparse(path)
    for router in DOMAIN_ROUTERS:
        status, payload = router(parsed)
        if status is not None:
            return status, payload
    return None, {}


__all__ = ["resolve_get_payload"]
