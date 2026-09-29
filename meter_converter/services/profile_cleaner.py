from __future__ import annotations

from meter_converter.services.legacy_partition import LegacyPartitionFallback


class ProfileCleaner(LegacyPartitionFallback):
    """Backward-compatible name for the old position-based fallback.

    New conversion flows use `TimelineValidator`.
    """
