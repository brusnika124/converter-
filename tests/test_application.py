from meter_converter.domain import InputValueType, Period, ProcessingMode
from meter_converter.services.application import ConverterService


def test_invalid_kt_keeps_legacy_default():
    assert ConverterService._parse_kt("") == 1.0
    assert ConverterService._parse_kt("not-a-number") == 1.0
    assert ConverterService._parse_kt("2,5") == 2.5


def test_find_reference_can_be_found_by_point_or_serial(tmp_path):
    import pandas as pd

    rows = [[None] * 23 for _ in range(7)]
    rows[6][4] = "660185121"
    rows[6][9] = "012288182212039"
    rows[6][10] = 600
    rows[6][22] = "x"
    path = tmp_path / "reference.xlsx"
    pd.DataFrame(rows).to_excel(path, index=False, header=False)

    service = ConverterService()
    service.load_reference(path, "08", "2026")

    by_point = service.find_reference("660185121", InputValueType.POINT)
    by_serial = service.find_reference("012288182212039", InputValueType.SERIAL)

    assert by_point is not None
    assert by_serial is not None
    assert by_point.point_number == "660185121"
    assert by_serial.point_number == "660185121"
    assert by_point.transformation_coefficient == 600
    assert by_serial.transformation_coefficient == 600


def test_point_context_uses_period_lookup(tmp_path):
    import pandas as pd

    service = ConverterService()
    for month, kt in [("07", 400), ("08", 600)]:
        rows = [[None] * 23 for _ in range(7)]
        rows[6][4] = "660185121"
        rows[6][9] = "012288182212039"
        rows[6][10] = kt
        rows[6][22] = "x"
        path = tmp_path / f"reference_{month}.xlsx"
        pd.DataFrame(rows).to_excel(path, index=False, header=False)
        service.load_reference(path, month, "2026")

    fallback_kt, point_number, provider = service._selected_input_context(
        "660185121", InputValueType.POINT
    )

    assert fallback_kt == 400
    assert point_number == "660185121"
    assert provider(Period("07", "2026")).transformation_coefficient == 400
    assert provider(Period("08", "2026")).transformation_coefficient == 600
    assert provider(Period("06", "2026")) is None


def test_serial_context_resolves_point_number_and_monthly_kt(tmp_path):
    import pandas as pd

    service = ConverterService()
    for month, kt in [("07", 400), ("08", 600)]:
        rows = [[None] * 23 for _ in range(7)]
        rows[6][4] = "660185121"
        rows[6][9] = "012288182212039"
        rows[6][10] = kt
        rows[6][22] = "x"
        path = tmp_path / f"reference_{month}.xlsx"
        pd.DataFrame(rows).to_excel(path, index=False, header=False)
        service.load_reference(path, month, "2026")

    fallback_kt, point_number, provider = service._selected_input_context(
        "012288182212039", InputValueType.SERIAL
    )

    assert fallback_kt == 400
    assert point_number == "660185121"
    assert provider(Period("07", "2026")).transformation_coefficient == 400
    assert provider(Period("08", "2026")).transformation_coefficient == 600


def test_direct_kt_context_uses_manual_kt_without_reference():
    service = ConverterService()
    kt, point_number, provider = service._selected_input_context("600", InputValueType.KT)
    assert kt == 600
    assert point_number is None
    assert provider is None
