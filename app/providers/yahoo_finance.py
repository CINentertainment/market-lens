from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

import pandas as pd
import yfinance as yf

from app import schemas


PRICE_PRECISION = Decimal("0.000001")


class MarketDataProviderError(Exception):
    pass


def normalize_price(value: float) -> Decimal:
    return Decimal(str(value)).quantize(
        PRICE_PRECISION,
        rounding=ROUND_HALF_UP,
    )


def fetch_price_history(
    symbol: str,
    start_date: date,
    end_date: date,
) -> list[schemas.PriceBarCreate]:
    if start_date > end_date:
        raise MarketDataProviderError(
            "Start date cannot be later than end date."
        )

    normalized_symbol = symbol.strip().upper()

    try:
        ticker = yf.Ticker(normalized_symbol)

        history = ticker.history(
            start=start_date.isoformat(),
            end=(
                end_date + timedelta(days=1)
            ).isoformat(),
            auto_adjust=False,
            actions=False,
        )
    except Exception as error:
        raise MarketDataProviderError(
            "The market-data provider request failed."
        ) from error

    if history.empty:
        raise MarketDataProviderError(
            (
                "No market data was returned for "
                f"{normalized_symbol}."
            )
        )

    price_bars = []

    for timestamp, row in history.iterrows():
        required_values = [
            row.get("Open"),
            row.get("High"),
            row.get("Low"),
            row.get("Close"),
        ]

        if any(
            value is None or pd.isna(value)
            for value in required_values
        ):
            continue

        adjusted_value = row.get("Adj Close")
        volume_value = row.get("Volume")

        adjusted_close = None

        if (
            adjusted_value is not None
            and not pd.isna(adjusted_value)
        ):
            adjusted_close = normalize_price(
                float(adjusted_value)
            )

        volume = None

        if (
            volume_value is not None
            and not pd.isna(volume_value)
        ):
            volume = int(volume_value)

        price_bars.append(
            schemas.PriceBarCreate(
                trading_date=timestamp.date(),
                open_price=normalize_price(
                    float(row["Open"])
                ),
                high_price=normalize_price(
                    float(row["High"])
                ),
                low_price=normalize_price(
                    float(row["Low"])
                ),
                close_price=normalize_price(
                    float(row["Close"])
                ),
                adjusted_close=adjusted_close,
                volume=volume,
            )
        )

    if not price_bars:
        raise MarketDataProviderError(
            (
                "The provider response did not contain "
                "usable price data."
            )
        )

    return price_bars