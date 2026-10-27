from datetime import date

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Response,
    status,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import Base, engine, get_db


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Market Lens",
    description=(
        "A local market-intelligence and analytical "
        "tracking application."
    ),
    version="0.1.0",
)


def get_asset_or_404(
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


@app.get("/")
def read_root():
    return {
        "application": "Market Lens",
        "status": "operational",
        "version": "0.1.0",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post(
    "/assets",
    response_model=schemas.MarketAssetResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_asset(
    asset_data: schemas.MarketAssetCreate,
    database: Session = Depends(get_db),
):
    asset = models.MarketAsset(
        **asset_data.model_dump()
    )

    database.add(asset)

    try:
        database.commit()
        database.refresh(asset)
    except IntegrityError:
        database.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A market asset with this symbol "
                "already exists."
            ),
        )

    return asset


@app.get(
    "/assets",
    response_model=list[schemas.MarketAssetResponse],
)
def list_assets(
    include_inactive: bool = False,
    database: Session = Depends(get_db),
):
    statement = select(models.MarketAsset)

    if not include_inactive:
        statement = statement.where(
            models.MarketAsset.is_active.is_(True)
        )

    statement = statement.order_by(
        models.MarketAsset.symbol
    )

    return database.scalars(statement).all()


@app.get(
    "/assets/{asset_id}",
    response_model=schemas.MarketAssetDetailResponse,
)
def get_asset(
    asset_id: int,
    database: Session = Depends(get_db),
):
    return get_asset_or_404(
        asset_id,
        database,
    )


@app.patch(
    "/assets/{asset_id}",
    response_model=schemas.MarketAssetResponse,
)
def update_asset(
    asset_id: int,
    asset_data: schemas.MarketAssetUpdate,
    database: Session = Depends(get_db),
):
    asset = get_asset_or_404(
        asset_id,
        database,
    )

    changes = asset_data.model_dump(
        exclude_unset=True
    )

    required_fields = {
        "symbol",
        "asset_type",
        "currency",
        "is_active",
    }

    for field_name in required_fields:
        if (
            field_name in changes
            and changes[field_name] is None
        ):
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ),
                detail=(
                    f"{field_name} cannot be null."
                ),
            )

    for field_name, value in changes.items():
        setattr(asset, field_name, value)

    try:
        database.commit()
        database.refresh(asset)
    except IntegrityError:
        database.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A market asset with this symbol "
                "already exists."
            ),
        )

    return asset


@app.delete(
    "/assets/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_asset(
    asset_id: int,
    database: Session = Depends(get_db),
):
    asset = get_asset_or_404(
        asset_id,
        database,
    )

    database.delete(asset)
    database.commit()

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )


@app.post(
    "/assets/{asset_id}/prices",
    response_model=schemas.PriceBarResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_price_bar(
    asset_id: int,
    price_data: schemas.PriceBarCreate,
    database: Session = Depends(get_db),
):
    get_asset_or_404(
        asset_id,
        database,
    )

    price_bar = models.PriceBar(
        asset_id=asset_id,
        **price_data.model_dump(),
    )

    database.add(price_bar)

    try:
        database.commit()
        database.refresh(price_bar)
    except IntegrityError:
        database.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A price bar already exists for this "
                "asset and trading date."
            ),
        )

    return price_bar


@app.get(
    "/assets/{asset_id}/prices",
    response_model=list[schemas.PriceBarResponse],
)
def list_price_bars(
    asset_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
    database: Session = Depends(get_db),
):
    get_asset_or_404(
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
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                "start_date cannot be later than "
                "end_date."
            ),
        )

    statement = select(models.PriceBar).where(
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

    statement = statement.order_by(
        models.PriceBar.trading_date.desc()
    )

    return database.scalars(statement).all()


@app.delete(
    "/assets/{asset_id}/prices/{price_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_price_bar(
    asset_id: int,
    price_id: int,
    database: Session = Depends(get_db),
):
    get_asset_or_404(
        asset_id,
        database,
    )

    price_bar = database.get(
        models.PriceBar,
        price_id,
    )

    if (
        price_bar is None
        or price_bar.asset_id != asset_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Price bar not found.",
        )

    database.delete(price_bar)
    database.commit()

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )