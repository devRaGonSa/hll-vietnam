"""Shared CRCON foundation models and sanitized adapter errors."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


CRCON_REPOSITORY = "https://github.com/MarechJ/hll_rcon_tool"
CRCON_REFERENCE_BRANCH = "v12.0.1"
CRCON_CONTRACT_REVISION = "17c5880684cc419b27ef2bcca0dc439dfd623eae"
CRCON_TARGET_VERSION = "12.0.1"


class CrconContractStatus(StrEnum):
    """Evidence status for a version-specific API or schema contract."""

    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    UNVERIFIED = "unverified"


class CrconCapability(StrEnum):
    """Independently probed CRCON capabilities used by future migrations."""

    LIVE_STATE = "live_state"
    HISTORICAL_MAPS = "historical_maps"
    HISTORICAL_PLAYER_STATS = "historical_player_stats"
    PLAYER_AGGREGATES = "player_aggregates"
    EVENT_LOGS = "event_logs"
    PLAYER_IDENTITIES = "player_identities"
    PLAYER_SESSIONS = "player_sessions"
    SERVER_COUNT_HISTORY = "server_count_history"


class CrconCapabilityStatus(StrEnum):
    """Compatibility state for one CRCON capability."""

    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"
    INCOMPATIBLE = "incompatible"


class CrconAggregateState(StrEnum):
    """Publicly observable state for a selected CRCON aggregate read."""

    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    UNVERIFIED_SCHEMA = "UNVERIFIED_SCHEMA"
    PERFORMANCE_BLOCKED = "PERFORMANCE_BLOCKED"


class CrconPlayerHistoryState(StrEnum):
    """Runtime state of the authenticated player-history capability."""

    SUPPORTED = "SUPPORTED"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    UNAVAILABLE = "UNAVAILABLE"
    UNVERIFIED_HLLV = "UNVERIFIED_HLLV"


@dataclass(frozen=True, slots=True)
class CrconSourceMetadata:
    """Source observation metadata safe to pass to later domain services."""

    source: str
    observed_at: datetime
    contract_revision: str = CRCON_CONTRACT_REVISION


@dataclass(frozen=True, slots=True)
class CrconCapabilityResult:
    """One precise, sanitized capability result."""

    capability: CrconCapability
    status: CrconCapabilityStatus
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class CrconCapabilityReport:
    """Immutable report whose capabilities fail independently."""

    results: tuple[CrconCapabilityResult, ...]
    contract_revision: str = CRCON_CONTRACT_REVISION

    def get(self, capability: CrconCapability) -> CrconCapabilityResult:
        for result in self.results:
            if result.capability is capability:
                return result
        raise KeyError(capability)

    @property
    def supported(self) -> frozenset[CrconCapability]:
        return frozenset(
            result.capability
            for result in self.results
            if result.status is CrconCapabilityStatus.SUPPORTED
        )


class CrconError(RuntimeError):
    """Base error that must never include upstream credentials or raw payloads."""


class CrconUnavailableError(CrconError):
    """Raised when optional CRCON configuration or access is unavailable."""


class CrconApiError(CrconError):
    """Raised for sanitized CRCON HTTP failures."""


class CrconApiAuthenticationError(CrconApiError):
    """Raised for sanitized HTTP 401/403 CRCON failures."""


class CrconDatabaseError(CrconError):
    """Raised for sanitized CRCON database failures."""


class CrconSchemaIncompatibleError(CrconDatabaseError):
    """Raised when a required CRCON database contract is incompatible."""
