from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

import pandas as pd


class ProcessingMode(str, Enum):
    MANUAL = "manual"
    AUTO = "auto"


class InputValueType(str, Enum):
    KT = "kt"
    POINT = "point"
    SERIAL = "serial"


class DataType(str, Enum):
    P_PLUS = "P+"
    A_PLUS = "A+"


@dataclass(frozen=True)
class IntervalInfo:
    minutes: Optional[int]

    @property
    def label(self) -> str:
        if self.minutes == 30:
            return "Получасовки"
        if self.minutes == 60:
            return "Часовки"
        if self.minutes is None:
            return "Неизвестно"
        return f"Интервал {self.minutes} мин"

    @property
    def expected_steps_per_day(self) -> int:
        # Совместимость со старой логикой: только получасовки дают 48,
        # все остальные интервалы обрабатываются как 24 значения в сутки.
        return 48 if self.minutes == 30 else 24


@dataclass
class ParsedProfile:
    frame: pd.DataFrame
    date_column: str
    value_column: str
    value_column_index: int
    data_type: DataType
    interval: IntervalInfo
    serial_number: Optional[str] = None
    timestamp_column: str = "_timestamp"


@dataclass(frozen=True)
class ReferenceRecord:
    transformation_coefficient: Optional[float]
    serial_number: Optional[str]
    fpp_volume: Optional[str]
    meter_consumption: Optional[str]
    point_number: Optional[str] = None


@dataclass(frozen=True)
class Period:
    month: str
    year: str


@dataclass(frozen=True)
class ConversionResult:
    output_path: Path
