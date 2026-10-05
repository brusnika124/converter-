from pathlib import Path

import pandas as pd
from openpyxl import Workbook, load_workbook

from meter_converter.domain import (
    DataType,
    IntervalInfo,
    ParsedProfile,
    Period,
    ReferenceRecord,
)
from meter_converter.services.loading_statement import LoadingStatementService


def _template(path: Path) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Лист1"
    row = 3
    for day in range(1, 32):
        for hour in range(24):
            worksheet.cell(row=row, column=1, value=day)
            worksheet.cell(row=row, column=2, value=hour)
            row += 1
    workbook.save(path)
    workbook.close()


def _profile() -> ParsedProfile:
    frame = pd.DataFrame(
        {
            "Дата": ["31.07", "31.07", "01.08", "01.08"],
            "P+": [1.0, 2.0, 3.0, 4.0],
            "_month": ["07", "07", "08", "08"],
            "_year": ["2026", "2026", "2026", "2026"],
            "_error": [None, None, None, None],
        }
    )
    return ParsedProfile(
        frame=frame,
        date_column="Дата",
        value_column="P+",
        value_column_index=1,
        data_type=DataType.P_PLUS,
        interval=IntervalInfo(60),
    )


def test_loading_statement_uses_monthly_kt_and_template(tmp_path):
    template = tmp_path / "template.xlsx"
    output = tmp_path / "statement.xlsx"
    _template(template)

    service = LoadingStatementService(template)

    def provider(period: Period):
        kt = 10 if period.month == "07" else 20
        return ReferenceRecord(kt, None, None, None, "660185121")

    service.add_profile(
        profile=_profile(),
        point_number="660185121",
        fallback_kt=1,
        reference_provider=provider,
    )
    service.export(output)

    workbook = load_workbook(output, data_only=True)
    try:
        assert workbook.sheetnames == ["Июль_2026", "Август_2026"]
        july = workbook["Июль_2026"]
        august = workbook["Август_2026"]
        assert july["C1"].value == "660185121"
        assert july["C3"].value == 10
        assert july["C4"].value == 20
        assert august["C1"].value == "660185121"
        assert august["C3"].value == 60
        assert august["C4"].value == 80
        # Template columns A/B remain intact.
        assert july["A3"].value == 1
        assert july["B3"].value == 0
    finally:
        workbook.close()


def test_same_point_updates_existing_column_instead_of_duplicating(tmp_path):
    template = tmp_path / "template.xlsx"
    output = tmp_path / "statement.xlsx"
    _template(template)
    service = LoadingStatementService(template)

    profile = _profile()
    service.add_profile(profile=profile, point_number="100", fallback_kt=1)
    service.add_profile(profile=profile, point_number="200", fallback_kt=1)
    service.add_profile(profile=profile, point_number="100", fallback_kt=2)
    service.export(output)

    workbook = load_workbook(output, data_only=True)
    try:
        july = workbook["Июль_2026"]
        assert july["C1"].value == "100"
        assert july["D1"].value == "200"
        assert july["E1"].value is None
        assert july["C3"].value == 2
        assert july["D3"].value == 1
    finally:
        workbook.close()
