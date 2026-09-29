from __future__ import annotations

from collections.abc import Iterable

from meter_converter.domain import DataType, IntervalInfo


class KtCalculator:
    def calculate(
        self,
        values: Iterable[object],
        interval: IntervalInfo,
        data_type: DataType,
        kt: float,
    ) -> list[float | None]:
        source = list(values)
        if interval.minutes == 30:
            return self._calculate_half_hour(source, data_type, kt)
        return self._calculate_other(source, kt)

    @staticmethod
    def _calculate_half_hour(
        values: list[object],
        data_type: DataType,
        kt: float,
    ) -> list[float]:
        numeric = [value if isinstance(value, (int, float)) else 0 for value in values]
        result: list[float] = []
        for index in range(0, len(numeric) - 1, 2):
            first = numeric[index]
            second = numeric[index + 1]
            if data_type == DataType.A_PLUS:
                result.append((first + second) * kt)
            else:
                result.append((first / 2 + second / 2) * kt)
        return result

    @staticmethod
    def _calculate_other(values: list[object], kt: float) -> list[float | None]:
        return [value * kt if isinstance(value, (int, float)) else None for value in values]
