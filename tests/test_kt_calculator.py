from meter_converter.domain import DataType, IntervalInfo
from meter_converter.services.kt_calculator import KtCalculator


def test_half_hour_p_plus_averages_pair_then_applies_kt():
    result = KtCalculator().calculate(
        [10, 14, 20, 24], IntervalInfo(30), DataType.P_PLUS, kt=2
    )
    assert result == [24, 44]


def test_half_hour_a_plus_sums_pair_then_applies_kt():
    result = KtCalculator().calculate(
        [10, 14], IntervalInfo(30), DataType.A_PLUS, kt=2
    )
    assert result == [48]


def test_hourly_multiplies_each_value():
    result = KtCalculator().calculate(
        [10, None, 5], IntervalInfo(60), DataType.P_PLUS, kt=3
    )
    assert result == [30, None, 15]
