import pytest
from fastapi.testclient import TestClient
from sqlalchemy import (
    create_engine,
    delete,
    select,
)
from sqlalchemy.orm import (
    Session,
    sessionmaker,
)
from sqlalchemy.pool import StaticPool

from app import models
from app.database import Base, get_db
from app.integration_auth import (
    ARTEMIS_API_KEY_ENVIRONMENT_VARIABLE,
)
from app.main import app


TEST_API_KEY = (
    "market-lens-artemis-route-test-"
    "0123456789abcdef"
)

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

client = TestClient(app)


def override_get_db():
    database = TestingSessionLocal()

    try:
        yield database
    finally:
        database.close()


@pytest.fixture(autouse=True)
def isolated_integration_database(
    monkeypatch,
):
    previous_override = (
        app.dependency_overrides.get(
            get_db
        )
    )

    app.dependency_overrides[
        get_db
    ] = override_get_db

    monkeypatch.setenv(
        ARTEMIS_API_KEY_ENVIRONMENT_VARIABLE,
        TEST_API_KEY,
    )

    with Session(test_engine) as database:
        database.execute(
            delete(models.PaperPosition)
        )
        database.execute(
            delete(models.MarketSignal)
        )
        database.execute(
            delete(models.PriceBar)
        )
        database.execute(
            delete(models.MarketAsset)
        )
        database.commit()

    yield

    if previous_override is None:
        app.dependency_overrides.pop(
            get_db,
            None,
        )
    else:
        app.dependency_overrides[
            get_db
        ] = previous_override


def integration_headers(
    api_key: str = TEST_API_KEY,
) -> dict[str, str]:
    return {
        "X-Artemis-Key": api_key,
    }


def create_asset(
    *,
    symbol: str = "AAPL",
    is_active: bool = True,
) -> dict:
    response = client.post(
        "/assets",
        json={
            "symbol": symbol,
            "name": f"{symbol} Test Asset",
            "asset_type": "Equity",
            "exchange": "NASDAQ",
            "currency": "USD",
            "is_active": is_active,
        },
    )

    assert response.status_code == 201

    return response.json()


def create_price(
    asset_id: int,
    *,
    trading_date: str,
    close_price: str,
) -> dict:
    response = client.post(
        f"/assets/{asset_id}/prices",
        json={
            "trading_date": trading_date,
            "open_price": close_price,
            "high_price": close_price,
            "low_price": close_price,
            "close_price": close_price,
            "adjusted_close": close_price,
            "volume": 1000,
        },
    )

    assert response.status_code == 201

    return response.json()


def test_integration_requires_api_key():
    response = client.get(
        "/integration/artemis/health"
    )

    assert response.status_code == 401


def test_integration_rejects_incorrect_key():
    response = client.get(
        "/integration/artemis/health",
        headers=integration_headers(
            "incorrect-api-key"
        ),
    )

    assert response.status_code == 401


def test_integration_health_is_read_only():
    response = client.get(
        "/integration/artemis/health",
        headers=integration_headers(),
    )

    assert response.status_code == 200

    assert response.json() == {
        "status": "healthy",
        "application": "Market Lens",
        "integration": "artemis",
        "access": "read-only",
    }


def test_integration_lists_active_assets():
    active_asset = create_asset(
        symbol="AAPL",
        is_active=True,
    )

    create_asset(
        symbol="MSFT",
        is_active=False,
    )

    response = client.get(
        "/integration/artemis/assets",
        headers=integration_headers(),
    )

    assert response.status_code == 200

    assets = response.json()

    assert len(assets) == 1

    assert (
        assets[0]["id"]
        == active_asset["id"]
    )

    assert assets[0]["symbol"] == "AAPL"


def test_integration_reads_price_history():
    asset = create_asset()

    create_price(
        asset["id"],
        trading_date="2026-11-01",
        close_price="100.00",
    )

    create_price(
        asset["id"],
        trading_date="2026-11-02",
        close_price="105.00",
    )

    response = client.get(
        (
            "/integration/artemis/assets/"
            f"{asset['id']}/prices"
        ),
        headers=integration_headers(),
    )

    assert response.status_code == 200

    prices = response.json()

    assert len(prices) == 2

    assert (
        prices[0]["trading_date"]
        == "2026-11-02"
    )


def test_integration_reads_analytics():
    asset = create_asset()

    create_price(
        asset["id"],
        trading_date="2026-11-01",
        close_price="100.00",
    )

    create_price(
        asset["id"],
        trading_date="2026-11-02",
        close_price="105.00",
    )

    response = client.get(
        (
            "/integration/artemis/assets/"
            f"{asset['id']}/analytics"
        ),
        headers=integration_headers(),
    )

    assert response.status_code == 200

    result = response.json()

    assert result["asset_id"] == asset["id"]
    assert result["symbol"] == "AAPL"
    assert result["price_bar_count"] == 2
    assert result["latest_close"] == 105.0


def test_signal_read_does_not_trigger_or_commit():
    asset = create_asset()

    signal_response = client.post(
        f"/assets/{asset['id']}/signals",
        json={
            "signal_type": "Watch",
            "target_price": "100.00",
            "trigger_direction": "Above",
            "rationale": "Test threshold",
            "is_active": True,
        },
    )

    assert signal_response.status_code == 201

    signal_data = signal_response.json()
    signal_id = signal_data["id"]

    assert signal_data["is_triggered"] is False
    assert signal_data["triggered_at"] is None

    create_price(
        asset["id"],
        trading_date="2026-11-02",
        close_price="150.00",
    )

    response = client.get(
        (
            "/integration/artemis/assets/"
            f"{asset['id']}/signals"
        ),
        headers=integration_headers(),
    )

    assert response.status_code == 200

    signals = response.json()

    assert len(signals) == 1
    assert signals[0]["is_triggered"] is False
    assert signals[0]["triggered_at"] is None

    with Session(test_engine) as database:
        stored_signal = database.scalar(
            select(models.MarketSignal)
            .where(
                models.MarketSignal.id
                == signal_id
            )
        )

        assert stored_signal is not None
        assert stored_signal.is_triggered is False
        assert stored_signal.triggered_at is None


def test_legacy_integration_exposes_only_get_routes():
    openapi_paths = app.openapi()["paths"]

    integration_paths = {
        path: operations
        for path, operations
        in openapi_paths.items()
        if path.startswith(
            "/integration/artemis"
        ) and not path.startswith("/integration/artemis/automation/")
    }

    assert integration_paths

    http_methods = {
        "get",
        "put",
        "post",
        "delete",
        "patch",
        "options",
        "head",
        "trace",
    }

    for operations in integration_paths.values():
        exposed_methods = (
            set(operations)
            & http_methods
        )

        assert exposed_methods == {"get"}

def test_automation_writes_are_limited_to_research_operations():
    paths=app.openapi()["paths"]
    writes={path for path, operations in paths.items() if path.startswith("/integration/artemis/automation/") and "post" in operations}
    assert writes == {
        "/integration/artemis/automation/track",
        "/integration/artemis/automation/assets/{asset_id}/refresh",
        "/integration/artemis/automation/assets/{asset_id}/research",
    }
    assert not any(method in operations for path, operations in paths.items() if path.startswith("/integration/artemis/automation/") for method in ("delete","patch","put"))
