const portfolioElements = {
    refreshButton: document.querySelector(
        "#refreshPortfolioButton"
    ),

    positionFilter: document.querySelector(
        "#globalPositionFilter"
    ),

    openPositions: document.querySelector(
        "#globalOpenPositions"
    ),

    totalPositions: document.querySelector(
        "#globalTotalPositions"
    ),

    entryValue: document.querySelector(
        "#globalEntryValue"
    ),

    marketValue: document.querySelector(
        "#globalMarketValue"
    ),

    unrealizedGainLoss: document.querySelector(
        "#globalUnrealizedGainLoss"
    ),

    realizedGainLoss: document.querySelector(
        "#globalRealizedGainLoss"
    ),

    assetList: document.querySelector(
        "#globalPortfolioAssets"
    ),

    positionList: document.querySelector(
        "#globalPositionList"
    ),
};


const portfolioState = {
    summary: null,
};


function portfolioEscapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function portfolioCurrency() {
    const assets = (
        portfolioState.summary?.assets
        || []
    );

    const currencies = new Set(
        assets.map((asset) => asset.currency)
    );

    if (currencies.size === 1) {
        return assets[0].currency;
    }

    if (currencies.size > 1) {
        return null;
    }

    return "USD";
}


function portfolioFormatMoney(value, currency) {
    const numericValue = Number(value || 0);

    if (!Number.isFinite(numericValue)) {
        return "—";
    }

    if (!currency) {
        return numericValue.toLocaleString(
            "en-US",
            {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
            }
        );
    }

    try {
        return new Intl.NumberFormat(
            "en-US",
            {
                style: "currency",
                currency,
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
            }
        ).format(numericValue);
    } catch {
        return (
            `${currency} `
            + numericValue.toFixed(2)
        );
    }
}


function portfolioFormatDate(value) {
    if (!value) {
        return "—";
    }

    const date = new Date(`${value}T00:00:00`);

    if (Number.isNaN(date.getTime())) {
        return value;
    }

    return date.toLocaleDateString(
        "en-US",
        {
            month: "short",
            day: "numeric",
            year: "numeric",
        }
    );
}


function portfolioValueClass(value) {
    const numericValue = Number(value || 0);

    if (numericValue > 0) {
        return "positive-value";
    }

    if (numericValue < 0) {
        return "negative-value";
    }

    return "neutral-value";
}


function setPortfolioMetric(
    element,
    value,
    currency,
    colorize = false
) {
    element.textContent = portfolioFormatMoney(
        value,
        currency
    );

    element.classList.remove(
        "positive-value",
        "negative-value",
        "neutral-value"
    );

    if (colorize) {
        element.classList.add(
            portfolioValueClass(value)
        );
    }
}


function renderPortfolioMetrics(summary) {
    const currency = portfolioCurrency();

    portfolioElements.openPositions.textContent = (
        summary.open_position_count
    );

    portfolioElements.totalPositions.textContent = (
        summary.total_position_count
    );

    setPortfolioMetric(
        portfolioElements.entryValue,
        summary.entry_value,
        currency
    );

    setPortfolioMetric(
        portfolioElements.marketValue,
        summary.market_value,
        currency
    );

    setPortfolioMetric(
        portfolioElements.unrealizedGainLoss,
        summary.unrealized_gain_loss,
        currency,
        true
    );

    setPortfolioMetric(
        portfolioElements.realizedGainLoss,
        summary.realized_gain_loss,
        currency,
        true
    );
}


function renderPortfolioAssets(summary) {
    const assets = summary.assets || [];

    if (assets.length === 0) {
        portfolioElements.assetList.innerHTML = `
            <p class="empty-state">
                No portfolio assets available.
            </p>
        `;

        return;
    }

    portfolioElements.assetList.innerHTML = assets
        .map((asset) => {
            const unrealizedClass = (
                portfolioValueClass(
                    asset.unrealized_gain_loss
                )
            );

            const realizedClass = (
                portfolioValueClass(
                    asset.realized_gain_loss
                )
            );

            return `
                <article class="global-asset-card">
                    <div class="global-asset-heading">
                        <div>
                            <strong>
                                ${portfolioEscapeHtml(
                                    asset.symbol
                                )}
                            </strong>

                            <span>
                                ${portfolioEscapeHtml(
                                    asset.asset_name
                                    || "Unnamed asset"
                                )}
                            </span>
                        </div>

                        <button
                            class="secondary-button compact-button"
                            type="button"
                            data-global-action="analyze"
                            data-asset-id="${asset.asset_id}"
                        >
                            Analyze
                        </button>
                    </div>

                    <div class="global-asset-metrics">
                        <div>
                            <span>Open</span>

                            <strong>
                                ${asset.open_position_count}
                            </strong>
                        </div>

                        <div>
                            <span>Closed</span>

                            <strong>
                                ${asset.closed_position_count}
                            </strong>
                        </div>

                        <div>
                            <span>Market Value</span>

                            <strong>
                                ${portfolioEscapeHtml(
                                    portfolioFormatMoney(
                                        asset.market_value,
                                        asset.currency
                                    )
                                )}
                            </strong>
                        </div>

                        <div>
                            <span>Unrealized</span>

                            <strong class="${unrealizedClass}">
                                ${portfolioEscapeHtml(
                                    portfolioFormatMoney(
                                        asset.unrealized_gain_loss,
                                        asset.currency
                                    )
                                )}
                            </strong>
                        </div>

                        <div>
                            <span>Realized</span>

                            <strong class="${realizedClass}">
                                ${portfolioEscapeHtml(
                                    portfolioFormatMoney(
                                        asset.realized_gain_loss,
                                        asset.currency
                                    )
                                )}
                            </strong>
                        </div>
                    </div>
                </article>
            `;
        })
        .join("");
}


