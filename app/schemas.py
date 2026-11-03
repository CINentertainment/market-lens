from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


AssetType = Literal[
    "Equity",
    "ETF",
    "Index",
    "Crypto",
    "Mutual Fund",
    "Other",
]


class MarketAssetBase(BaseModel):
    symbol: str = Field(
        min_length=1,
        max_length=20,
        pattern=r"^[A-Za-z0-9.^=\-]+$",
    )

    name: str | None = Field(
        default=None,
        max_length=200,
    )

    asset_type: AssetType = "Equity"

    exchange: str | None = Field(
        default=None,
        max_length=100,
    )

    currency: str = Field(
        default="USD",
        min_length=1,
        max_length=10,
    )

    is_active: bool = True

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().upper()


class MarketAssetCreate(MarketAssetBase):
    pass


class MarketAssetUpdate(BaseModel):
    symbol: str | None = Field(
        default=None,
        min_length=1,
        max_length=20,
        pattern=r"^[A-Za-z0-9.^=\-]+$",
    )

    name: str | None = Field(
        default=None,
        max_length=200,
    )

    asset_type: AssetType | None = None

    exchange: str | None = Field(
        default=None,
        max_length=100,
    )

    currency: str | None = Field(
        default=None,
        min_length=1,
        max_length=10,
    )

    is_active: bool | None = None

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        return value.strip().upper()

    @field_validator("currency")
    @classmethod
    def normalize_currency(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        return value.strip().upper()


class MarketAssetResponse(MarketAssetBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class PriceBarBase(BaseModel):
    trading_date: date

    open_price: Decimal = Field(
        ge=0,
        decimal_places=6,
    )

    high_price: Decimal = Field(
        ge=0,
        decimal_places=6,
    )

    low_price: Decimal = Field(
        ge=0,
        decimal_places=6,
    )

    close_price: Decimal = Field(
        ge=0,
        decimal_places=6,
    )

    adjusted_close: Decimal | None = Field(
        default=None,
        ge=0,
        decimal_places=6,
    )

    volume: int | None = Field(
        default=None,
        ge=0,
    )

    @model_validator(mode="after")
    def validate_price_range(self) -> Self:
        if self.high_price < self.low_price:
            raise ValueError(
                "High price cannot be lower than low price."
            )

        prices_within_range = (
            self.low_price
            <= self.open_price
            <= self.high_price
            and self.low_price
            <= self.close_price
            <= self.high_price
        )

        if not prices_within_range:
            raise ValueError(
                "Open and close prices must fall within "
                "the daily low and high range."
            )

        return self


class PriceBarCreate(PriceBarBase):
    pass


class PriceBarResponse(PriceBarBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    created_at: datetime


class MarketAssetDetailResponse(MarketAssetResponse):
    price_bars: list[PriceBarResponse] = Field(
        default_factory=list
    )
class MarketDataSyncResponse(BaseModel):
    asset_id: int
    symbol: str
    start_date: date
    end_date: date
    received_count: int = Field(ge=0)
    created_count: int = Field(ge=0)
    updated_count: int = Field(ge=0)
class MarketAnalyticsResponse(BaseModel):
    asset_id: int
    symbol: str
    price_bar_count: int
    latest_close: float | None
    daily_change_percent: float | None
    total_return_percent: float | None
    moving_average_20: float | None
    moving_average_50: float | None
    annualized_volatility_percent: float | None
    trend: str
SignalType = Literal[
    "Watch",
    "Buy",
    "Sell",
    "Review",
]

TriggerDirection = Literal[
    "Above",
    "Below",
]


class MarketSignalBase(BaseModel):
    signal_type: SignalType = "Watch"

    target_price: Decimal | None = Field(
        default=None,
        gt=0,
        decimal_places=6,
    )

    trigger_direction: (
        TriggerDirection | None
    ) = None

    rationale: str | None = Field(
        default=None,
        max_length=2000,
    )

    is_active: bool = True

    @field_validator("rationale")
    @classmethod
    def normalize_rationale(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()

        return normalized_value or None

    @model_validator(mode="after")
    def validate_price_trigger(self) -> Self:
        has_target_price = (
            self.target_price is not None
        )

        has_trigger_direction = (
            self.trigger_direction is not None
        )

        if (
            has_target_price
            != has_trigger_direction
        ):
            raise ValueError(
                "Target price and trigger direction "
                "must be provided together."
            )

        return self


class MarketSignalCreate(MarketSignalBase):
    pass


class MarketSignalUpdate(BaseModel):
    signal_type: SignalType | None = None

    target_price: Decimal | None = Field(
        default=None,
        gt=0,
        decimal_places=6,
    )

    trigger_direction: (
        TriggerDirection | None
    ) = None

    rationale: str | None = Field(
        default=None,
        max_length=2000,
    )

    is_active: bool | None = None

    @field_validator("rationale")
    @classmethod
    def normalize_rationale(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()

        return normalized_value or None


class MarketSignalResponse(MarketSignalBase):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    asset_id: int
    is_triggered: bool
    triggered_at: datetime | None
    created_at: datetime
    updated_at: datetime
PositionType = Literal[
    "Long",
    "Short",
]


class PaperPositionBase(BaseModel):
    position_type: PositionType = "Long"

    quantity: Decimal = Field(
        gt=0,
        decimal_places=6,
    )

    entry_price: Decimal = Field(
        gt=0,
        decimal_places=6,
    )

    opened_date: date

    notes: str | None = Field(
        default=None,
        max_length=2000,
    )

    @field_validator("notes")
    @classmethod
    def normalize_position_notes(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()

        return normalized_value or None


class PaperPositionCreate(PaperPositionBase):
    pass


class PaperPositionUpdate(BaseModel):
    position_type: PositionType | None = None

    quantity: Decimal | None = Field(
        default=None,
        gt=0,
        decimal_places=6,
    )

    entry_price: Decimal | None = Field(
        default=None,
        gt=0,
        decimal_places=6,
    )

    opened_date: date | None = None

    notes: str | None = Field(
        default=None,
        max_length=2000,
    )

    @field_validator("notes")
    @classmethod
    def normalize_updated_position_notes(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()

        return normalized_value or None


class PaperPositionClose(BaseModel):
    exit_price: Decimal = Field(
        gt=0,
        decimal_places=6,
    )

    closed_date: date


class PaperPositionResponse(PaperPositionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int

    exit_price: Decimal | None
    closed_date: date | None
    is_open: bool

    current_price: Decimal | None
    entry_value: Decimal
    market_value: Decimal | None

    unrealized_gain_loss: Decimal | None
    realized_gain_loss: Decimal | None
    return_percent: Decimal | None

    created_at: datetime
    updated_at: datetime