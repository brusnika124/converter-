from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from meter_converter.domain import IntervalInfo


_DATE_FORMATS = ("%d.%m.%Y", "%d.%m.%y")


def interval_from_two_times(first: str, second: str) -> IntervalInfo:
    try:
        first_minutes = _clock_to_minutes(first)
        second_minutes = _clock_to_minutes(second)
        diff = second_minutes - first_minutes
        if diff < 0:
            diff += 24 * 60
        return IntervalInfo(diff)
    except (TypeError, ValueError, IndexError):
        return IntervalInfo(None)


def interval_from_range(value: str) -> IntervalInfo:
    try:
        start, end = str(value).strip().rstrip(":").split("-", 1)
        start_minutes = _clock_to_minutes(start.strip().rstrip(":"))
        end_minutes = _clock_to_minutes(end.strip().rstrip(":"))
        diff = end_minutes - start_minutes
        if diff < 0:
            diff += 24 * 60
        return IntervalInfo(diff)
    except (TypeError, ValueError, IndexError):
        return IntervalInfo(None)


def interval_from_xlsx_date_cell(value: str) -> IntervalInfo:
    try:
        parts = str(value).split(" ")
        start_minutes = _clock_to_minutes(parts[1])
        end_minutes = _clock_to_minutes(parts[3])
        diff = end_minutes - start_minutes
        if diff < 0:
            diff += 24 * 60
        return IntervalInfo(diff)
    except (TypeError, ValueError, IndexError):
        return IntervalInfo(None)


def timestamp_from_xlsx_date_cell(value: object) -> datetime | None:
    """Return the start timestamp from `dd.mm.yyyy HH:MM - HH:MM`."""
    text = str(value).strip()
    parts = text.split()
    if len(parts) < 2:
        return None

    date = _parse_date(parts[0])
    if date is None:
        return None

    try:
        minutes = _clock_to_minutes(parts[1])
    except (TypeError, ValueError):
        return None
    return date + timedelta(minutes=minutes)


def timestamp_from_txt_range(date_value: object, range_value: object) -> datetime | None:
    """Return the interval start from a TXT date and `HH:MM-HH:MM` range."""
    date = _parse_date(date_value)
    if date is None:
        return None

    try:
        start, _ = str(range_value).strip().rstrip(":").split("-", 1)
        minutes = _clock_to_minutes(start.strip().rstrip(":"))
    except (TypeError, ValueError):
        return None
    return date + timedelta(minutes=minutes)


def timestamp_from_html_end_time(
    date_value: object,
    end_time_value: object,
    interval: IntervalInfo,
) -> datetime | None:
    """Normalize HTML's interval-end clock to the interval start.

    Meter HTML reports commonly store `01:00` for the 00:00-01:00 interval and
    `00:00` for the last interval of the same reported day.  Using the interval
    start gives a monotonically increasing timeline and keeps the last interval
    of a month inside that month.
    """
    if interval.minutes is None or interval.minutes <= 0:
        return None

    date = _parse_date(date_value)
    if date is None:
        return None

    try:
        end_minutes = _clock_to_minutes(end_time_value)
    except (TypeError, ValueError):
        return None

    # 00:00 in these reports means the end of the reported day (24:00).
    if end_minutes == 0:
        end_minutes = 24 * 60

    return date + timedelta(minutes=end_minutes - interval.minutes)


def _parse_date(value: object) -> datetime | None:
    text = str(value).strip().split(" ")[0]
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _clock_to_minutes(value: object) -> int:
    hour, minute = map(int, str(value).strip().split(":"))
    if hour == 24 and minute == 0:
        return 24 * 60
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Некорректное время: {value}")
    return hour * 60 + minute
