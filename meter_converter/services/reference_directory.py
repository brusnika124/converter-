from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from meter_converter.domain import Period
from meter_converter.services.reference_catalog import ReferenceCatalog


_REFERENCE_NAME = re.compile(r"^(?P<month>0[1-9]|1[0-2])\.(?P<year>\d{2}|\d{4})\.xlsx$", re.IGNORECASE)


@dataclass(frozen=True)
class ReferenceDirectoryReport:
    loaded_periods: tuple[Period, ...]
    ignored_files: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    changed: bool = False


class ReferenceDirectoryLoader:
    """Loads monthly reference books from a dedicated directory.

    Supported names:
      - 09.26.xlsx
      - 09.2026.xlsx

    The directory is scanned cheaply using file metadata. Excel files are only
    re-read when the directory contents actually change.
    """

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self._last_signature: tuple[tuple[str, int, int], ...] | None = None
        self._last_report = ReferenceDirectoryReport(loaded_periods=())

    def refresh(
        self,
        current_catalog: ReferenceCatalog,
        *,
        force: bool = False,
    ) -> tuple[ReferenceCatalog, ReferenceDirectoryReport]:
        self.directory.mkdir(parents=True, exist_ok=True)
        files = tuple(sorted(self.directory.iterdir(), key=lambda path: path.name.lower()))
        signature = self._signature(files)

        if not force and self._last_signature == signature:
            return current_catalog, self._last_report

        catalog = ReferenceCatalog()
        ignored: list[str] = []
        errors: list[str] = []
        seen_periods: set[Period] = set()

        for path in files:
            if not path.is_file():
                continue
            parsed = self._period_from_name(path.name)
            if parsed is None:
                # .gitkeep and unrelated files are intentionally silent.
                if path.suffix.lower() in {".xlsx", ".xls"}:
                    ignored.append(path.name)
                continue

            if parsed in seen_periods:
                errors.append(
                    f"{path.name}: уже есть справочник за {parsed.month}.{parsed.year}"
                )
                continue

            try:
                catalog.load(path, parsed)
                seen_periods.add(parsed)
            except Exception as exc:
                errors.append(f"{path.name}: {exc}")

        loaded = tuple(sorted(catalog.periods, key=lambda item: (item.year, item.month)))
        report = ReferenceDirectoryReport(
            loaded_periods=loaded,
            ignored_files=tuple(ignored),
            errors=tuple(errors),
            changed=True,
        )
        self._last_signature = signature
        self._last_report = report
        return catalog, report

    @staticmethod
    def _period_from_name(filename: str) -> Period | None:
        match = _REFERENCE_NAME.fullmatch(filename)
        if not match:
            return None
        month = match.group("month")
        raw_year = match.group("year")
        year = f"20{raw_year}" if len(raw_year) == 2 else raw_year
        return Period(month=month, year=year)

    @staticmethod
    def _signature(files: tuple[Path, ...]) -> tuple[tuple[str, int, int], ...]:
        result: list[tuple[str, int, int]] = []
        for path in files:
            if not path.is_file():
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            result.append((path.name, stat.st_mtime_ns, stat.st_size))
        return tuple(result)
