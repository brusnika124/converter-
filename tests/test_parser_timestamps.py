from datetime import datetime

from meter_converter.domain import IntervalInfo
from meter_converter.parsers.common import (
    timestamp_from_html_end_time,
    timestamp_from_txt_range,
    timestamp_from_xlsx_date_cell,
)


def test_xlsx_timestamp_uses_interval_start():
    assert timestamp_from_xlsx_date_cell("01.06.2026 11:00 - 12:00") == datetime(
        2026, 6, 1, 11, 0
    )


def test_html_midnight_end_stays_on_reported_day_as_last_interval():
    assert timestamp_from_html_end_time(
        "31.07.26", "00:00", IntervalInfo(60)
    ) == datetime(2026, 7, 31, 23, 0)


def test_txt_timestamp_uses_range_start():
    assert timestamp_from_txt_range("01.07.2026", "23:30-00:00") == datetime(
        2026, 7, 1, 23, 30
    )
