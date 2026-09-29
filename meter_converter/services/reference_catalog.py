from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

import pandas as pd

from meter_converter.domain import Period, ReferenceRecord


class ReferenceCatalog:
    """Хранит справочники, загруженные для конкретных месяца и года."""

    def __init__(self) -> None:
        self._catalogs: OrderedDict[Period, pd.DataFrame] = OrderedDict()

    def load(self, path: Path, period: Period) -> None:
        frame = pd.read_excel(path, skiprows=6, header=None, dtype=str)
        if frame.shape[1] <= 22:
            raise ValueError("В справочнике недостаточно колонок.")

        catalog = frame.iloc[:, [4, 9, 10, 15, 22]].copy()
        catalog.columns = [
            "point_number",
            "serial_number",
            "kt",
            "fpp_volume",
            "meter_consumption",
        ]
        catalog["point_number"] = catalog["point_number"].map(self._to_optional_string)
        catalog["serial_number"] = catalog["serial_number"].map(self._to_optional_string)
        catalog["_point_key"] = catalog["point_number"].map(self._normalize_identifier)
        catalog["_serial_key"] = catalog["serial_number"].map(self._normalize_identifier)
        self._catalogs[period] = catalog

    def lookup(self, point_number: str, period: Period | None = None) -> ReferenceRecord | None:
        """Lookup by point number only. Kept for automatic folder-based mode."""
        catalog = self._select_catalog(period)
        if catalog is None:
            return None
        return self._lookup_in_catalog(catalog, point_number, by_point=True)

    def lookup_identifier(
        self,
        identifier: str,
        period: Period | None = None,
    ) -> ReferenceRecord | None:
        """Find a meter by point number OR factory serial number.

        When a period is supplied, only that month's catalog is searched. Without
        a period, all already-loaded catalogs are searched in load order; this is
        used to obtain a cheap fallback KT for months whose catalog is missing.
        """
        key = self._normalize_identifier(identifier)
        if not key:
            return None

        if period is not None:
            catalog = self._catalogs.get(period)
            return self._lookup_in_catalog(catalog, key) if catalog is not None else None

        for catalog in self._catalogs.values():
            match = self._lookup_in_catalog(catalog, key)
            if match is not None:
                return match
        return None

    def lookup_serial(self, serial_number: str, period: Period | None = None) -> ReferenceRecord | None:
        """Lookup by factory serial number only."""
        key = self._normalize_identifier(serial_number)
        if not key:
            return None

        if period is not None:
            catalog = self._catalogs.get(period)
            return self._lookup_serial_in_catalog(catalog, key) if catalog is not None else None

        for catalog in self._catalogs.values():
            match = self._lookup_serial_in_catalog(catalog, key)
            if match is not None:
                return match
        return None

    @property
    def periods(self) -> tuple[Period, ...]:
        return tuple(self._catalogs.keys())

    @property
    def is_empty(self) -> bool:
        return not self._catalogs

    def _select_catalog(self, period: Period | None) -> pd.DataFrame | None:
        if period is not None:
            return self._catalogs.get(period)
        if not self._catalogs:
            return None
        # Совместимость авто-режима: без периода используется первый справочник.
        return next(iter(self._catalogs.values()))

    def _lookup_in_catalog(
        self,
        catalog: pd.DataFrame,
        identifier: str,
        *,
        by_point: bool = False,
    ) -> ReferenceRecord | None:
        key = self._normalize_identifier(identifier)
        if not key:
            return None

        matches = catalog[catalog["_point_key"] == key]
        if matches.empty and not by_point:
            # If the same numeric value could theoretically exist in both columns,
            # an exact point-number match has priority over a serial-number match.
            matches = catalog[catalog["_serial_key"] == key]

        if matches.empty:
            return None

        row = matches.iloc[0]
        return ReferenceRecord(
            transformation_coefficient=self._to_float(row["kt"]),
            serial_number=self._to_optional_string(row["serial_number"]),
            fpp_volume=self._to_optional_string(row["fpp_volume"]),
            meter_consumption=self._to_optional_string(row["meter_consumption"]),
            point_number=self._to_optional_string(row["point_number"]),
        )

    def _lookup_serial_in_catalog(self, catalog: pd.DataFrame, identifier: str) -> ReferenceRecord | None:
        key = self._normalize_identifier(identifier)
        if not key:
            return None

        matches = catalog[catalog["_serial_key"] == key]
        if matches.empty:
            return None

        row = matches.iloc[0]
        return ReferenceRecord(
            transformation_coefficient=self._to_float(row["kt"]),
            serial_number=self._to_optional_string(row["serial_number"]),
            fpp_volume=self._to_optional_string(row["fpp_volume"]),
            meter_consumption=self._to_optional_string(row["meter_consumption"]),
            point_number=self._to_optional_string(row["point_number"]),
        )

    @staticmethod
    def _normalize_identifier(value: object) -> str:
        if value is None or pd.isna(value):
            return ""
        text = str(value).strip()
        # Excel often turns an integer identifier into e.g. "21.0".
        if text.endswith(".0") and text[:-2].isdigit():
            text = text[:-2]
        if text.isdigit():
            # Numeric identifiers may lose leading zeroes when Excel infers a number.
            return text.lstrip("0") or "0"
        return text

    @staticmethod
    def _to_float(value: object) -> float | None:
        if value is None or pd.isna(value):
            return None
        try:
            return float(str(value).replace(",", "."))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_optional_string(value: object) -> str | None:
        if value is None or pd.isna(value):
            return None
        text = str(value).strip()
        if text.endswith(".0") and text[:-2].isdigit():
            text = text[:-2]
        return text or None
