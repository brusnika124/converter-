from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from meter_converter.domain import DataType, ParsedProfile
from meter_converter.errors import InvalidProfileError
from meter_converter.parsers.base import ProfileParser
from meter_converter.parsers.common import interval_from_range, timestamp_from_txt_range


class TxtProfileParser(ProfileParser):
    def parse(self, path: Path) -> ParsedProfile:
        frame = self._read_table(path)
        if frame.shape[1] < 3:
            raise InvalidProfileError("TXT-файл имеет неожиданный формат.")

        frame = frame.iloc[:, [0, 1, 2]].copy()
        date_column = frame.columns[0]
        time_column = frame.columns[1]
        value_column = frame.columns[2]

        frame[value_column] = pd.to_numeric(
            frame[value_column].astype(str).str.replace(",", ".", regex=False),
            errors="coerce",
        )

        interval = interval_from_range(frame[time_column].astype(str).iloc[0]) if len(frame) else interval_from_range("")
        frame["_timestamp"] = [
            timestamp_from_txt_range(date, time_range)
            for date, time_range in zip(frame[date_column], frame[time_column])
        ]

        return ParsedProfile(
            frame=frame,
            date_column=str(date_column),
            value_column=str(value_column),
            value_column_index=2,
            data_type=DataType.P_PLUS,
            interval=interval,
            serial_number=self._extract_serial(path),
        )

    @staticmethod
    def _read_table(path: Path) -> pd.DataFrame:
        last_error: Exception | None = None
        for encoding in ("cp1251", "utf-8"):
            try:
                return pd.read_csv(path, sep="\t", skiprows=4, encoding=encoding, engine="python")
            except Exception as exc:
                # Совместимость со старой версией: при любой ошибке чтения
                # первым encoding пробуем следующий.
                last_error = exc
        if last_error:
            raise last_error
        raise InvalidProfileError("Не удалось прочитать TXT-файл.")

    @staticmethod
    def _extract_serial(path: Path) -> str | None:
        for encoding in ("cp1251", "utf-8", "latin-1"):
            try:
                text = path.read_text(encoding=encoding)
                break
            except (UnicodeDecodeError, OSError):
                continue
        else:
            return None

        match = re.search(r"Счетчик\s*№\s*(\d+)", text)
        return match.group(1) if match else None
