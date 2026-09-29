import pandas as pd

from meter_converter.domain import Period
from meter_converter.services.reference_catalog import ReferenceCatalog


def _write_reference(path):
    rows = [[None] * 23 for _ in range(8)]
    rows[6][4] = "660185121"
    rows[6][9] = "012288182212039"
    rows[6][10] = "600"
    rows[6][15] = "39114"
    rows[6][22] = "39114"

    rows[7][4] = 777
    rows[7][9] = 21.0
    rows[7][10] = "40,5"
    pd.DataFrame(rows).to_excel(path, index=False, header=False)


def test_lookup_identifier_accepts_point_or_serial(tmp_path):
    path = tmp_path / "reference.xlsx"
    _write_reference(path)
    catalog = ReferenceCatalog()
    period = Period("08", "2026")
    catalog.load(path, period)

    by_point = catalog.lookup_identifier("660185121", period)
    by_serial = catalog.lookup_identifier("012288182212039", period)

    assert by_point is not None
    assert by_serial is not None
    assert by_point == by_serial
    assert by_point.transformation_coefficient == 600
    assert by_point.point_number == "660185121"
    assert by_point.serial_number == "012288182212039"


def test_lookup_identifier_normalizes_excel_integer_serial(tmp_path):
    path = tmp_path / "reference.xlsx"
    _write_reference(path)
    catalog = ReferenceCatalog()
    period = Period("08", "2026")
    catalog.load(path, period)

    record = catalog.lookup_identifier("21", period)

    assert record is not None
    assert record.point_number == "777"
    assert record.serial_number == "21"
    assert record.transformation_coefficient == 40.5
