from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import models, schemas
from app.database import Base, get_db
from app.main import app
from app.providers import yahoo_finance


test_engine = create_engine(
    "sqlite://",
    connect_args={
        "check_same_thread": False,
    },
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    autocommit=False,
)

Base.metadata.create_all(bind=test_engine)


def override_get_db():
    database = TestingSessionLocal()

    try:
        yield database
    finally:
        database.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_database():
    with Session(test_engine) as database:
        database.execute(delete(models.PriceBar))
        database.execute(delete(models.MarketAsset))
        database.commit()

    yield


def create_test_asset(
    symbol: str = "AAPL",
) -> dict:
    response = client.post(
        "/assets",
        json={
            "symbol": symbol,
            "name": "Apple Inc.",
            "asset_type": "Equity",
            "exchange": "NASDAQ",
            "currency": "USD",
            "is_active": True,
        },
    )

    assert response.status_code == 201

    return response.json()


def create_test_price(
    asset_id: int,
    trading_date: str = "2026-10-27",
) -> dict:
    response = client.post(
        f"/assets/{asset_id}/prices",
        json={
            "trading_date": trading_date,
            "open_price": "100.00",
            "high_price": "105.00",
            "low_price": "99.00",
            "close_price": "103.50",
            "adjusted_close": "103.50",
            "volume": 1500000,
        },
    )

    assert response.status_code == 201

    return response.json()


def test_read_root():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "application": "Market Lens",
        "status": "operational",
        "version": "0.1.0",
    }


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy"
    }


def test_openapi_version():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["version"] == (
        "0.1.0"
    )


def test_create_asset():
    response = client.post(
        "/assets",
        json={
            "symbol": "aapl",
            "name": "Apple Inc.",
            "asset_type": "Equity",
            "exchange": "NASDAQ",
            "currency": "usd",
        },
    )

    assert response.status_code == 201

    asset = response.json()

    assert asset["symbol"] == "AAPL"
    assert asset["name"] == "Apple Inc."
    assert asset["currency"] == "USD"
    assert asset["is_active"] is True
    assert asset["id"] > 0


def test_reject_duplicate_symbol():
    create_test_asset()

    response = client.post(
        "/assets",
        json={
            "symbol": "aapl",
            "name": "Duplicate Apple",
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "A market asset with this symbol "
            "already exists."
        )
    }


def test_list_assets():
    create_test_asset("AAPL")
    create_test_asset("MSFT")

    response = client.get("/assets")

    assert response.status_code == 200
    assert [
        asset["symbol"]
        for asset in response.json()
    ] == ["AAPL", "MSFT"]


def test_inactive_assets_hidden_by_default():
    asset = create_test_asset()

    update_response = client.patch(
        f"/assets/{asset['id']}",
        json={
            "is_active": False,
        },
    )

    assert update_response.status_code == 200

    default_response = client.get("/assets")
    all_response = client.get(
        "/assets",
        params={
            "include_inactive": True,
        },
    )

    assert default_response.json() == []
    assert len(all_response.json()) == 1
    assert all_response.json()[0]["is_active"] is False


def test_get_asset():
    created_asset = create_test_asset()

    response = client.get(
        f"/assets/{created_asset['id']}"
    )

    assert response.status_code == 200
    assert response.json()["symbol"] == "AAPL"
    assert response.json()["price_bars"] == []


def test_get_missing_asset():
    response = client.get("/assets/999")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Market asset not found."
    }


def test_update_asset():
    created_asset = create_test_asset()

    response = client.patch(
        f"/assets/{created_asset['id']}",
        json={
            "name": "Apple Incorporated",
            "exchange": "NASDAQ Global Select",
        },
    )

    assert response.status_code == 200
    assert response.json()["name"] == (
        "Apple Incorporated"
    )
    assert response.json()["exchange"] == (
        "NASDAQ Global Select"
    )


def test_reject_null_required_asset_field():
    created_asset = create_test_asset()

    response = client.patch(
        f"/assets/{created_asset['id']}",
        json={
            "symbol": None,
        },
    )

    assert response.status_code == 422


def test_delete_asset():
    created_asset = create_test_asset()

    delete_response = client.delete(
        f"/assets/{created_asset['id']}"
    )

    assert delete_response.status_code == 204

    get_response = client.get(
        f"/assets/{created_asset['id']}"
    )

    assert get_response.status_code == 404


def test_create_price_bar():
    created_asset = create_test_asset()

    price_bar = create_test_price(
        created_asset["id"]
    )

    assert price_bar["asset_id"] == (
        created_asset["id"]
    )
    assert price_bar["trading_date"] == (
        "2026-10-27"
    )
    assert price_bar["volume"] == 1500000


def test_reject_duplicate_price_date():
    created_asset = create_test_asset()

    create_test_price(created_asset["id"])

    response = client.post(
        f"/assets/{created_asset['id']}/prices",
        json={
            "trading_date": "2026-10-27",
            "open_price": "100.00",
            "high_price": "105.00",
            "low_price": "99.00",
            "close_price": "103.50",
            "volume": 1500000,
        },
    )

    assert response.status_code == 409


def test_reject_invalid_price_range():
    created_asset = create_test_asset()

    response = client.post(
        f"/assets/{created_asset['id']}/prices",
        json={
            "trading_date": "2026-10-27",
            "open_price": "100.00",
            "high_price": "95.00",
            "low_price": "99.00",
            "close_price": "103.50",
        },
    )

    assert response.status_code == 422


