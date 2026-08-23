"""Shared route result contract and identical query parsers."""

from __future__ import annotations

from datetime import datetime, timezone
from http import HTTPStatus
from urllib.parse import parse_qs

RouteResult = tuple[HTTPStatus | None, dict[str, object]]


def unmatched_route() -> RouteResult:
    """Return a fresh unmatched result without shared mutable request state."""
    return None, {}


def parse_limit(query: str) -> int | None:
    raw_limit = parse_qs(query).get("limit", ["20"])[0]
    try:
        limit = int(raw_limit)
    except ValueError:
        return None

    if limit < 1 or limit > 100:
        return None

    return limit


def parse_page(query: str) -> int | None:
    raw_page = parse_qs(query).get("page", ["1"])[0]
    try:
        page = int(raw_page)
    except ValueError:
        return None
    return page if 1 <= page <= 1000 else None


def parse_year(query: str) -> int | None:
    params = parse_qs(query)
    raw_year = params.get("year", [None])[0]
    if raw_year is None:
        return datetime.now(timezone.utc).year
    try:
        year = int(raw_year)
    except ValueError:
        return None
    if year <= 0:
        return None
    return year


def parse_required_year(query: str) -> int | None:
    params = parse_qs(query)
    if "year" not in params:
        return None
    return parse_year(query)


def parse_limit_with_default(query: str, default: int = 20) -> int | None:
    params = parse_qs(query)
    if "limit" not in params:
        return default
    return parse_limit(query)
