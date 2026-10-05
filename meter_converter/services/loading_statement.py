from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

from openpyxl import load_workbook

from meter_converter.domain import ParsedProfile, Period, ReferenceRecord
from meter_converter.errors import ConverterError
from meter_converter.months import MONTH_NAMES_RU
from meter_converter.services.excel_exporter import ReferenceProvider
from meter_converter.services.kt_calculator import KtCalculator


class LoadingStatementService:
    """Accumulates final values by period/TU and exports them into an XLSX template."""

    def __init__(
        self,
        template_path: Path | None = None,
        kt_calculator: KtCalculator | None = None,
    ) -> None:
        self.template_path = template_path
        self._kt_calculator = kt_calculator or KtCalculator()
        self._data: dict[Period, OrderedDict[str, list[float | None]]] = {}

    @property
    def has_data(self) -> bool:
        return any(points for points in self._data.values())

    @property
    def periods(self) -> tuple[Period, ...]:
        return tuple(sorted(self._data, key=lambda item: (int(item.year), int(item.month))))

    def add_profile(
        self,
        *,
        profile: ParsedProfile,
        point_number: str,
        fallback_kt: float,
        reference_provider: ReferenceProvider | None = None,
    ) -> None:
        point_number = str(point_number).strip()
        if not point_number:
            raise ConverterError(
                "Для формирования загрузочной ведомости необходимо определить номер точки учета."
            )

        for (month, year), group in profile.frame.groupby(["_month", "_year"], sort=True):
            period = Period(month=str(month), year=str(year))
            reference = (
                reference_provider(period)
                if reference_provider is not None
                else None
            )
            kt = self._resolve_kt(reference, fallback_kt)
            values = group[profile.value_column].tolist()
            calculated = self._kt_calculator.calculate(
                values=values,
                interval=profile.interval,
                data_type=profile.data_type,
                kt=kt,
            )

            points = self._data.setdefault(period, OrderedDict())
            # Re-processing the same TU updates its column instead of creating a duplicate.
            points[point_number] = calculated

    def export(self, output_path: Path) -> None:
        if not self.has_data:
            raise ConverterError("В загрузочной ведомости пока нет данных для выгрузки.")
        if self.template_path is None or not self.template_path.exists():
            raise ConverterError(
                "Не найден шаблон загрузочной ведомости. "
                "Файл «шаблон загрузочной ведомости.xlsx» должен находиться рядом с main.py."
            )
        if output_path.resolve() == self.template_path.resolve():
            raise ConverterError("Нельзя сохранять ведомость поверх файла шаблона.")

        workbook = load_workbook(self.template_path)
        try:
            if not workbook.worksheets:
                raise ConverterError("Шаблон загрузочной ведомости не содержит листов.")

            base_sheet = workbook.worksheets[0]
            periods = self.periods

            # Create all monthly copies while the base sheet is still pristine.
            sheets = [base_sheet]
            for _ in periods[1:]:
                sheets.append(workbook.copy_worksheet(base_sheet))

            for worksheet, period in zip(sheets, periods):
                worksheet.title = self._sheet_name(period)
                self._write_period(worksheet, self._data[period])

            # The supplied template currently has one sheet. If a replacement template
            # contains additional sheets, keep only the sheets used by the statement.
            used = set(sheets)
            for worksheet in list(workbook.worksheets):
                if worksheet not in used:
                    workbook.remove(worksheet)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            workbook.save(output_path)
        finally:
            workbook.close()

    @staticmethod
    def _resolve_kt(reference: ReferenceRecord | None, fallback: float) -> float:
        if reference is not None and reference.transformation_coefficient is not None:
            return reference.transformation_coefficient
        return fallback

    @staticmethod
    def _sheet_name(period: Period) -> str:
        month_name = MONTH_NAMES_RU.get(period.month, f"Месяц_{period.month}")
        return f"{month_name}_{period.year}"

    @staticmethod
    def _write_period(worksheet, points: OrderedDict[str, list[float | None]]) -> None:
        for column_index, (point_number, values) in enumerate(points.items(), start=3):
            worksheet.cell(row=1, column=column_index, value=point_number)
            for row_index, value in enumerate(values, start=3):
                worksheet.cell(row=row_index, column=column_index, value=value)
