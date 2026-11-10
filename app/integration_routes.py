from datetime import date

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import analytics, models, schemas
from app.database import get_db
from app.integration_auth import (
    require_artemis_api_key,
)


router = APIRouter(
    prefix="/integration/artemis",
    tags=["Artemis Integration"],
    dependencies=[
        Depends(require_artemis_api_key)
    ],
)


def get_integration_asset_or_404(
    asset_id: int,
    database: Session,
) -> models.MarketAsset:
    asset = database.get(
        models.MarketAsset,
        asset_id,
    )

    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Market asset not found.",
        )

    return asset


@router.get("/health")
def read_integration_health():
    return {
        "status": "healthy",
        "application": "Market Lens",
        "integration": "artemis",
        "access": "read-only",
    }


@router.get(
    "/assets",
    response_model=list[
        schemas.MarketAssetResponse
    ],
)
def read_integration_assets(
    include_inactive: bool = False,
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
    database: Session = Depends(get_db),
):
    statement = select(
        models.MarketAsset
    )

    if not include_inactive:
        statement = statement.where(
            models.MarketAsset.is_active.is_(
                True
            )
        )

    statement = (
        statement
        .order_by(
            models.MarketAsset.symbol.asc()
        )
        .limit(limit)
    )

    return database.scalars(
        statement
    ).all()


@router.get(
    "/assets/{asset_id}",
    response_model=(
        schemas.MarketAssetDetailResponse
    ),
)
def read_integration_asset(
    asset_id: int,
    database: Session = Depends(get_db),
):
    return get_integration_asset_or_404(
        asset_id,
        database,
    )


@router.get(
    "/assets/{asset_id}/prices",
    response_model=list[
        schemas.PriceBarResponse
    ],
)
def read_integration_price_bars(
    asset_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = Query(
        default=250,
        ge=1,
        le=2000,
    ),
    database: Session = Depends(get_db),
):
    get_integration_asset_or_404(
        asset_id,
        database,
    )

    if (
        start_date is not None
        and end_date is not None
        and start_date > end_date
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail=(
                "start_date cannot be later than "
                "end_date."
            ),
        )

    statement = select(
        models.PriceBar
    ).where(
        models.PriceBar.asset_id == asset_id
    )

    if start_date is not None:
        statement = statement.where(
            models.PriceBar.trading_date
            >= start_date
        )

    if end_date is not None:
        statement = statement.where(
            models.PriceBar.trading_date
            <= end_date
        )

    statement = (
        statement
        .order_by(
            models.PriceBar.trading_date.desc()
        )
        .limit(limit)
    )

    return database.scalars(
        statement
    ).all()


@router.get(
    "/assets/{asset_id}/analytics",
    response_model=(
        schemas.MarketAnalyticsResponse
    ),
)
def read_integration_analytics(
    asset_id: int,
    database: Session = Depends(get_db),
):
    asset = get_integration_asset_or_404(
        asset_id,
        database,
    )

    price_bars = database.scalars(
        select(models.PriceBar)
        .where(
            models.PriceBar.asset_id
            == asset.id
        )
        .order_by(
            models.PriceBar.trading_date.asc()
        )
    ).all()

    analytics_result = (
        analytics.build_market_analytics(
            price_bars
        )
    )

    return {
        "asset_id": asset.id,
        "symbol": asset.symbol,
        **analytics_result,
    }


@router.get(
    "/assets/{asset_id}/signals",
    response_model=list[
        schemas.MarketSignalResponse
    ],
)
def read_integration_signals(
    asset_id: int,
    include_inactive: bool = True,
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
    database: Session = Depends(get_db),
):
    get_integration_asset_or_404(
        asset_id,
        database,
    )

    statement = select(
        models.MarketSignal
    ).where(
        models.MarketSignal.asset_id
        == asset_id
    )

    if not include_inactive:
        statement = statement.where(
            models.MarketSignal.is_active.is_(
                True
            )
        )

    statement = (
        statement
        .order_by(
            models.MarketSignal.created_at.desc(),
            models.MarketSignal.id.desc(),
        )
        .limit(limit)
    )

    return database.scalars(
        statement
    ).all()