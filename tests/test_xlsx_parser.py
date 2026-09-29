from openpyxl import Workbook

from meter_converter.domain import DataType
from meter_converter.parsers.xlsx_parser import XlsxProfileParser


def test_xlsx_detects_a_plus_and_hour_interval(tmp_path):
    path = tmp_path / "source.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet["A1"] = "Дата"
    sheet["B1"] = "A+"
    sheet["A2"] = "01.01.2026 00:00 - 01:00"
    sheet["B2"] = 5
    sheet["A3"] = "01.01.2026 01:00 - 02:00"
    sheet["B3"] = 6
    workbook.save(path)
    workbook.close()

    parsed = XlsxProfileParser().parse(path)

    assert parsed.data_type == DataType.A_PLUS
    assert parsed.value_column == "A+"
    assert parsed.interval.minutes == 60
    assert list(parsed.frame["A+"]) == [5, 6]


def test_xlsx_ignores_trailing_status_rows(tmp_path):
    path = tmp_path / "source_with_status.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet["A1"] = "Дата"
    sheet["B1"] = "P+"
    sheet["A2"] = "31.08.2026 22:00 - 23:00"
    sheet["B2"] = 1.25
    sheet["A3"] = "31.08.2026 23:00 - 24:00"
    sheet["B3"] = 1.5
    sheet["A4"] = None
    sheet["A5"] = "Статус данных:"
    sheet["A6"] = "Рассчитаны"
    sheet["A7"] = "Неполные"
    workbook.save(path)
    workbook.close()

    parsed = XlsxProfileParser().parse(path)

    assert len(parsed.frame) == 2
    assert list(parsed.frame["P+"]) == [1.25, 1.5]
    assert parsed.frame["_timestamp"].notna().all()
