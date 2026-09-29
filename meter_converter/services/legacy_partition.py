from __future__ import annotations

import calendar

import pandas as pd

from meter_converter.domain import ParsedProfile
from meter_converter.errors import InvalidProfileError


class LegacyPartitionFallback:
    """Old position-based month partitioning used only when timestamps are unavailable."""

    def clean(self, profile: ParsedProfile) -> ParsedProfile:
        frame = profile.frame.reset_index(drop=True).copy()
        if frame.empty:
            raise InvalidProfileError("Профиль не содержит данных.")

        start_month, start_year = self._first_period(frame, profile.date_column)
        current_month = start_month
        current_year = start_year
        position = 0
        total = len(frame)
        steps = profile.interval.expected_steps_per_day

        frame["_error"] = None

        while position < total:
            days_in_month = calendar.monthrange(current_year, current_month)[1]
            block_size = days_in_month * steps
            end = min(position + block_size, total)

            for row_index in range(position, end):
                row_month = self._month_or_default(
                    frame.at[row_index, profile.date_column],
                    current_month,
                )

                if row_month != current_month:
                    frame.at[row_index, profile.value_column] = 0
                    frame.at[row_index, "_error"] = "*"

                frame.at[row_index, "_month"] = str(current_month).zfill(2)
                frame.at[row_index, "_year"] = str(current_year)

            position += block_size
            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1

        profile.frame = frame
        return profile

    @staticmethod
    def _first_period(frame: pd.DataFrame, date_column: str) -> tuple[int, int]:
        try:
            first_date = str(frame.at[0, date_column]).split(" ")[0]
            parts = first_date.split(".")
            month = int(parts[1])
            year = int(parts[2][:4])
            if year < 100:
                year += 2000
            return month, year
        except (IndexError, TypeError, ValueError) as exc:
            raise InvalidProfileError(
                "Не удалось определить месяц и год первой строки профиля."
            ) from exc

    @staticmethod
    def _month_or_default(value: object, default: int) -> int:
        try:
            date_part = str(value).split(" ")[0]
            return int(date_part.split(".")[1])
        except (IndexError, TypeError, ValueError):
            return default

