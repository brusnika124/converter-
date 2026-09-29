from __future__ import annotations

from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET

import pandas as pd

from meter_converter.domain import DataType, IntervalInfo, ParsedProfile
from meter_converter.errors import InvalidProfileError
from meter_converter.parsers.base import ProfileParser


class XmlProfileParser(ProfileParser):
    """Parser for Excel 2003 XML power-profile exports.

    The source stores active power in watts and, in observed exports, rows are
    ordered newest-to-oldest.  This parser normalizes both details at the input
    boundary: values are converted W -> kW and rows are returned in ascending
    timestamp order so the rest of the application can stay format-agnostic.
    """

    DATE_FORMAT = "%d.%m.%y %H:%M:%S"
    WATTS_PER_KILOWATT = 1000.0

    def parse(self, path: Path) -> ParsedProfile:
        records = self._read_records(path)
        if not records:
            raise InvalidProfileError("XML-файл не содержит строк профиля мощности.")

        records.sort(key=lambda item: item[0])
        interval = self._detect_interval(records)

        frame = pd.DataFrame(
            {
                "Время": [timestamp.strftime(self.DATE_FORMAT) for timestamp, _ in records],
                DataType.P_PLUS.value: [watts / self.WATTS_PER_KILOWATT for _, watts in records],
                "_timestamp": [timestamp for timestamp, _ in records],
            }
        )

        return ParsedProfile(
            frame=frame,
            date_column="Время",
            value_column=DataType.P_PLUS.value,
            value_column_index=1,
            data_type=DataType.P_PLUS,
            interval=interval,
        )

    def _read_records(self, path: Path) -> list[tuple[datetime, float]]:
        records: list[tuple[datetime, float]] = []
        try:
            for _, element in ET.iterparse(path, events=("end",)):
                if self._local_name(element.tag) != "Row":
                    continue

                values = self._row_values(element)
                element.clear()
                if len(values) < 2 or values[0] is None or values[1] is None:
                    continue

                timestamp = self._parse_timestamp(values[0])
                watts = self._parse_number(values[1])
                if timestamp is None or watts is None:
                    continue

                records.append((timestamp, watts))
        except (ET.ParseError, OSError) as exc:
            raise InvalidProfileError(f"Не удалось прочитать XML-профиль: {exc}") from exc

        return records

    @classmethod
    def _detect_interval(cls, records: list[tuple[datetime, float]]) -> IntervalInfo:
        if len(records) < 2:
            return IntervalInfo(None)

        delta_seconds = (records[1][0] - records[0][0]).total_seconds()
        if delta_seconds <= 0 or delta_seconds % 60 != 0:
            return IntervalInfo(None)
        return IntervalInfo(int(delta_seconds // 60))

    @classmethod
    def _row_values(cls, row: ET.Element) -> list[str | None]:
        values: list[str | None] = []
        for cell in row:
            if cls._local_name(cell.tag) != "Cell":
                continue

            # SpreadsheetML may use ss:Index to skip empty cells. Respect it so
            # the first two logical columns remain correctly aligned.
            index = None
            for key, value in cell.attrib.items():
                if cls._local_name(key) == "Index":
                    try:
                        index = int(value)
                    except ValueError:
                        index = None
                    break
            if index is not None:
                while len(values) < index - 1:
                    values.append(None)

            data_text: str | None = None
            for child in cell:
                if cls._local_name(child.tag) == "Data":
                    data_text = child.text
                    break
            values.append(data_text)
        return values

    @classmethod
    def _parse_timestamp(cls, value: object) -> datetime | None:
        try:
            return datetime.strptime(str(value).strip(), cls.DATE_FORMAT)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_number(value: object) -> float | None:
        try:
            return float(str(value).strip().replace(" ", "").replace(",", "."))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _local_name(tag: str) -> str:
        return tag.rsplit("}", 1)[-1]
