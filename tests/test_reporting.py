import csv
from decimal import Decimal
from io import StringIO

from app.reporting import (
    build_portfolio_csv,
    build_portfolio_html,
    format_decimal,
    gain_loss_class,
)


def build_sample_summary() -> dict:
    return {
        "open_position_count": 1,
        "closed_position_count": 1,
        "total_position_count": 2,
        "entry_value": Decimal("200.00"),
        "market_value": Decimal("210.00"),
        "unrealized_gain_loss": Decimal("10.00"),
        "realized_gain_loss": Decimal("-5.00"),
        "assets": [
            {
                "asset_id": 1,
                "symbol": "AAPL",
                "asset_name": "Apple Inc.",
                "currency": "USD",
                "open_position_count": 1,
                "closed_position_count": 1,
                "entry_value": Decimal("200.00"),
                "market_value": Decimal("210.00"),
                "unrealized_gain_loss": Decimal("10.00"),
                "realized_gain_loss": Decimal("-5.00"),
            }
        ],
        "positions": [
            {
                "id": 1,
                "asset_id": 1,
                "symbol": "AAPL",
                "asset_name": "Apple Inc.",
                "currency": "USD",
                "position_type": "Long",
                "quantity": Decimal("2"),
                "entry_price": Decimal("100"),
                "opened_date": "2026-10-20",
                "notes": "Long-term test position.",
                "exit_price": None,
                "closed_date": None,
                "is_open": True,
                "current_price": Decimal("105"),
                "entry_value": Decimal("200"),
                "market_value": Decimal("210"),
                "unrealized_gain_loss": Decimal("10"),
                "realized_gain_loss": None,
                "return_percent": Decimal("5"),
                "created_at": "2026-10-20T12:00:00",
                "updated_at": "2026-10-20T12:00:00",
            },
            {
                "id": 2,
                "asset_id": 1,
                "symbol": "AAPL",
                "asset_name": "Apple Inc.",
                "currency": "USD",
                "position_type": "Long",
                "quantity": Decimal("1"),
                "entry_price": Decimal("100"),
                "opened_date": "2026-10-01",
                "notes": "Closed test position.",
                "exit_price": Decimal("95"),
                "closed_date": "2026-10-10",
                "is_open": False,
                "current_price": Decimal("105"),
                "entry_value": Decimal("100"),
                "market_value": Decimal("95"),
                "unrealized_gain_loss": None,
                "realized_gain_loss": Decimal("-5"),
                "return_percent": Decimal("-5"),
                "created_at": "2026-10-01T12:00:00",
                "updated_at": "2026-10-10T12:00:00",
            },
        ],
    }


def test_format_decimal():
    assert format_decimal(
        Decimal("12.345")
    ) == "12.34"

    assert format_decimal("10") == "10.00"
    assert format_decimal(None) == ""


def test_gain_loss_class():
    assert gain_loss_class("10") == "positive"
    assert gain_loss_class("-10") == "negative"
    assert gain_loss_class("0") == "neutral"
    assert gain_loss_class(None) == "neutral"


def test_build_portfolio_csv():
    csv_text = build_portfolio_csv(
        build_sample_summary()
    )

    rows = list(
        csv.reader(
            StringIO(csv_text)
        )
    )

    assert rows[0][0] == "Symbol"
    assert rows[0][-1] == "Notes"

    assert len(rows) == 3

    assert rows[1][0] == "AAPL"
    assert rows[1][4] == "Open"
    assert rows[1][5] == "2.00"
    assert rows[1][13] == "10.00"

    assert rows[2][4] == "Closed"
    assert rows[2][8] == "95.00"
    assert rows[2][14] == "-5.00"


def test_build_portfolio_html():
    html = build_portfolio_html(
        build_sample_summary()
    )

    assert "<!DOCTYPE html>" in html
    assert "Market Lens Portfolio Report" in html
    assert "Portfolio by Asset" in html
    assert "Consolidated Position Register" in html

    assert "AAPL" in html
    assert "Apple Inc." in html
    assert "Long-term test position." not in html

    assert 'class="positive"' in html
    assert 'class="negative"' in html


def test_html_report_escapes_asset_content():
    summary = build_sample_summary()

    summary["assets"][0][
        "asset_name"
    ] = "<script>alert('test')</script>"

    html = build_portfolio_html(summary)

    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html