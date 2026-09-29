from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from meter_converter.domain import DataType, ParsedProfile
from meter_converter.errors import InvalidProfileError
from meter_converter.parsers.base import ProfileParser
from meter_converter.parsers.common import (
    interval_from_two_times,
    timestamp_from_html_end_time,
)


class HtmlProfileParser(ProfileParser):
    def parse(self, path: Path) -> ParsedProfile:
        tables = pd.read_html(path)
        if not tables:
            raise InvalidProfileError("В HTML-файле не найдена таблица с профилем.")

        source = tables[0]
        if source.shape[1] < 7:
            raise InvalidProfileError("HTML-таблица имеет неожиданный формат.")

        frame = source.iloc[:, [6, 5, 1]].copy()
        frame.columns = ["Дата", "Время", DataType.P_PLUS.value]
        frame[DataType.P_PLUS.value] = pd.to_numeric(
            frame[DataType.P_PLUS.value].astype(str).str.replace(",", ".", regex=False),
            errors="coerce",
        )
        interval = interval_from_two_times(
            frame["Время"].astype(str).iloc[0].strip(),
            frame["Время"].astype(str).iloc[1].strip(),
        ) if len(frame) >= 2 else interval_from_two_times("", "")

        frame["_timestamp"] = [
            timestamp_from_html_end_time(date, time, interval)
            for date, time in zip(frame["Дата"], frame["Время"])
        ]

        return ParsedProfile(
            frame=frame,
            date_column="Дата",
            value_column=DataType.P_PLUS.value,
            value_column_index=2,
            data_type=DataType.P_PLUS,
            interval=interval,
            serial_number=self._extract_serial(path),
        )

    @staticmethod
    def _extract_serial(path: Path) -> str | None:
        text = _read_text(path, ("utf-8", "cp1251", "latin-1"))
        if not text:
            return None
        match = re.search(r"Серийный номер\s*-\s*(\d+)", text)
        if not match:
            match = re.search(r"\d{6,}", text)
        if not match:
            return None
        return match.group(1) if match.lastindex else match.group(0)


def _read_text(path: Path, encodings: tuple[str, ...]) -> str | None:
    for encoding in encodings:
        try:
            return path.read_text(encoding=encoding)
        except (UnicodeDecodeError, OSError):
            continue
    return None
