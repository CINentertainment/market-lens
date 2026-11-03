from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Response,
    status,
)
from fastapi.encoders import jsonable_encoder
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
)
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import (
    analytics,
    models,
    reporting,
    schemas,
)
from app.database import Base, engine, get_db
from app.providers import yahoo_finance


Base.metadata.create_all(bind=engine)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


app = FastAPI(
    title="Market Lens",
    description=(
        "A local market-intelligence and analytical "
        "tracking application."
    ),
    version="0.1.0",
)

app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static",
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


@app.get("/dashboard", include_in_schema=False)
def dashboard():
    return FileResponse(
        STATIC_DIR / "index.html"
    )


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
    "/assets/{asset_id}/sync",
    response_model=schemas.MarketDataSyncResponse,
)
def sync_asset_market_data(
    asset_id: int,
    start_date: date,
    end_date: date,
    database: Session = Depends(get_db),
):
    asset = get_asset_or_404(
        asset_id,
        database,
    )

    if start_date > end_date:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail=(
                "start_date cannot be later than "
                "end_date."
            ),
        )

    try:
        received_bars = (
            yahoo_finance.fetch_price_history(
                symbol=asset.symbol,
                start_date=start_date,
                end_date=end_date,
            )
        )
    except yahoo_finance.MarketDataProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error

    created_count = 0
    updated_count = 0

    for bar_data in received_bars:
        statement = select(
            models.PriceBar
        ).where(
            models.PriceBar.asset_id == asset_id,
            models.PriceBar.trading_date
            == bar_data.trading_date,
        )

        existing_bar = database.scalar(statement)
        bar_values = bar_data.model_dump()

        if existing_bar is None:
            database.add(
                models.PriceBar(
                    asset_id=asset_id,
                    **bar_values,
                )
            )

            created_count += 1
        else:
            for field_name, value in (
                bar_values.items()
            ):
                setattr(
                    existing_bar,
                    field_name,
                    value,
                )

            updated_count += 1

    database.commit()

    return schemas.MarketDataSyncResponse(
        asset_id=asset.id,
        symbol=asset.symbol,
        start_date=start_date,
        end_date=end_date,
        received_count=len(received_bars),
        created_count=created_count,
        updated_count=updated_count,
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
@app.get(
    "/assets/{asset_id}/analytics",
    response_model=schemas.MarketAnalyticsResponse,
)
def get_asset_analytics(
    asset_id: int,
    database: Session = Depends(get_db),
):
    asset = get_asset_or_404(
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
def get_market_signal_or_404(
    asset_id: int,
    signal_id: int,
    database: Session,
) -> models.MarketSignal:
    signal = database.get(
        models.MarketSignal,
        signal_id,
    )

    if (
        signal is None
        or signal.asset_id != asset_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Market signal not found.",
        )

    return signal


def get_latest_price_bar(
    asset_id: int,
    database: Session,
) -> models.PriceBar | None:
    return database.scalar(
        select(models.PriceBar)
        .where(
            models.PriceBar.asset_id
            == asset_id
        )
        .order_by(
            models.PriceBar.trading_date.desc()
        )
        .limit(1)
    )


def evaluate_market_signal(
    signal: models.MarketSignal,
    latest_price_bar: models.PriceBar | None,
) -> bool:
    if (
        not signal.is_active
        or signal.is_triggered
        or signal.target_price is None
        or signal.trigger_direction is None
        or latest_price_bar is None
    ):
        return False

    current_price = (
        latest_price_bar.close_price
    )

    should_trigger = (
        signal.trigger_direction == "Above"
        and current_price
        >= signal.target_price
    ) or (
        signal.trigger_direction == "Below"
        and current_price
        <= signal.target_price
    )

    if not should_trigger:
        return False

    signal.is_triggered = True
    signal.triggered_at = datetime.utcnow()

    return True


def validate_signal_trigger_pair(
    target_price,
    trigger_direction,
) -> None:
    has_target_price = (
        target_price is not None
    )

    has_trigger_direction = (
        trigger_direction is not None
    )

    if (
        has_target_price
        != has_trigger_direction
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                "Target price and trigger direction "
                "must be provided together."
            ),
        )


@app.post(
    "/assets/{asset_id}/signals",
    response_model=schemas.MarketSignalResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_market_signal(
    asset_id: int,
    signal_data: schemas.MarketSignalCreate,
    database: Session = Depends(get_db),
):
    get_asset_or_404(
        asset_id,
        database,
    )

    signal = models.MarketSignal(
        asset_id=asset_id,
        **signal_data.model_dump(),
    )

    latest_price_bar = get_latest_price_bar(
        asset_id,
        database,
    )

    evaluate_market_signal(
        signal,
        latest_price_bar,
    )

    database.add(signal)
    database.commit()
    database.refresh(signal)

    return signal


@app.get(
    "/assets/{asset_id}/signals",
    response_model=list[
        schemas.MarketSignalResponse
    ],
)
def list_market_signals(
    asset_id: int,
    include_inactive: bool = True,
    database: Session = Depends(get_db),
):
    get_asset_or_404(
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
            models.MarketSignal.is_active
            .is_(True)
        )

    statement = statement.order_by(
        models.MarketSignal.created_at.desc(),
        models.MarketSignal.id.desc(),
    )

    signals = database.scalars(
        statement
    ).all()

    latest_price_bar = get_latest_price_bar(
        asset_id,
        database,
    )

    signal_was_triggered = False

    for signal in signals:
        if evaluate_market_signal(
            signal,
            latest_price_bar,
        ):
            signal_was_triggered = True

    if signal_was_triggered:
        database.commit()

        for signal in signals:
            database.refresh(signal)

    return signals


@app.get(
    "/assets/{asset_id}/signals/{signal_id}",
    response_model=schemas.MarketSignalResponse,
)
def get_market_signal(
    asset_id: int,
    signal_id: int,
    database: Session = Depends(get_db),
):
    get_asset_or_404(
        asset_id,
        database,
    )

    signal = get_market_signal_or_404(
        asset_id,
        signal_id,
        database,
    )

    latest_price_bar = get_latest_price_bar(
        asset_id,
        database,
    )

    if evaluate_market_signal(
        signal,
        latest_price_bar,
    ):
        database.commit()
        database.refresh(signal)

    return signal


@app.patch(
    "/assets/{asset_id}/signals/{signal_id}",
    response_model=schemas.MarketSignalResponse,
)
def update_market_signal(
    asset_id: int,
    signal_id: int,
    signal_data: schemas.MarketSignalUpdate,
    database: Session = Depends(get_db),
):
    get_asset_or_404(
        asset_id,
        database,
    )

    signal = get_market_signal_or_404(
        asset_id,
        signal_id,
        database,
    )

    updates = signal_data.model_dump(
        exclude_unset=True
    )

    if (
        "signal_type" in updates
        and updates["signal_type"] is None
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail="signal_type cannot be null.",
        )

    if (
        "is_active" in updates
        and updates["is_active"] is None
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail="is_active cannot be null.",
        )

    updated_target_price = updates.get(
        "target_price",
        signal.target_price,
    )

    updated_trigger_direction = updates.get(
        "trigger_direction",
        signal.trigger_direction,
    )

    validate_signal_trigger_pair(
        updated_target_price,
        updated_trigger_direction,
    )

    trigger_configuration_changed = (
        "target_price" in updates
        or "trigger_direction" in updates
    )

    for field_name, value in updates.items():
        setattr(
            signal,
            field_name,
            value,
        )

    if trigger_configuration_changed:
        signal.is_triggered = False
        signal.triggered_at = None

    latest_price_bar = get_latest_price_bar(
        asset_id,
        database,
    )

    evaluate_market_signal(
        signal,
        latest_price_bar,
    )

    database.commit()
    database.refresh(signal)

    return signal


@app.delete(
    "/assets/{asset_id}/signals/{signal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_market_signal(
    asset_id: int,
    signal_id: int,
    database: Session = Depends(get_db),
):
    get_asset_or_404(
        asset_id,
        database,
    )

    signal = get_market_signal_or_404(
        asset_id,
        signal_id,
        database,
    )

    database.delete(signal)
    database.commit()

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )
def get_paper_position_or_404(
    asset_id: int,
    position_id: int,
    database: Session,
) -> models.PaperPosition:
    position = database.get(
        models.PaperPosition,
        position_id,
    )

    if (
        position is None
        or position.asset_id != asset_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper position not found.",
        )

    return position


def build_paper_position_response(
    position: models.PaperPosition,
    database: Session,
) -> dict:
    quantity = Decimal(position.quantity)
    entry_price = Decimal(position.entry_price)

    entry_value = quantity * entry_price

    latest_price_bar = get_latest_price_bar(
        position.asset_id,
        database,
    )

    current_price = (
        Decimal(latest_price_bar.close_price)
        if latest_price_bar is not None
        else None
    )

    market_value = None
    unrealized_gain_loss = None
    realized_gain_loss = None
    return_percent = None

    if position.is_open and current_price is not None:
        market_value = quantity * current_price

        if position.position_type == "Short":
            unrealized_gain_loss = (
                entry_price - current_price
            ) * quantity
        else:
            unrealized_gain_loss = (
                current_price - entry_price
            ) * quantity

        if entry_value != 0:
            return_percent = (
                unrealized_gain_loss
                / entry_value
                * Decimal("100")
            )

    if (
        not position.is_open
        and position.exit_price is not None
    ):
        exit_price = Decimal(position.exit_price)

        if position.position_type == "Short":
            realized_gain_loss = (
                entry_price - exit_price
            ) * quantity
        else:
            realized_gain_loss = (
                exit_price - entry_price
            ) * quantity

        if entry_value != 0:
            return_percent = (
                realized_gain_loss
                / entry_value
                * Decimal("100")
            )

    return {
        "id": position.id,
        "asset_id": position.asset_id,
        "position_type": position.position_type,
        "quantity": position.quantity,
        "entry_price": position.entry_price,
        "opened_date": position.opened_date,
        "exit_price": position.exit_price,
        "closed_date": position.closed_date,
        "notes": position.notes,
        "is_open": position.is_open,
        "current_price": current_price,
        "entry_value": entry_value,
        "market_value": market_value,
        "unrealized_gain_loss": unrealized_gain_loss,
        "realized_gain_loss": realized_gain_loss,
        "return_percent": return_percent,
        "created_at": position.created_at,
        "updated_at": position.updated_at,
    }


@app.post(
    "/assets/{asset_id}/positions",
    response_model=schemas.PaperPositionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_paper_position(
    asset_id: int,
    position_data: schemas.PaperPositionCreate,
    database: Session = Depends(get_db),
):
    get_asset_or_404(
        asset_id,
        database,
    )

    position = models.PaperPosition(
        asset_id=asset_id,
        **position_data.model_dump(),
    )

    database.add(position)
    database.commit()
    database.refresh(position)

    return build_paper_position_response(
        position,
        database,
    )


@app.get(
    "/assets/{asset_id}/positions",
    response_model=list[
        schemas.PaperPositionResponse
    ],
)
def list_paper_positions(
    asset_id: int,
    include_closed: bool = True,
    database: Session = Depends(get_db),
):
    get_asset_or_404(
        asset_id,
        database,
    )

    statement = select(
        models.PaperPosition
    ).where(
        models.PaperPosition.asset_id == asset_id
    )

    if not include_closed:
        statement = statement.where(
            models.PaperPosition.is_open.is_(True)
        )

    statement = statement.order_by(
        models.PaperPosition.opened_date.desc(),
        models.PaperPosition.id.desc(),
    )

    positions = database.scalars(statement).all()

    return [
        build_paper_position_response(
            position,
            database,
        )
        for position in positions
    ]


@app.get(
    (
        "/assets/{asset_id}"
        "/positions/{position_id}"
    ),
    response_model=schemas.PaperPositionResponse,
)
def get_paper_position(
    asset_id: int,
    position_id: int,
    database: Session = Depends(get_db),
):
    get_asset_or_404(
        asset_id,
        database,
    )

    position = get_paper_position_or_404(
        asset_id,
        position_id,
        database,
    )

    return build_paper_position_response(
        position,
        database,
    )


@app.patch(
    (
        "/assets/{asset_id}"
        "/positions/{position_id}"
    ),
    response_model=schemas.PaperPositionResponse,
)
def update_paper_position(
    asset_id: int,
    position_id: int,
    position_data: schemas.PaperPositionUpdate,
    database: Session = Depends(get_db),
):
    get_asset_or_404(
        asset_id,
        database,
    )

    position = get_paper_position_or_404(
        asset_id,
        position_id,
        database,
    )

    if not position.is_open:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Closed paper positions cannot "
                "be updated."
            ),
        )

    updates = position_data.model_dump(
        exclude_unset=True
    )

    required_fields = {
        "position_type",
        "quantity",
        "entry_price",
        "opened_date",
    }

    for field_name, value in updates.items():
        if (
            field_name in required_fields
            and value is None
        ):
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ),
                detail=(
                    f"{field_name} cannot be null."
                ),
            )

        setattr(
            position,
            field_name,
            value,
        )

    database.commit()
    database.refresh(position)

    return build_paper_position_response(
        position,
        database,
    )