function getFilteredPortfolioPositions() {
    const positions = (
        portfolioState.summary?.positions
        || []
    );

    const filter = (
        portfolioElements.positionFilter.value
    );

    if (filter === "open") {
        return positions.filter(
            (position) => position.is_open
        );
    }

    if (filter === "closed") {
        return positions.filter(
            (position) => !position.is_open
        );
    }

    return positions;
}


function renderPortfolioPositions() {
    const positions = (
        getFilteredPortfolioPositions()
    );

    if (positions.length === 0) {
        portfolioElements.positionList.innerHTML = `
            <p class="empty-state">
                No paper positions match this view.
            </p>
        `;

        return;
    }

    portfolioElements.positionList.innerHTML = positions
        .map((position) => {
            const gainLoss = position.is_open
                ? position.unrealized_gain_loss
                : position.realized_gain_loss;

            const gainLossClass = (
                portfolioValueClass(gainLoss)
            );

            const statusText = position.is_open
                ? "Open"
                : "Closed";

            const valuation = position.is_open
                ? position.market_value
                : (
                    Number(position.quantity)
                    * Number(position.exit_price || 0)
                );

            const valuationLabel = position.is_open
                ? "Market Value"
                : "Exit Value";

            return `
                <article class="global-position-card">
                    <div class="global-position-heading">
                        <div>
                            <span class="global-position-symbol">
                                ${portfolioEscapeHtml(
                                    position.symbol
                                )}
                            </span>

                            <strong>
                                ${portfolioEscapeHtml(
                                    position.position_type
                                )}
                                ·
                                ${portfolioEscapeHtml(
                                    String(position.quantity)
                                )}
                                units
                            </strong>
                        </div>

                        <span class="position-status ${
                            position.is_open
                                ? "open"
                                : "closed"
                        }">
                            ${statusText}
                        </span>
                    </div>

                    <div class="global-position-metrics">
                        <div>
                            <span>Entry Price</span>

                            <strong>
                                ${portfolioEscapeHtml(
                                    portfolioFormatMoney(
                                        position.entry_price,
                                        position.currency
                                    )
                                )}
                            </strong>
                        </div>

                        <div>
                            <span>${valuationLabel}</span>

                            <strong>
                                ${portfolioEscapeHtml(
                                    portfolioFormatMoney(
                                        valuation,
                                        position.currency
                                    )
                                )}
                            </strong>
                        </div>

                        <div>
                            <span>Gain / Loss</span>

                            <strong class="${gainLossClass}">
                                ${portfolioEscapeHtml(
                                    portfolioFormatMoney(
                                        gainLoss,
                                        position.currency
                                    )
                                )}
                            </strong>
                        </div>

                        <div>
                            <span>Opened</span>

                            <strong>
                                ${portfolioEscapeHtml(
                                    portfolioFormatDate(
                                        position.opened_date
                                    )
                                )}
                            </strong>
                        </div>
                    </div>

                    <div class="global-position-footer">
                        <span>
                            ${portfolioEscapeHtml(
                                position.notes
                                || "No position notes recorded."
                            )}
                        </span>

                        <button
                            class="secondary-button compact-button"
                            type="button"
                            data-global-action="analyze"
                            data-asset-id="${position.asset_id}"
                        >
                            View Asset
                        </button>
                    </div>
                </article>
            `;
        })
        .join("");
}


function renderPortfolioSummary(summary) {
    portfolioState.summary = summary;

    renderPortfolioMetrics(summary);
    renderPortfolioAssets(summary);
    renderPortfolioPositions();
}


async function loadPortfolioSummary(
    showConfirmation = false
) {
    const button = portfolioElements.refreshButton;
    const originalText = button.textContent;

    button.disabled = true;
    button.textContent = "Refreshing...";

    try {
        const response = await fetch(
            "/portfolio/summary"
        );

        if (!response.ok) {
            let message = (
                "Unable to load portfolio summary."
            );

            try {
                const payload = await response.json();

                if (payload.detail) {
                    message = payload.detail;
                }
            } catch {
                // Preserve the default message.
            }

            throw new Error(message);
        }

        const summary = await response.json();

        renderPortfolioSummary(summary);

        if (showConfirmation) {
            showToast("Portfolio overview refreshed.");
        }
    } catch (error) {
        showToast(error.message, true);
    } finally {
        button.disabled = false;
        button.textContent = originalText;
    }
}


function handleGlobalPortfolioClick(event) {
    const button = event.target.closest(
        "[data-global-action]"
    );

    if (!button) {
        return;
    }

    const assetId = Number(
        button.dataset.assetId
    );

    if (!Number.isInteger(assetId)) {
        return;
    }

    if (
        button.dataset.globalAction === "analyze"
        && typeof selectAsset === "function"
    ) {
        selectAsset(assetId);
    }
}


function registerPortfolioEvents() {
    portfolioElements.refreshButton.addEventListener(
        "click",
        () => loadPortfolioSummary(true)
    );

    portfolioElements.positionFilter.addEventListener(
        "change",
        renderPortfolioPositions
    );

    portfolioElements.assetList.addEventListener(
        "click",
        handleGlobalPortfolioClick
    );

    portfolioElements.positionList.addEventListener(
        "click",
        handleGlobalPortfolioClick
    );
}


function initializePortfolioDashboard() {
    registerPortfolioEvents();
    loadPortfolioSummary();
}


initializePortfolioDashboard();