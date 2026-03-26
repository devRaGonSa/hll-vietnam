"""Contracts and capability helpers for the Elo/MMR monthly ranking system."""

from __future__ import annotations

from dataclasses import asdict, dataclass


CAPABILITY_EXACT = "exact"
CAPABILITY_APPROXIMATE = "approximate"
CAPABILITY_UNAVAILABLE = "not_available"

ACCURACY_EXACT = "exact"
ACCURACY_APPROXIMATE = "approximate"
ACCURACY_PARTIAL = "partial"

DEFAULT_BASE_MMR = 1000.0
MIN_VALID_MATCH_DURATION_SECONDS = 900
MIN_VALID_MATCH_PLAYERS = 20
MIN_VALID_PLAYER_PARTICIPATION_SECONDS = 600
MIN_VALID_PLAYER_PARTICIPATION_RATIO = 0.35
FULL_QUALITY_PLAYER_COUNT = 70
FULL_QUALITY_DURATION_SECONDS = 3600
MONTHLY_MIN_VALID_MATCHES = 5
MONTHLY_MIN_TIME_SECONDS = 21600
MONTHLY_ACTIVITY_TARGET_MATCHES = 12
MONTHLY_ACTIVITY_TARGET_HOURS = 20.0
DEFAULT_MONTHLY_SCOREBOARD_MIN_MATCHES = 3
ELO_K_FACTOR = 28.0
PERSISTENT_RATING_MODEL_VERSION = "elo-v3-competitive"
PERSISTENT_RATING_FORMULA_VERSION = "elo-v3-competitive-match-v2"
PERSISTENT_RATING_CONTRACT_VERSION = "elo-mmr-player-rating-v2"
MATCH_RESULT_CONTRACT_VERSION = "elo-mmr-match-result-v2"
MONTHLY_RANKING_MODEL_VERSION = "elo-v3-competitive"
MONTHLY_RANKING_FORMULA_VERSION = "elo-v3-competitive-balanced-v2"
MONTHLY_RANKING_CONTRACT_VERSION = "elo-mmr-monthly-ranking-v2"
MONTHLY_CHECKPOINT_CONTRACT_VERSION = "elo-mmr-monthly-checkpoint-v2"


@dataclass(frozen=True, slots=True)
class EloSignalAvailability:
    """Normalized availability state for one scoring input."""

    name: str
    status: str
    detail: str

    def to_dict(self) -> dict[str, object]:
        """Return the availability entry as a serializable mapping."""
        return asdict(self)


def build_signal(name: str, status: str, detail: str) -> dict[str, object]:
    """Create a normalized availability block for one signal."""
    return EloSignalAvailability(name=name, status=status, detail=detail).to_dict()


def summarize_accuracy(signals: list[dict[str, object]]) -> dict[str, object]:
    """Summarize exact, approximate and unavailable signals for one calculation."""
    exact_count = sum(1 for signal in signals if signal.get("status") == CAPABILITY_EXACT)
    approximate_count = sum(
        1 for signal in signals if signal.get("status") == CAPABILITY_APPROXIMATE
    )
    unavailable_count = sum(
        1 for signal in signals if signal.get("status") == CAPABILITY_UNAVAILABLE
    )
    if unavailable_count > 0:
        accuracy_mode = ACCURACY_PARTIAL
    elif approximate_count > 0:
        accuracy_mode = ACCURACY_APPROXIMATE
    else:
        accuracy_mode = ACCURACY_EXACT
    total = max(1, len(signals))
    return {
        "accuracy_mode": accuracy_mode,
        "exact_count": exact_count,
        "approximate_count": approximate_count,
        "unavailable_count": unavailable_count,
        "exact_ratio": round(exact_count / total, 3),
        "approximate_ratio": round(approximate_count / total, 3),
        "unavailable_ratio": round(unavailable_count / total, 3),
        "signals": list(signals),
    }