@app.post(
    (
        "/assets/{asset_id}"
        "/positions/{position_id}/close"
    ),
    response_model=schemas.PaperPositionResponse,
)
def close_paper_position(
    asset_id: int,
    position_id: int,
    close_data: schemas.PaperPositionClose,
    database: Session = Depends(get_db),
):
    get_asset_or_404(
        asset_id,
        database,
    )

    position = get_paper_position_or_404(
        asset_id,
        position_id,
        database,
    )

    if not position.is_open:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Paper position is already closed.",
        )

    if close_data.closed_date < position.opened_date:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                "closed_date cannot be earlier than "
                "opened_date."
            ),
        )

    position.exit_price = close_data.exit_price
    position.closed_date = close_data.closed_date
    position.is_open = False

    database.commit()
    database.refresh(position)

    return build_paper_position_response(
        position,
        database,
    )


@app.delete(
    (
        "/assets/{asset_id}"
        "/positions/{position_id}"
    ),
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_paper_position(
    asset_id: int,
    position_id: int,
    database: Session = Depends(get_db),
):
    get_asset_or_404(
        asset_id,
        database,
    )

    position = get_paper_position_or_404(
        asset_id,
        position_id,
        database,
    )

    database.delete(position)
    database.commit()

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )
@app.get(
    "/portfolio/summary",
    response_model=schemas.PortfolioSummaryResponse,
)
def get_portfolio_summary(
    database: Session = Depends(get_db),
):
    positions = database.scalars(
        select(models.PaperPosition)
        .order_by(
            models.PaperPosition.is_open.desc(),
            models.PaperPosition.opened_date.desc(),
            models.PaperPosition.id.desc(),
        )
    ).all()

    assets = database.scalars(
        select(models.MarketAsset)
    ).all()

    assets_by_id = {
        asset.id: asset
        for asset in assets
    }

    open_position_count = 0
    closed_position_count = 0

    entry_value = Decimal("0")
    market_value = Decimal("0")
    unrealized_gain_loss = Decimal("0")
    realized_gain_loss = Decimal("0")

    asset_summaries: dict[int, dict] = {}
    portfolio_positions: list[dict] = []

    for position in positions:
        asset = assets_by_id.get(position.asset_id)

        if asset is None:
            continue

        position_response = (
            build_paper_position_response(
                position,
                database,
            )
        )

        portfolio_positions.append(
            {
                **position_response,
                "symbol": asset.symbol,
                "asset_name": asset.name,
                "currency": asset.currency,
            }
        )

        if asset.id not in asset_summaries:
            asset_summaries[asset.id] = {
                "asset_id": asset.id,
                "symbol": asset.symbol,
                "asset_name": asset.name,
                "currency": asset.currency,
                "open_position_count": 0,
                "closed_position_count": 0,
                "entry_value": Decimal("0"),
                "market_value": Decimal("0"),
                "unrealized_gain_loss": Decimal("0"),
                "realized_gain_loss": Decimal("0"),
            }

        asset_summary = asset_summaries[asset.id]

        if position.is_open:
            open_position_count += 1
            asset_summary[
                "open_position_count"
            ] += 1

            position_entry_value = Decimal(
                position_response["entry_value"]
            )

            position_market_value = Decimal(
                position_response["market_value"]
                or 0
            )

            position_unrealized = Decimal(
                position_response[
                    "unrealized_gain_loss"
                ]
                or 0
            )

            entry_value += position_entry_value
            market_value += position_market_value
            unrealized_gain_loss += (
                position_unrealized
            )

            asset_summary[
                "entry_value"
            ] += position_entry_value

            asset_summary[
                "market_value"
            ] += position_market_value

            asset_summary[
                "unrealized_gain_loss"
            ] += position_unrealized
        else:
            closed_position_count += 1
            asset_summary[
                "closed_position_count"
            ] += 1

            position_realized = Decimal(
                position_response[
                    "realized_gain_loss"
                ]
                or 0
            )

            realized_gain_loss += position_realized

            asset_summary[
                "realized_gain_loss"
            ] += position_realized

    ordered_asset_summaries = sorted(
        asset_summaries.values(),
        key=lambda summary: summary["symbol"],
    )

    return {
        "open_position_count": open_position_count,
        "closed_position_count": (
            closed_position_count
        ),
        "total_position_count": len(
            portfolio_positions
        ),
        "entry_value": entry_value,
        "market_value": market_value,
        "unrealized_gain_loss": (
            unrealized_gain_loss
        ),
        "realized_gain_loss": realized_gain_loss,
        "assets": ordered_asset_summaries,
        "positions": portfolio_positions,
    }
@app.get(
    "/portfolio/export.json",
    include_in_schema=False,
)
def export_portfolio_json(
    database: Session = Depends(get_db),
):
    summary = get_portfolio_summary(database)

    return JSONResponse(
        content=jsonable_encoder(summary),
        headers={
            "Content-Disposition": (
                "attachment; "
                'filename="market-lens-portfolio.json"'
            ),
        },
    )


@app.get(
    "/portfolio/export.csv",
    include_in_schema=False,
)
def export_portfolio_csv(
    database: Session = Depends(get_db),
):
    summary = get_portfolio_summary(database)

    csv_content = reporting.build_portfolio_csv(
        summary
    )

    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                "attachment; "
                'filename="market-lens-portfolio.csv"'
            ),
        },
    )


@app.get(
    "/portfolio/report",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def view_portfolio_report(
    database: Session = Depends(get_db),
):
    summary = get_portfolio_summary(database)

    html_content = reporting.build_portfolio_html(
        summary
    )

    return HTMLResponse(
        content=html_content,
        headers={
            "Content-Disposition": (
                "inline; "
                'filename="market-lens-portfolio-report.html"'
            ),
        },
    )