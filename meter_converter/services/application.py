from __future__ import annotations

from pathlib import Path

from meter_converter.domain import (
    ConversionResult,
    InputValueType,
    Period,
    ProcessingMode,
    ReferenceRecord,
)
from meter_converter.errors import ConverterError
from meter_converter.parsers.registry import ParserRegistry
from meter_converter.services.excel_exporter import ExcelProfileExporter
from meter_converter.services.output_path import OutputPathGenerator
from meter_converter.services.reference_catalog import ReferenceCatalog
from meter_converter.services.reference_directory import (
    ReferenceDirectoryLoader,
    ReferenceDirectoryReport,
)
from meter_converter.services.timeline_validator import TimelineValidator


class ConverterService:
    """Application service: orchestrates parsing, validation and exporting."""

    def __init__(
        self,
        parsers: ParserRegistry | None = None,
        validator: TimelineValidator | None = None,
        references: ReferenceCatalog | None = None,
        exporter: ExcelProfileExporter | None = None,
        output_paths: OutputPathGenerator | None = None,
        reference_directory: Path | None = None,
    ) -> None:
        self.parsers = parsers or ParserRegistry()
        self.validator = validator or TimelineValidator()
        self.references = references or ReferenceCatalog()
        self.exporter = exporter or ExcelProfileExporter()
        self.output_paths = output_paths or OutputPathGenerator()
        self.reference_loader = (
            ReferenceDirectoryLoader(reference_directory)
            if reference_directory is not None
            else None
        )

    def load_reference(self, path: Path, month: str, year: str) -> None:
        """Programmatic compatibility helper; UI uses the reference directory."""
        self.references.load(path, Period(month=month, year=year))

    def refresh_references(self, *, force: bool = False) -> ReferenceDirectoryReport:
        if self.reference_loader is None:
            return ReferenceDirectoryReport(loaded_periods=self.references.periods)
        self.references, report = self.reference_loader.refresh(
            self.references,
            force=force,
        )
        return report

    @property
    def reference_directory(self) -> Path | None:
        return self.reference_loader.directory if self.reference_loader else None

    @property
    def reference_periods(self) -> tuple[Period, ...]:
        return self.references.periods

    @property
    def has_references(self) -> bool:
        return not self.references.is_empty

    def suggest_kt(self, source_path: Path) -> float | None:
        """Auto-mode preview: lookup the point number from the source folder name."""
        self.refresh_references()
        point_number = source_path.parent.name
        reference = self.references.lookup(point_number)
        return reference.transformation_coefficient if reference else None

    def find_reference(
        self,
        value: str,
        input_type: InputValueType,
    ) -> ReferenceRecord | None:
        self.refresh_references()
        return self._lookup_reference(value, input_type)

    def convert(
        self,
        source_path: Path,
        mode: ProcessingMode,
        input_text: str = "",
        input_type: InputValueType = InputValueType.POINT,
    ) -> ConversionResult:
        if not source_path.exists():
            raise ConverterError("Выбранный файл не существует.")

        self.refresh_references()
        kt, point_number, provider = self._resolve_context(
            source_path=source_path,
            mode=mode,
            input_text=input_text,
            input_type=input_type,
        )

        parser = self.parsers.for_path(source_path)
        profile = self.validator.validate(parser.parse(source_path))
        output_path = self.output_paths.next_path(source_path)

        self.exporter.export(
            profile=profile,
            output_path=output_path,
            kt=kt,
            point_number=point_number,
            reference_provider=provider,
        )
        return ConversionResult(output_path=output_path)

    def _resolve_context(
        self,
        *,
        source_path: Path,
        mode: ProcessingMode,
        input_text: str,
        input_type: InputValueType,
    ):
        value = input_text.strip()
        if not value and mode == ProcessingMode.AUTO:
            return self._auto_reference_context(source_path)
        return self._selected_input_context(value, input_type)

    def _auto_reference_context(self, source_path: Path):
        point_number: str | None = None
        provider = None
        kt = 1.0

        if not self.references.is_empty:
            point_number = source_path.parent.name
            provider = lambda period: self.references.lookup(point_number, period)
            fallback = self.references.lookup(point_number)
            if fallback and fallback.transformation_coefficient is not None:
                kt = fallback.transformation_coefficient

        return kt, point_number, provider

    def _selected_input_context(self, value: str, input_type: InputValueType):
        if not value:
            raise ConverterError("Введите значение.")

        if input_type == InputValueType.KT:
            return self._kt_context(value)

        if self.references.is_empty:
            raise ConverterError(
                "Справочники не найдены. Положите файлы вида 09.26.xlsx в папку «справочники»."
            )

        reference = self._lookup_reference(value, input_type)
        if reference is None:
            kind_label = (
                "номер точки учета"
                if input_type == InputValueType.POINT
                else "заводской номер"
            )
            raise ConverterError(f"«{value}» не найден как {kind_label}.")
        if reference.transformation_coefficient is None:
            raise ConverterError(f"Для «{value}» в справочнике не указан КТ.")

        point_number = reference.point_number
        fallback_kt = reference.transformation_coefficient
        provider = lambda period: self._lookup_reference(value, input_type, period)
        return fallback_kt, point_number, provider

    def _lookup_reference(
        self,
        value: str,
        input_type: InputValueType,
        period: Period | None = None,
    ) -> ReferenceRecord | None:
        if input_type == InputValueType.POINT:
            return self.references.lookup(value, period)
        if input_type == InputValueType.SERIAL:
            return self.references.lookup_serial(value, period)
        return self.references.lookup_identifier(value, period)

    def _kt_context(self, value: str):
        kt = self._parse_required_kt(value)
        return kt, None, None

    @staticmethod
    def _parse_kt(value: str) -> float:
        try:
            return float(value.strip().replace(",", "."))
        except (TypeError, ValueError):
            return 1.0

    @staticmethod
    def _parse_required_kt(value: str) -> float:
        text = value.strip().replace(",", ".")
        if not text:
            raise ConverterError("Введите КТ.")
        try:
            return float(text)
        except (TypeError, ValueError):
            raise ConverterError("КТ должен быть числом.")
