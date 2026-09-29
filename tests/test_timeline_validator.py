from datetime import datetime

import pandas as pd

from meter_converter.domain import DataType, IntervalInfo, ParsedProfile
from meter_converter.services.timeline_validator import TimelineValidator


def _profile(timestamps: list[datetime], values: list[float] | None = None) -> ParsedProfile:
    values = values or [float(index + 1) for index in range(len(timestamps))]
    return ParsedProfile(
        frame=pd.DataFrame(
            {
                "Дата": [value.strftime("%d.%m.%Y %H:%M") for value in timestamps],
                "P+": values,
                "_timestamp": timestamps,
            }
        ),
        date_column="Дата",
        value_column="P+",
        value_column_index=1,
        data_type=DataType.P_PLUS,
        interval=IntervalInfo(60),
    )


def test_partial_month_uses_real_timestamp_for_period_split():
    profile = _profile(
        [
            datetime(2026, 6, 30, 22),
            datetime(2026, 6, 30, 23),
            datetime(2026, 7, 1, 0),
            datetime(2026, 7, 1, 1),
        ]
    )

    validated = TimelineValidator().validate(profile).frame

    assert list(validated["_month"]) == ["06", "06", "07", "07"]
    assert list(validated["_year"]) == ["2026"] * 4
    assert validated["_error"].isna().all()


def test_backward_date_block_is_repaired_and_marked_as_outlier():
    profile = _profile(
        [
            datetime(2026, 7, 12, 8),
            datetime(2026, 7, 12, 9),
            datetime(2026, 4, 18, 2),
            datetime(2026, 4, 18, 3),
            datetime(2026, 7, 12, 12),
        ]
    )

    validated = TimelineValidator().validate(profile).frame

    assert list(validated["_error"].fillna("")) == ["", "", "*", "*", ""]
    assert validated.loc[2, "P+"] == 0
    assert validated.loc[3, "P+"] == 0
    assert validated.loc[2, "_timestamp"] == pd.Timestamp("2026-07-12 10:00")
    assert validated.loc[3, "_timestamp"] == pd.Timestamp("2026-07-12 11:00")
    assert set(validated["_month"]) == {"07"}


def test_forward_date_block_is_repaired_and_marked_as_outlier():
    profile = _profile(
        [
            datetime(2026, 7, 12, 8),
            datetime(2026, 7, 12, 9),
            datetime(2026, 10, 1, 10),
            datetime(2026, 10, 1, 11),
            datetime(2026, 7, 12, 12),
        ]
    )

    validated = TimelineValidator().validate(profile).frame

    assert list(validated["_error"].fillna("")) == ["", "", "*", "*", ""]
    assert set(validated["_month"]) == {"07"}


def test_any_forward_break_is_an_error_because_profiles_are_continuous():
    profile = _profile(
        [
            datetime(2026, 7, 12, 8),
            datetime(2026, 7, 12, 9),
            datetime(2026, 7, 12, 11),
            datetime(2026, 7, 12, 11),
            datetime(2026, 7, 12, 12),
        ]
    )

    validated = TimelineValidator().validate(profile).frame

    assert list(validated["_error"].fillna("")) == ["", "", "*", "", ""]
    assert validated.loc[2, "P+"] == 0
    assert validated.loc[2, "_timestamp"] == pd.Timestamp("2026-07-12 10:00")