def test_list_price_bars_by_date_range():
    created_asset = create_test_asset()

    create_test_price(
        created_asset["id"],
        "2026-10-24",
    )

    create_test_price(
        created_asset["id"],
        "2026-10-27",
    )

    response = client.get(
        f"/assets/{created_asset['id']}/prices",
        params={
            "start_date": "2026-10-26",
            "end_date": "2026-10-27",
        },
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["trading_date"] == (
        "2026-10-27"
    )


def test_reject_reversed_date_range():
    created_asset = create_test_asset()

    response = client.get(
        f"/assets/{created_asset['id']}/prices",
        params={
            "start_date": "2026-10-28",
            "end_date": "2026-10-27",
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": (
            "start_date cannot be later than "
            "end_date."
        )
    }


def test_delete_price_bar():
    created_asset = create_test_asset()

    price_bar = create_test_price(
        created_asset["id"]
    )

    response = client.delete(
        (
            f"/assets/{created_asset['id']}"
            f"/prices/{price_bar['id']}"
        )
    )

    assert response.status_code == 204

    list_response = client.get(
        f"/assets/{created_asset['id']}/prices"
    )

    assert list_response.status_code == 200
    assert list_response.json() == []


def test_sync_asset_market_data(monkeypatch):
    asset = create_test_asset()
    asset_id = asset["id"]

    def mock_fetch_price_history(
        symbol: str,
        start_date: date,
        end_date: date,
    ):
        assert symbol == "AAPL"
        assert start_date == date(2026, 10, 26)
        assert end_date == date(2026, 10, 27)

        return [
            schemas.PriceBarCreate(
                trading_date=date(2026, 10, 26),
                open_price=Decimal("268.50"),
                high_price=Decimal("272.00"),
                low_price=Decimal("267.75"),
                close_price=Decimal("271.25"),
                adjusted_close=Decimal("271.25"),
                volume=45200000,
            ),
            schemas.PriceBarCreate(
                trading_date=date(2026, 10, 27),
                open_price=Decimal("271.50"),
                high_price=Decimal("274.25"),
                low_price=Decimal("270.50"),
                close_price=Decimal("273.75"),
                adjusted_close=Decimal("273.75"),
                volume=48100000,
            ),
        ]

    monkeypatch.setattr(
        "app.main.yahoo_finance.fetch_price_history",
        mock_fetch_price_history,
    )

    response = client.post(
        f"/assets/{asset_id}/sync",
        params={
            "start_date": "2026-10-26",
            "end_date": "2026-10-27",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "asset_id": asset_id,
        "symbol": "AAPL",
        "start_date": "2026-10-26",
        "end_date": "2026-10-27",
        "received_count": 2,
        "created_count": 2,
        "updated_count": 0,
    }

    prices_response = client.get(
        f"/assets/{asset_id}/prices"
    )

    assert prices_response.status_code == 200
    assert len(prices_response.json()) == 2


def test_sync_updates_existing_price_bar(monkeypatch):
    asset = create_test_asset()
    asset_id = asset["id"]
    closing_price = Decimal("271.25")

    def mock_fetch_price_history(
        symbol: str,
        start_date: date,
        end_date: date,
    ):
        return [
            schemas.PriceBarCreate(
                trading_date=date(2026, 10, 27),
                open_price=Decimal("268.50"),
                high_price=Decimal("275.00"),
                low_price=Decimal("267.75"),
                close_price=closing_price,
                adjusted_close=closing_price,
                volume=45200000,
            )
        ]

    monkeypatch.setattr(
        "app.main.yahoo_finance.fetch_price_history",
        mock_fetch_price_history,
    )

    first_response = client.post(
        f"/assets/{asset_id}/sync",
        params={
            "start_date": "2026-10-27",
            "end_date": "2026-10-27",
        },
    )

    assert first_response.status_code == 200
    assert first_response.json()["created_count"] == 1
    assert first_response.json()["updated_count"] == 0

    closing_price = Decimal("273.75")

    second_response = client.post(
        f"/assets/{asset_id}/sync",
        params={
            "start_date": "2026-10-27",
            "end_date": "2026-10-27",
        },
    )

    assert second_response.status_code == 200
    assert second_response.json()["created_count"] == 0
    assert second_response.json()["updated_count"] == 1

    prices_response = client.get(
        f"/assets/{asset_id}/prices"
    )

    assert prices_response.status_code == 200

    prices = prices_response.json()

    assert len(prices) == 1
    assert Decimal(prices[0]["close_price"]) == Decimal(
        "273.750000"
    )


def test_sync_handles_market_data_provider_failure(
    monkeypatch,
):
    asset = create_test_asset()

    def mock_fetch_price_history(
        symbol: str,
        start_date: date,
        end_date: date,
    ):
        raise yahoo_finance.MarketDataProviderError(
            "Yahoo Finance is temporarily unavailable."
        )

    monkeypatch.setattr(
        "app.main.yahoo_finance.fetch_price_history",
        mock_fetch_price_history,
    )

    response = client.post(
        f"/assets/{asset['id']}/sync",
        params={
            "start_date": "2026-10-26",
            "end_date": "2026-10-27",
        },
    )

    assert response.status_code == 502
    assert response.json() == {
        "detail": (
            "Yahoo Finance is temporarily unavailable."
        )
    }
def test_sync_rejects_reversed_date_range(monkeypatch):
    asset = create_test_asset()

    def mock_fetch_price_history(
        symbol: str,
        start_date: date,
        end_date: date,
    ):
        pytest.fail(
            "The provider should not be called "
            "for an invalid date range."
        )

    monkeypatch.setattr(
        "app.main.yahoo_finance.fetch_price_history",
        mock_fetch_price_history,
    )

    response = client.post(
        f"/assets/{asset['id']}/sync",
        params={
            "start_date": "2026-10-28",
            "end_date": "2026-10-27",
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": (
            "start_date cannot be later than "
            "end_date."
        )
    }
def test_dashboard():
    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "Market Lens" in response.text
    assert "/static/styles.css" in response.text
    assert "/static/app.js" in response.text