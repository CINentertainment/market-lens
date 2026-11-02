from decimal import Decimal
from types import SimpleNamespace

import pytest

from app import analytics


def make_price_bars(
    closing_prices: list[float],
):
    return [
        SimpleNamespace(
            close_price=Decimal(str(price))
        )
        for price in closing_prices
    ]


def test_extract_closing_prices():
    price_bars = make_price_bars(
        [100.00, 102.50, 105.00]
    )

    result = analytics.extract_closing_prices(
        price_bars
    )

    assert result == [
        100.00,
        102.50,
        105.00,
    ]


def test_extract_closing_prices_ignores_invalid_values():
    price_bars = [
        SimpleNamespace(
            close_price=Decimal("100.00")
        ),
        SimpleNamespace(
            close_price=None
        ),
        SimpleNamespace(
            close_price=Decimal("0")
        ),
        SimpleNamespace(
            close_price=Decimal("-5.00")
        ),
        SimpleNamespace(
            close_price=Decimal("105.00")
        ),
    ]

    result = analytics.extract_closing_prices(
        price_bars
    )

    assert result == [
        100.00,
        105.00,
    ]


def test_calculate_daily_change():
    result = analytics.calculate_daily_change(
        [100.00, 105.00]
    )

    assert result == pytest.approx(5.0)


def test_daily_change_requires_two_prices():
    assert (
        analytics.calculate_daily_change(
            [100.00]
        )
        is None
    )


def test_calculate_total_return():
    result = analytics.calculate_total_return(
        [100.00, 104.00, 110.00]
    )

    assert result == pytest.approx(10.0)


def test_total_return_requires_two_prices():
    assert (
        analytics.calculate_total_return([])
        is None
    )

    assert (
        analytics.calculate_total_return(
            [100.00]
        )
        is None
    )


def test_calculate_moving_average():
    result = analytics.calculate_moving_average(
        [10.00, 20.00, 30.00, 40.00],
        3,
    )

    assert result == pytest.approx(30.0)


def test_moving_average_requires_enough_prices():
    result = analytics.calculate_moving_average(
        [10.00, 20.00],
        3,
    )

    assert result is None


def test_moving_average_rejects_invalid_period():
    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        analytics.calculate_moving_average(
            [10.00, 20.00],
            0,
        )


def test_calculate_daily_returns():
    result = analytics.calculate_daily_returns(
        [100.00, 110.00, 99.00]
    )

    assert result == pytest.approx(
        [0.10, -0.10]
    )


def test_calculate_annualized_volatility():
    result = (
        analytics.calculate_annualized_volatility(
            [100.00, 102.00, 101.00, 105.00]
        )
    )

    assert result is not None
    assert result > 0


def test_volatility_requires_three_prices():
    result = (
        analytics.calculate_annualized_volatility(
            [100.00, 105.00]
        )
    )

    assert result is None


def test_classify_bullish_trend():
    result = analytics.classify_trend(
        latest_close=120.00,
        moving_average_20=110.00,
        moving_average_50=100.00,
    )

    assert result == "Bullish"


def test_classify_bearish_trend():
    result = analytics.classify_trend(
        latest_close=80.00,
        moving_average_20=90.00,
        moving_average_50=100.00,
    )

    assert result == "Bearish"


def test_classify_short_term_trend():
    bullish_result = analytics.classify_trend(
        latest_close=110.00,
        moving_average_20=100.00,
        moving_average_50=None,
    )

    bearish_result = analytics.classify_trend(
        latest_close=90.00,
        moving_average_20=100.00,
        moving_average_50=None,
    )

    assert bullish_result == "Short-Term Bullish"
    assert bearish_result == "Short-Term Bearish"


def test_classify_trend_with_insufficient_data():
    assert analytics.classify_trend(
        latest_close=None,
        moving_average_20=None,
        moving_average_50=None,
    ) == "Insufficient Data"

    assert analytics.classify_trend(
        latest_close=100.00,
        moving_average_20=None,
        moving_average_50=None,
    ) == "Insufficient Data"


def test_build_market_analytics_with_fifty_prices():
    price_bars = make_price_bars(
        [
            float(price)
            for price in range(100, 150)
        ]
    )

    result = analytics.build_market_analytics(
        price_bars
    )

    assert result["price_bar_count"] == 50
    assert result["latest_close"] == 149.00
    assert result["daily_change_percent"] == (
        pytest.approx(
            ((149.00 - 148.00) / 148.00)
            * 100
        )
    )
    assert result["total_return_percent"] == (
        pytest.approx(49.0)
    )
    assert result["moving_average_20"] == (
        pytest.approx(139.5)
    )
    assert result["moving_average_50"] == (
        pytest.approx(124.5)
    )
    assert (
        result[
            "annualized_volatility_percent"
        ]
        is not None
    )
    assert result["trend"] == "Bullish"


def test_build_market_analytics_with_no_prices():
    result = analytics.build_market_analytics(
        []
    )

    assert result == {
        "price_bar_count": 0,
        "latest_close": None,
        "daily_change_percent": None,
        "total_return_percent": None,
        "moving_average_20": None,
        "moving_average_50": None,
        "annualized_volatility_percent": None,
        "trend": "Insufficient Data",
    }