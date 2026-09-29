import pandas as pd

from meter_converter.domain import DataType, IntervalInfo, ParsedProfile
from meter_converter.services.profile_cleaner import ProfileCleaner


def test_wrong_month_inside_expected_block_is_zeroed_and_marked():
    profile = ParsedProfile(
        frame=pd.DataFrame(
            {
                "Дата": ["01.01.2026 00:00", "01.02.2026 01:00"],
                "P+": [10.0, 20.0],
                "_month": ["01", "02"],
                "_year": ["2026", "2026"],
            }
        ),
        date_column="Дата",
        value_column="P+",
        value_column_index=1,
        data_type=DataType.P_PLUS,
        interval=IntervalInfo(60),
    )

    cleaned = ProfileCleaner().clean(profile).frame

    assert cleaned.loc[0, "P+"] == 10.0
    assert cleaned.loc[0, "_error"] is None
    assert cleaned.loc[1, "P+"] == 0.0
    assert cleaned.loc[1, "_error"] == "*"
    assert cleaned.loc[1, "_month"] == "01"
    assert cleaned.loc[1, "_year"] == "2026"
