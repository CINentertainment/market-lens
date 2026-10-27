from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MarketAsset(Base):
    __tablename__ = "market_assets"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    symbol: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )

    name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    asset_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Equity",
    )

    exchange: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="USD",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    price_bars: Mapped[list["PriceBar"]] = relationship(
        back_populates="asset",
        cascade="all, delete-orphan",
    )


class PriceBar(Base):
    __tablename__ = "price_bars"
    __table_args__ = (
        UniqueConstraint(
            "asset_id",
            "trading_date",
            name="uq_price_bar_asset_date",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    asset_id: Mapped[int] = mapped_column(
        ForeignKey(
            "market_assets.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    trading_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    open_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 6),
        nullable=False,
    )

    high_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 6),
        nullable=False,
    )

    low_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 6),
        nullable=False,
    )

    close_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 6),
        nullable=False,
    )

    adjusted_close: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 6),
        nullable=True,
    )

    volume: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    asset: Mapped["MarketAsset"] = relationship(
        back_populates="price_bars",
    )