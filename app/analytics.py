from __future__ import annotations

from math import sqrt
from statistics import mean, stdev
from typing import Iterable, Protocol


TRADING_DAYS_PER_YEAR = 252


class PriceBarLike(Protocol):
    close_price: object


def extract_closing_prices(
    price_bars: Iterable[PriceBarLike],
) -> list[float]:
    """Return valid closing prices in the supplied order."""
    closing_prices: list[float] = []

    for price_bar in price_bars:
        close_price = getattr(
            price_bar,
            "close_price",
            None,
        )

        if close_price is None:
            continue

        numeric_price = float(close_price)

        if numeric_price > 0:
            closing_prices.append(numeric_price)

    return closing_prices


def calculate_daily_change(
    closing_prices: list[float],
) -> float | None:
    """Calculate the percentage change between the last two prices."""
    if len(closing_prices) < 2:
        return None

    previous_close = closing_prices[-2]
    latest_close = closing_prices[-1]

    if previous_close == 0:
        return None

    return (
        (latest_close - previous_close)
        / previous_close
    ) * 100


def calculate_total_return(
    closing_prices: list[float],
) -> float | None:
    """Calculate percentage return across the entire price series."""
    if len(closing_prices) < 2:
        return None

    first_close = closing_prices[0]
    latest_close = closing_prices[-1]

    if first_close == 0:
        return None

    return (
        (latest_close - first_close)
        / first_close
    ) * 100


def calculate_moving_average(
    closing_prices: list[float],
    period: int,
) -> float | None:
    """Calculate a simple moving average for the requested period."""
    if period <= 0:
        raise ValueError(
            "Moving-average period must be greater than zero."
        )

    if len(closing_prices) < period:
        return None

    return mean(closing_prices[-period:])


def calculate_daily_returns(
    closing_prices: list[float],
) -> list[float]:
    """Calculate decimal daily returns for a price series."""
    daily_returns: list[float] = []

    for index in range(
        1,
        len(closing_prices),
    ):
        previous_close = closing_prices[index - 1]
        current_close = closing_prices[index]

        if previous_close == 0:
            continue

        daily_returns.append(
            (current_close - previous_close)
            / previous_close
        )

    return daily_returns


def calculate_annualized_volatility(
    closing_prices: list[float],
) -> float | None:
    """
    Calculate annualized historical volatility as a percentage.

    At least three closing prices are required because sample
    standard deviation needs at least two daily returns.
    """
    daily_returns = calculate_daily_returns(
        closing_prices
    )

    if len(daily_returns) < 2:
        return None

    return (
        stdev(daily_returns)
        * sqrt(TRADING_DAYS_PER_YEAR)
        * 100
    )


def classify_trend(
    latest_close: float | None,
    moving_average_20: float | None,
    moving_average_50: float | None,
) -> str:
    """Classify the available price trend."""
    if latest_close is None:
        return "Insufficient Data"

    if moving_average_20 is None:
        return "Insufficient Data"

    if moving_average_50 is None:
        if latest_close > moving_average_20:
            return "Short-Term Bullish"

        if latest_close < moving_average_20:
            return "Short-Term Bearish"

        return "Short-Term Neutral"

    if (
        latest_close > moving_average_20
        and moving_average_20 > moving_average_50
    ):
        return "Bullish"

    if (
        latest_close < moving_average_20
        and moving_average_20 < moving_average_50
    ):
        return "Bearish"

    if latest_close > moving_average_50:
        return "Moderately Bullish"

    if latest_close < moving_average_50:
        return "Moderately Bearish"

    return "Neutral"


def build_market_analytics(
    price_bars: Iterable[PriceBarLike],
) -> dict[str, float | int | str | None]:
    """Build a complete analytical summary from chronological bars."""
    closing_prices = extract_closing_prices(
        price_bars
    )

    latest_close = (
        closing_prices[-1]
        if closing_prices
        else None
    )

    moving_average_20 = calculate_moving_average(
        closing_prices,
        20,
    )

    moving_average_50 = calculate_moving_average(
        closing_prices,
        50,
    )

    return {
        "price_bar_count": len(closing_prices),
        "latest_close": latest_close,
        "daily_change_percent": calculate_daily_change(
            closing_prices
        ),
        "total_return_percent": calculate_total_return(
            closing_prices
        ),
        "moving_average_20": moving_average_20,
        "moving_average_50": moving_average_50,
        "annualized_volatility_percent": (
            calculate_annualized_volatility(
                closing_prices
            )
        ),
        "trend": classify_trend(
            latest_close,
            moving_average_20,
            moving_average_50,
        ),
    }