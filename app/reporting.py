import csv
from datetime import datetime
from decimal import Decimal
from html import escape
from io import StringIO


def format_decimal(
    value: Decimal | str | float | int | None,
) -> str:
    if value is None:
        return ""

    return f"{Decimal(str(value)):.2f}"


def build_portfolio_csv(
    summary: dict,
) -> str:
    output = StringIO(newline="")

    writer = csv.writer(output)

    writer.writerow(
        [
            "Symbol",
            "Asset Name",
            "Currency",
            "Position Type",
            "Status",
            "Quantity",
            "Entry Price",
            "Opened Date",
            "Exit Price",
            "Closed Date",
            "Current Price",
            "Entry Value",
            "Market Value",
            "Unrealized Gain/Loss",
            "Realized Gain/Loss",
            "Return Percent",
            "Notes",
        ]
    )

    for position in summary.get(
        "positions",
        [],
    ):
        writer.writerow(
            [
                position.get("symbol", ""),
                position.get("asset_name") or "",
                position.get("currency", ""),
                position.get("position_type", ""),
                (
                    "Open"
                    if position.get("is_open")
                    else "Closed"
                ),
                format_decimal(
                    position.get("quantity")
                ),
                format_decimal(
                    position.get("entry_price")
                ),
                position.get("opened_date", ""),
                format_decimal(
                    position.get("exit_price")
                ),
                position.get("closed_date") or "",
                format_decimal(
                    position.get("current_price")
                ),
                format_decimal(
                    position.get("entry_value")
                ),
                format_decimal(
                    position.get("market_value")
                ),
                format_decimal(
                    position.get(
                        "unrealized_gain_loss"
                    )
                ),
                format_decimal(
                    position.get(
                        "realized_gain_loss"
                    )
                ),
                format_decimal(
                    position.get("return_percent")
                ),
                position.get("notes") or "",
            ]
        )

    return output.getvalue()


def build_metric(
    label: str,
    value: str,
    value_class: str = "",
) -> str:
    class_attribute = (
        f' class="{escape(value_class)}"'
        if value_class
        else ""
    )

    return f"""
        <div class="metric">
            <span>{escape(label)}</span>
            <strong{class_attribute}>
                {escape(value)}
            </strong>
        </div>
    """


def gain_loss_class(
    value: Decimal | str | float | int | None,
) -> str:
    numeric_value = Decimal(str(value or 0))

    if numeric_value > 0:
        return "positive"

    if numeric_value < 0:
        return "negative"

    return "neutral"


