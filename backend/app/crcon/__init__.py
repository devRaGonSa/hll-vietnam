"""Dormant CRCON anti-corruption foundation for future endpoint migrations."""

from .api import CrconApiClient
from .cache import TtlCache
from .database import CrconDatabase
from .models import (
    CRCON_CONTRACT_REVISION,
    CRCON_REFERENCE_BRANCH,
    CRCON_REPOSITORY,
    CrconApiError,
    CrconCapability,
    CrconCapabilityReport,
    CrconCapabilityResult,
    CrconCapabilityStatus,
    CrconDatabaseError,
    CrconError,
    CrconSchemaIncompatibleError,
    CrconSourceMetadata,
    CrconUnavailableError,
)

__all__ = [
    "CRCON_CONTRACT_REVISION",
    "CRCON_REFERENCE_BRANCH",
    "CRCON_REPOSITORY",
    "CrconApiClient",
    "CrconApiError",
    "CrconCapability",
    "CrconCapabilityReport",
    "CrconCapabilityResult",
    "CrconCapabilityStatus",
    "CrconDatabase",
    "CrconDatabaseError",
    "CrconError",
    "CrconSchemaIncompatibleError",
    "CrconSourceMetadata",
    "CrconUnavailableError",
    "TtlCache",
]
