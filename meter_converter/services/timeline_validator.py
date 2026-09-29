from __future__ import annotations

import pandas as pd

from meter_converter.domain import ParsedProfile
from meter_converter.errors import InvalidProfileError
from meter_converter.services.legacy_partition import LegacyPartitionFallback


class TimelineValidator:
    """Validate and normalize a continuous meter-profile timeline.

    The parser-provided timestamp is the source of truth for period splitting.
    The business assumption is that profile measurements are continuous for the
    detected interval. Therefore, once the first timestamp is accepted, every
    following row must be exactly one interval later.

    If a row breaks that sequence, its displayed source date is kept unchanged,
    while its internal timestamp is repaired to the expected value, its reading
    is replaced with 0 and `_error='*'` is set. This lets later correct rows
    naturally rejoin the expected timeline.
    """

    def __init__(self, fallback: LegacyPartitionFallback | None = None) -> None:
        self._fallback = fallback or LegacyPartitionFallback()

    def validate(self, profile: ParsedProfile) -> ParsedProfile:
        frame = profile.frame.reset_index(drop=True).copy()
        if frame.empty:
            raise InvalidProfileError("Профиль не содержит данных.")

        timestamp_column = profile.timestamp_column
        if timestamp_column not in frame.columns:
            return self._fallback.clean(profile)

        raw_timestamps = pd.to_datetime(frame[timestamp_column], errors="coerce")
        if raw_timestamps.empty or pd.isna(raw_timestamps.iloc[0]):
            return self._fallback.clean(profile)

        step_minutes = profile.interval.minutes
        if step_minutes is None or step_minutes <= 0:
            # Without a known interval we cannot repair timeline anomalies, but
            # valid timestamps are still enough to split the profile by month.
            if raw_timestamps.isna().any():
                return self._fallback.clean(profile)
            frame[timestamp_column] = raw_timestamps
            frame["_error"] = None
            self._assign_periods(frame, timestamp_column)
            profile.frame = frame
            return profile

        step = pd.Timedelta(minutes=step_minutes)
        frame["_error"] = None

        corrected: list[pd.Timestamp] = [raw_timestamps.iloc[0]]
        previous = corrected[0]

        for index in range(1, len(frame)):
            expected = previous + step
            raw = raw_timestamps.iloc[index]

            if pd.isna(raw) or raw != expected:
                current = self._mark_outlier(frame, profile, index, expected)
            else:
                current = raw

            corrected.append(current)
            previous = current

        frame[timestamp_column] = corrected
        self._assign_periods(frame, timestamp_column)
        profile.frame = frame
        return profile

    # Compatibility with the old service name while callers migrate.
    def clean(self, profile: ParsedProfile) -> ParsedProfile:
        return self.validate(profile)

    @staticmethod
    def _mark_outlier(
        frame: pd.DataFrame,
        profile: ParsedProfile,
        index: int,
        expected: pd.Timestamp,
    ) -> pd.Timestamp:
        frame.at[index, profile.value_column] = 0
        frame.at[index, "_error"] = "*"
        return expected

    @staticmethod
    def _assign_periods(frame: pd.DataFrame, timestamp_column: str) -> None:
        timestamps = pd.to_datetime(frame[timestamp_column], errors="raise")
        frame["_month"] = timestamps.dt.month.astype(str).str.zfill(2)
        frame["_year"] = timestamps.dt.year.astype(str)
