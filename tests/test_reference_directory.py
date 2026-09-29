import pandas as pd

from meter_converter.domain import Period
from meter_converter.services.reference_catalog import ReferenceCatalog
from meter_converter.services.reference_directory import ReferenceDirectoryLoader


def _write_reference(path, point="660185121", serial="012288182212039", kt="600"):
    rows = [[None] * 23 for _ in range(7)]
    rows[6][4] = point
    rows[6][9] = serial
    rows[6][10] = kt
    rows[6][15] = "39114"
    rows[6][22] = "39114"
    pd.DataFrame(rows).to_excel(path, index=False, header=False)


def test_loads_period_from_short_filename(tmp_path):
    folder = tmp_path / "справочники"
    folder.mkdir()
    _write_reference(folder / "09.26.xlsx")

    loader = ReferenceDirectoryLoader(folder)
    catalog, report = loader.refresh(ReferenceCatalog())

    assert report.loaded_periods == (Period("09", "2026"),)
    assert catalog.lookup_identifier("012288182212039", Period("09", "2026")) is not None


def test_accepts_four_digit_year_and_ignores_wrong_excel_name(tmp_path):
    folder = tmp_path / "справочники"
    folder.mkdir()
    _write_reference(folder / "08.2026.xlsx", kt="400")
    _write_reference(folder / "ФПП Август.xlsx", kt="999")

    loader = ReferenceDirectoryLoader(folder)
    catalog, report = loader.refresh(ReferenceCatalog())

    assert report.loaded_periods == (Period("08", "2026"),)
    assert report.ignored_files == ("ФПП Август.xlsx",)
    assert catalog.lookup_identifier("660185121", Period("08", "2026")).transformation_coefficient == 400


def test_unchanged_directory_does_not_reload_excel(tmp_path):
    folder = tmp_path / "справочники"
    folder.mkdir()
    _write_reference(folder / "09.26.xlsx")

    loader = ReferenceDirectoryLoader(folder)
    first_catalog, _ = loader.refresh(ReferenceCatalog())
    second_catalog, _ = loader.refresh(first_catalog)

    assert second_catalog is first_catalog