def build_portfolio_html(
    summary: dict,
) -> str:
    generated_at = datetime.now().astimezone()

    assets = summary.get("assets", [])
    positions = summary.get("positions", [])

    asset_rows = []

    for asset in assets:
        asset_rows.append(
            f"""
                <tr>
                    <td>
                        <strong>
                            {escape(asset["symbol"])}
                        </strong>
                    </td>
                    <td>
                        {escape(
                            asset.get("asset_name")
                            or "Unnamed asset"
                        )}
                    </td>
                    <td>
                        {asset["open_position_count"]}
                    </td>
                    <td>
                        {asset["closed_position_count"]}
                    </td>
                    <td>
                        {escape(
                            format_decimal(
                                asset["entry_value"]
                            )
                        )}
                    </td>
                    <td>
                        {escape(
                            format_decimal(
                                asset["market_value"]
                            )
                        )}
                    </td>
                    <td class="{gain_loss_class(
                        asset[
                            "unrealized_gain_loss"
                        ]
                    )}">
                        {escape(
                            format_decimal(
                                asset[
                                    "unrealized_gain_loss"
                                ]
                            )
                        )}
                    </td>
                    <td class="{gain_loss_class(
                        asset["realized_gain_loss"]
                    )}">
                        {escape(
                            format_decimal(
                                asset[
                                    "realized_gain_loss"
                                ]
                            )
                        )}
                    </td>
                </tr>
            """
        )

    position_rows = []

    for position in positions:
        gain_loss = (
            position.get(
                "unrealized_gain_loss"
            )
            if position.get("is_open")
            else position.get(
                "realized_gain_loss"
            )
        )

        position_rows.append(
            f"""
                <tr>
                    <td>
                        <strong>
                            {escape(position["symbol"])}
                        </strong>
                    </td>
                    <td>
                        {escape(
                            position["position_type"]
                        )}
                    </td>
                    <td>
                        {
                            "Open"
                            if position["is_open"]
                            else "Closed"
                        }
                    </td>
                    <td>
                        {escape(
                            format_decimal(
                                position["quantity"]
                            )
                        )}
                    </td>
                    <td>
                        {escape(
                            format_decimal(
                                position["entry_price"]
                            )
                        )}
                    </td>
                    <td>
                        {escape(
                            str(
                                position[
                                    "opened_date"
                                ]
                            )
                        )}
                    </td>
                    <td class="{gain_loss_class(
                        gain_loss
                    )}">
                        {escape(
                            format_decimal(gain_loss)
                        )}
                    </td>
                    <td>
                        {escape(
                            format_decimal(
                                position.get(
                                    "return_percent"
                                )
                            )
                        )}
                    </td>
                </tr>
            """
        )

    asset_table = (
        "".join(asset_rows)
        if asset_rows
        else """
            <tr>
                <td colspan="8">
                    No portfolio assets available.
                </td>
            </tr>
        """
    )

    position_table = (
        "".join(position_rows)
        if position_rows
        else """
            <tr>
                <td colspan="8">
                    No paper positions available.
                </td>
            </tr>
        """
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>Market Lens Portfolio Report</title>

    <style>
        :root {{
            color-scheme: dark;
            font-family:
                Inter,
                ui-sans-serif,
                system-ui,
                sans-serif;
        }}

        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            padding: 32px;
            color: #f7f4ff;
            background: #080912;
        }}

        main {{
            width: min(1200px, 100%);
            margin: 0 auto;
        }}

        header {{
            margin-bottom: 24px;
            padding-bottom: 18px;
            border-bottom: 1px solid #30364d;
        }}

        h1,
        h2 {{
            margin-top: 0;
        }}

        h1 {{
            margin-bottom: 5px;
        }}

        h2 {{
            margin-bottom: 14px;
            font-size: 1rem;
        }}

        .subtitle {{
            color: #969fbe;
        }}

        .metrics {{
            display: grid;
            grid-template-columns:
                repeat(3, minmax(0, 1fr));
            gap: 12px;
            margin-bottom: 24px;
        }}

        .metric,
        section {{
            border: 1px solid #30364d;
            border-radius: 12px;
            background: #121421;
        }}

        .metric {{
            padding: 16px;
        }}

        .metric span {{
            display: block;
            margin-bottom: 8px;
            color: #8f9ac1;
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }}

        .metric strong {{
            font-size: 1.05rem;
        }}

        section {{
            margin-bottom: 18px;
            padding: 18px;
        }}

        .table-container {{
            overflow-x: auto;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
        }}

        th,
        td {{
            padding: 10px;
            border-bottom: 1px solid #292f45;
            text-align: left;
            font-size: 0.78rem;
        }}

        th {{
            color: #aab2d0;
            font-size: 0.67rem;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }}

        .positive {{
            color: #76e6d8;
        }}

        .negative {{
            color: #ff7f96;
        }}

        .neutral {{
            color: #b79cff;
        }}

        footer {{
            margin-top: 24px;
            color: #7f89ad;
            font-size: 0.72rem;
            text-align: center;
        }}

        @media print {{
            :root {{
                color-scheme: light;
            }}

            body {{
                padding: 0;
                color: #111827;
                background: #ffffff;
            }}

            .metric,
            section {{
                border-color: #d1d5db;
                background: #ffffff;
            }}

            th,
            td {{
                border-color: #e5e7eb;
            }}

            .subtitle,
            footer,
            .metric span,
            th {{
                color: #4b5563;
            }}

            .positive {{
                color: #047857;
            }}

            .negative {{
                color: #be123c;
            }}

            .neutral {{
                color: #6d28d9;
            }}
        }}

        @media (max-width: 700px) {{
            body {{
                padding: 16px;
            }}

            .metrics {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>

<body>
    <main>
        <header>
            <h1>Market Lens Portfolio Report</h1>

            <div class="subtitle">
                Generated
                {escape(
                    generated_at.strftime(
                        "%B %d, %Y at %I:%M %p %Z"
                    )
                )}
            </div>
        </header>

        <div class="metrics">
            {build_metric(
                "Open Positions",
                str(
                    summary[
                        "open_position_count"
                    ]
                ),
            )}

            {build_metric(
                "Closed Positions",
                str(
                    summary[
                        "closed_position_count"
                    ]
                ),
            )}

            {build_metric(
                "Total Positions",
                str(
                    summary[
                        "total_position_count"
                    ]
                ),
            )}

            {build_metric(
                "Entry Value",
                format_decimal(
                    summary["entry_value"]
                ),
            )}

            {build_metric(
                "Market Value",
                format_decimal(
                    summary["market_value"]
                ),
            )}

            {build_metric(
                "Unrealized Gain / Loss",
                format_decimal(
                    summary[
                        "unrealized_gain_loss"
                    ]
                ),
                gain_loss_class(
                    summary[
                        "unrealized_gain_loss"
                    ]
                ),
            )}

            {build_metric(
                "Realized Gain / Loss",
                format_decimal(
                    summary[
                        "realized_gain_loss"
                    ]
                ),
                gain_loss_class(
                    summary[
                        "realized_gain_loss"
                    ]
                ),
            )}
        </div>

        <section>
            <h2>Portfolio by Asset</h2>

            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Symbol</th>
                            <th>Asset</th>
                            <th>Open</th>
                            <th>Closed</th>
                            <th>Entry Value</th>
                            <th>Market Value</th>
                            <th>Unrealized</th>
                            <th>Realized</th>
                        </tr>
                    </thead>

                    <tbody>
                        {asset_table}
                    </tbody>
                </table>
            </div>
        </section>

        <section>
            <h2>Consolidated Position Register</h2>

            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Symbol</th>
                            <th>Type</th>
                            <th>Status</th>
                            <th>Quantity</th>
                            <th>Entry Price</th>
                            <th>Opened</th>
                            <th>Gain / Loss</th>
                            <th>Return %</th>
                        </tr>
                    </thead>

                    <tbody>
                        {position_table}
                    </tbody>
                </table>
            </div>
        </section>

        <footer>
            Market Lens · CIN Entertainment
        </footer>
    </main>
</body>
</html>
"""
