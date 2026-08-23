"""Temporary compatibility exports for the renamed read-only repository."""

from .postgres_repository import (
    CURRENT_MAP_MATCH_SQL,
    MATCH_COMBAT_AGGREGATE_SQL,
    MATCH_LOG_EVENTS_SQL,
    PLAYER_AGGREGATE_SQL,
    PostgresCrconRepository,
)
from .repository import (
    CrconCurrentMap,
    CrconMatchCombatStats,
    CrconMatchLogEvent,
    CrconPlayerAggregate,
    CrconServerScope,
)

CrconDatabase = PostgresCrconRepository

__all__ = [
    "CrconCurrentMap",
    "CrconDatabase",
    "CrconMatchCombatStats",
    "CrconMatchLogEvent",
    "CrconPlayerAggregate",
    "CrconServerScope",
    "PostgresCrconRepository",
    "CURRENT_MAP_MATCH_SQL",
    "MATCH_COMBAT_AGGREGATE_SQL",
    "MATCH_LOG_EVENTS_SQL",
    "PLAYER_AGGREGATE_SQL",
]
