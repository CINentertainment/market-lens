const state = {
    assets: [],
    assetDetails: new Map(),
    selectedAssetId: null,
    priceBars: [],
    signals: [],
    positions: [],
};

const elements = {
    assetForm: document.querySelector("#assetForm"),
    assetSymbol: document.querySelector("#assetSymbol"),
    assetName: document.querySelector("#assetName"),
    assetType: document.querySelector("#assetType"),
    assetCurrency: document.querySelector("#assetCurrency"),
    assetExchange: document.querySelector("#assetExchange"),
    assetActive: document.querySelector("#assetActive"),

    assetSearch: document.querySelector("#assetSearch"),
    assetTypeFilter: document.querySelector(
        "#assetTypeFilter"
    ),
    assetList: document.querySelector("#assetList"),
    refreshAssetsButton: document.querySelector(
        "#refreshAssetsButton"
    ),

    trackedAssets: document.querySelector("#trackedAssets"),
    activeAssets: document.querySelector("#activeAssets"),
    storedPrices: document.querySelector("#storedPrices"),
    selectedSymbol: document.querySelector(
        "#selectedSymbol"
    ),

    analysisWorkspace: document.querySelector(
        "#analysisWorkspace"
    ),
    selectedAssetTitle: document.querySelector(
        "#selectedAssetTitle"
    ),
    selectedAssetSummary: document.querySelector(
        "#selectedAssetSummary"
    ),
    closeWorkspaceButton: document.querySelector(
        "#closeWorkspaceButton"
    ),

    syncForm: document.querySelector("#syncForm"),
    syncStartDate: document.querySelector(
        "#syncStartDate"
    ),
    syncEndDate: document.querySelector("#syncEndDate"),
    syncResult: document.querySelector("#syncResult"),

    latestPriceSummary: document.querySelector(
        "#latestPriceSummary"
    ),

    analyticsTrend: document.querySelector(
        "#analyticsTrend"
    ),
    analyticsTotalReturn: document.querySelector(
        "#analyticsTotalReturn"
    ),
    analyticsDailyChange: document.querySelector(
        "#analyticsDailyChange"
    ),
    analyticsMovingAverage20: document.querySelector(
        "#analyticsMovingAverage20"
    ),
    analyticsMovingAverage50: document.querySelector(
        "#analyticsMovingAverage50"
    ),
    analyticsVolatility: document.querySelector(
        "#analyticsVolatility"
    ),

    signalForm: document.querySelector("#signalForm"),
    signalType: document.querySelector("#signalType"),
    signalDirection: document.querySelector(
        "#signalDirection"
    ),
    signalTargetPrice: document.querySelector(
        "#signalTargetPrice"
    ),
    signalStatus: document.querySelector(
        "#signalStatus"
    ),
    signalRationale: document.querySelector(
        "#signalRationale"
    ),
    refreshSignalsButton: document.querySelector(
        "#refreshSignalsButton"
    ),
    activeSignalCount: document.querySelector(
        "#activeSignalCount"
    ),
    triggeredSignalCount: document.querySelector(
        "#triggeredSignalCount"
    ),
    totalSignalCount: document.querySelector(
        "#totalSignalCount"
    ),
    signalList: document.querySelector("#signalList"),

    positionForm: document.querySelector("#positionForm"),
    positionType: document.querySelector("#positionType"),
    positionOpenedDate: document.querySelector(
        "#positionOpenedDate"
    ),
    positionQuantity: document.querySelector(
        "#positionQuantity"
    ),
    positionEntryPrice: document.querySelector(
        "#positionEntryPrice"
    ),
    positionNotes: document.querySelector(
        "#positionNotes"
    ),
    positionStatusFilter: document.querySelector(
        "#positionStatusFilter"
    ),
    refreshPositionsButton: document.querySelector(
        "#refreshPositionsButton"
    ),
    openPositionCount: document.querySelector(
        "#openPositionCount"
    ),
    portfolioEntryValue: document.querySelector(
        "#portfolioEntryValue"
    ),
    portfolioMarketValue: document.querySelector(
        "#portfolioMarketValue"
    ),
    portfolioUnrealizedGainLoss: document.querySelector(
        "#portfolioUnrealizedGainLoss"
    ),
    portfolioRealizedGainLoss: document.querySelector(
        "#portfolioRealizedGainLoss"
    ),
    positionList: document.querySelector("#positionList"),

    refreshPricesButton: document.querySelector(
        "#refreshPricesButton"
    ),
    priceChart: document.querySelector("#priceChart"),
    priceTableBody: document.querySelector(
        "#priceTableBody"
    ),

    toast: document.querySelector("#toast"),
};

let toastTimer = null;


function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function formatDate(dateValue) {
    if (!dateValue) {
        return "—";
    }

    const date = new Date(`${dateValue}T00:00:00`);

    return new Intl.DateTimeFormat(
        "en-US",
        {
            year: "numeric",
            month: "short",
            day: "numeric",
        }
    ).format(date);
}


function formatTimestamp(value) {
    if (!value) {
        return "Not triggered";
    }

    const timestamp = new Date(value);

    if (Number.isNaN(timestamp.getTime())) {
        return "Triggered";
    }

    return new Intl.DateTimeFormat(
        "en-US",
        {
            year: "numeric",
            month: "short",
            day: "numeric",
            hour: "numeric",
            minute: "2-digit",
        }
    ).format(timestamp);
}


function formatPrice(value, currency = "USD") {
    if (value === null || value === undefined) {
        return "—";
    }

    const numericValue = Number(value);

    if (!Number.isFinite(numericValue)) {
        return "—";
    }

    try {
        return new Intl.NumberFormat(
            "en-US",
            {
                style: "currency",
                currency,
                minimumFractionDigits: 2,
                maximumFractionDigits: 4,
            }
        ).format(numericValue);
    } catch {
        return numericValue.toFixed(2);
    }
}


function formatVolume(value) {
    if (value === null || value === undefined) {
        return "—";
    }

    return new Intl.NumberFormat(
        "en-US",
        {
            notation: "compact",
            maximumFractionDigits: 2,
        }
    ).format(Number(value));
}


function formatAnalyticsPercent(
    value,
    includeSign = false
) {
    if (value === null || value === undefined) {
        return "—";
    }

    const numericValue = Number(value);

    if (!Number.isFinite(numericValue)) {
        return "—";
    }

    const sign = (
        includeSign && numericValue > 0
            ? "+"
            : ""
    );

    return `${sign}${numericValue.toFixed(2)}%`;
}


function toDateInputValue(date) {
    const year = date.getFullYear();

    const month = String(
        date.getMonth() + 1
    ).padStart(2, "0");

    const day = String(
        date.getDate()
    ).padStart(2, "0");

    return `${year}-${month}-${day}`;
}


function setDefaultSyncDates() {
    const endDate = new Date();
    const startDate = new Date();

    startDate.setDate(startDate.getDate() - 30);

    elements.syncStartDate.value = toDateInputValue(
        startDate
    );

    elements.syncEndDate.value = toDateInputValue(
        endDate
    );
}


function setDefaultPositionDate() {
    elements.positionOpenedDate.value = (
        toDateInputValue(new Date())
    );
}


function showToast(message, isError = false) {
    window.clearTimeout(toastTimer);

    elements.toast.textContent = message;

    elements.toast.classList.remove(
        "hidden",
        "error"
    );

    if (isError) {
        elements.toast.classList.add("error");
    }

    toastTimer = window.setTimeout(
        () => {
            elements.toast.classList.add("hidden");
        },
        4500
    );
}


async function apiRequest(url, options = {}) {
    const response = await fetch(
        url,
        {
            ...options,
            headers: {
                "Content-Type": "application/json",
                ...(options.headers || {}),
            },
        }
    );

    if (!response.ok) {
        let message = (
            `Request failed with status ${response.status}.`
        );

        try {
            const errorData = await response.json();

            if (typeof errorData.detail === "string") {
                message = errorData.detail;
            } else if (
                Array.isArray(errorData.detail)
                && errorData.detail.length > 0
            ) {
                message = errorData.detail
                    .map((item) => item.msg)
                    .join(" ");
            }
        } catch {
            // Use the default error message.
        }

        throw new Error(message);
    }

    if (response.status === 204) {
        return null;
    }

    return response.json();
}


async function loadAssets() {
    elements.assetList.innerHTML = `
        <p class="empty-state">
            Loading tracked assets...
        </p>
    `;

    try {
        state.assets = await apiRequest(
            "/assets?include_inactive=true"
        );

        const details = await Promise.all(
            state.assets.map(
                (asset) => apiRequest(
                    `/assets/${asset.id}`
                )
            )
        );

        state.assetDetails.clear();

        for (const detail of details) {
            state.assetDetails.set(
                detail.id,
                detail
            );
        }

        renderStatistics();
        renderAssetList();

        if (
            state.selectedAssetId !== null
            && state.assetDetails.has(
                state.selectedAssetId
            )
        ) {
            await selectAsset(
                state.selectedAssetId,
                false
            );
        }
    } catch (error) {
        elements.assetList.innerHTML = `
            <p class="empty-state">
                Unable to load tracked assets.
            </p>
        `;

        showToast(error.message, true);
    }
}


function renderStatistics() {
    const activeCount = state.assets.filter(
        (asset) => asset.is_active
    ).length;

    let storedPriceCount = 0;

    for (
        const detail
        of state.assetDetails.values()
    ) {
        storedPriceCount += (
            detail.price_bars?.length || 0
        );
    }

    elements.trackedAssets.textContent = (
        state.assets.length
    );

    elements.activeAssets.textContent = activeCount;

    elements.storedPrices.textContent = (
        storedPriceCount
    );

    const selectedAsset = state.assets.find(
        (asset) => (
            asset.id === state.selectedAssetId
        )
    );

    elements.selectedSymbol.textContent = (
        selectedAsset?.symbol || "—"
    );
}


function getFilteredAssets() {
    const searchTerm = (
        elements.assetSearch.value
            .trim()
            .toLowerCase()
    );

    const selectedType = (
        elements.assetTypeFilter.value
    );

    return state.assets.filter(
        (asset) => {
            const searchableText = [
                asset.symbol,
                asset.name,
                asset.exchange,
                asset.currency,
            ]
                .join(" ")
                .toLowerCase();

            const matchesSearch = (
                !searchTerm
                || searchableText.includes(searchTerm)
            );

            const matchesType = (
                !selectedType
                || asset.asset_type === selectedType
            );

            return (
                matchesSearch
                && matchesType
            );
        }
    );
}


function renderAssetList() {
    const assets = getFilteredAssets();

    if (assets.length === 0) {
        elements.assetList.innerHTML = `
            <p class="empty-state">
                No assets match the current filters.
            </p>
        `;

        return;
    }

    elements.assetList.innerHTML = assets
        .map(
            (asset) => {
                const detail = state.assetDetails.get(
                    asset.id
                );

                const priceBars = (
                    detail?.price_bars || []
                );

                const latestPrice = [...priceBars]
                    .sort(
                        (first, second) => (
                            second.trading_date.localeCompare(
                                first.trading_date
                            )
                        )
                    )[0];

                const latestPriceText = latestPrice
                    ? formatPrice(
                        latestPrice.close_price,
                        asset.currency
                    )
                    : "No prices";

                const activeLabel = asset.is_active
                    ? "Active"
                    : "Inactive";

                return `
                    <article
                        class="asset-card"
                        data-asset-id="${asset.id}"
                    >
                        <div class="asset-card-header">
                            <div>
                                <h3>
                                    <span class="asset-symbol">
                                        ${escapeHtml(
                                            asset.symbol
                                        )}
                                    </span>
                                </h3>

                                <p class="asset-name">
                                    ${escapeHtml(
                                        asset.name
                                        || "Unnamed asset"
                                    )}
                                </p>
                            </div>

                            <strong>
                                ${escapeHtml(
                                    latestPriceText
                                )}
                            </strong>
                        </div>

                        <div class="asset-meta">
                            <span class="badge purple">
                                ${escapeHtml(
                                    asset.asset_type
                                )}
                            </span>

                            <span class="badge blue">
                                ${escapeHtml(
                                    asset.exchange
                                    || "No exchange"
                                )}
                            </span>

                            <span class="badge">
                                ${escapeHtml(
                                    asset.currency
                                )}
                            </span>

                            <span class="badge">
                                ${activeLabel}
                            </span>

                            <span class="badge">
                                ${priceBars.length}
                                price bars
                            </span>
                        </div>

                        <div class="asset-actions">
                            <button
                                class="asset-action"
                                type="button"
                                data-action="view"
                                data-asset-id="${asset.id}"
                            >
                                Analyze
                            </button>

                            <button
                                class="asset-action"
                                type="button"
                                data-action="sync"
                                data-asset-id="${asset.id}"
                            >
                                Sync
                            </button>

                            <button
                                class="danger-button asset-action"
                                type="button"
                                data-action="delete"
                                data-asset-id="${asset.id}"
                            >
                                Delete
                            </button>
                        </div>
                    </article>
                `;
            }
        )
        .join("");
}


async function createAsset(event) {
    event.preventDefault();

    const payload = {
        symbol: elements.assetSymbol.value
            .trim()
            .toUpperCase(),

        name: (
            elements.assetName.value.trim()
            || null
        ),

        asset_type: elements.assetType.value,

        exchange: (
            elements.assetExchange.value.trim()
            || null
        ),

        currency: elements.assetCurrency.value
            .trim()
            .toUpperCase(),

        is_active: (
            elements.assetActive.value === "true"
        ),
    };

    try {
        const createdAsset = await apiRequest(
            "/assets",
            {
                method: "POST",
                body: JSON.stringify(payload),
            }
        );

        elements.assetForm.reset();
        elements.assetType.value = "Equity";
        elements.assetCurrency.value = "USD";
        elements.assetActive.value = "true";

        showToast(
            `${createdAsset.symbol} was added.`
        );

        await loadAssets();
        await selectAsset(createdAsset.id);
    } catch (error) {
        showToast(error.message, true);
    }
}


function getAnalyticsValueClass(value) {
    if (value === null || value === undefined) {
        return "neutral-value";
    }

    const numericValue = Number(value);

    if (numericValue > 0) {
        return "positive-value";
    }

    if (numericValue < 0) {
        return "negative-value";
    }

    return "neutral-value";
}


function setAnalyticsMetric(
    element,
    text,
    valueClass = "neutral-value"
) {
    element.textContent = text;

    element.classList.remove(
        "positive-value",
        "negative-value",
        "neutral-value"
    );

    element.classList.add(valueClass);
}


function renderAnalytics(asset, analyticsData) {
    const trend = (
        analyticsData.trend || "Insufficient Data"
    );

    const normalizedTrend = trend.toLowerCase();
    let trendClass = "neutral-value";

    if (normalizedTrend.includes("bullish")) {
        trendClass = "positive-value";
    } else if (
        normalizedTrend.includes("bearish")
    ) {
        trendClass = "negative-value";
    }

    setAnalyticsMetric(
        elements.analyticsTrend,
        trend,
        trendClass
    );

    setAnalyticsMetric(
        elements.analyticsTotalReturn,
        formatAnalyticsPercent(
            analyticsData.total_return_percent,
            true
        ),
        getAnalyticsValueClass(
            analyticsData.total_return_percent
        )
    );

    setAnalyticsMetric(
        elements.analyticsDailyChange,
        formatAnalyticsPercent(
            analyticsData.daily_change_percent,
            true
        ),
        getAnalyticsValueClass(
            analyticsData.daily_change_percent
        )
    );

    setAnalyticsMetric(
        elements.analyticsMovingAverage20,
        analyticsData.moving_average_20 === null
            ? "Insufficient Data"
            : formatPrice(
                analyticsData.moving_average_20,
                asset.currency
            ),
        "neutral-value"
    );

    setAnalyticsMetric(
        elements.analyticsMovingAverage50,
        analyticsData.moving_average_50 === null
            ? "Insufficient Data"
            : formatPrice(
                analyticsData.moving_average_50,
                asset.currency
            ),
        "neutral-value"
    );

    setAnalyticsMetric(
        elements.analyticsVolatility,
        formatAnalyticsPercent(
            analyticsData
                .annualized_volatility_percent
        ),
        "neutral-value"
    );
}


async function selectAsset(
    assetId,
    scrollToWorkspace = true
) {
    try {
        const [
            asset,
            priceBars,
            analyticsData,
            signals,
            positions,
        ] = await Promise.all([
            apiRequest(`/assets/${assetId}`),
            apiRequest(`/assets/${assetId}/prices`),
            apiRequest(
                `/assets/${assetId}/analytics`
            ),
            apiRequest(
                `/assets/${assetId}/signals`
            ),
            apiRequest(
                `/assets/${assetId}/positions`
            ),
        ]);

        state.selectedAssetId = assetId;
        state.priceBars = priceBars;
        state.signals = signals;
        state.positions = positions;
        state.assetDetails.set(assetId, asset);

        elements.analysisWorkspace.classList.remove(
            "hidden"
        );

        elements.selectedAssetTitle.textContent = (
            `${asset.symbol} Market Analysis`
        );

        elements.selectedAssetSummary.innerHTML = `
            <div class="summary-item">
                <span>Asset Name</span>

                <strong>
                    ${escapeHtml(
                        asset.name || "Unnamed asset"
                    )}
                </strong>
            </div>

            <div class="summary-item">
                <span>Asset Type</span>

                <strong>
                    ${escapeHtml(asset.asset_type)}
                </strong>
            </div>

            <div class="summary-item">
                <span>Exchange</span>

                <strong>
                    ${escapeHtml(
                        asset.exchange || "Not specified"
                    )}
                </strong>
            </div>

            <div class="summary-item">
                <span>Currency</span>

                <strong>
                    ${escapeHtml(asset.currency)}
                </strong>
            </div>
        `;

        elements.syncResult.classList.add("hidden");

        renderStatistics();
        renderLatestPrice(asset);
        renderAnalytics(asset, analyticsData);
        renderSignals(asset);
        renderPositions(asset);
        renderPriceTable(asset);
        renderPriceChart(asset);

        if (scrollToWorkspace) {
            elements.analysisWorkspace.scrollIntoView({
                behavior: "smooth",
                block: "start",
            });
        }
    } catch (error) {
        showToast(error.message, true);
    }
}


function closeWorkspace() {
    state.selectedAssetId = null;
    state.priceBars = [];
    state.signals = [];
    state.positions = [];

    elements.analysisWorkspace.classList.add(
        "hidden"
    );

    elements.signalForm.reset();
    elements.signalType.value = "Watch";
    elements.signalStatus.value = "true";

    elements.positionForm.reset();
    elements.positionType.value = "Long";
    elements.positionStatusFilter.value = "all";
    setDefaultPositionDate();

    renderStatistics();
}


async function synchronizePrices(event) {
    event.preventDefault();

    if (state.selectedAssetId === null) {
        showToast(
            "Select an asset before synchronizing.",
            true
        );

        return;
    }

    const startDate = elements.syncStartDate.value;
    const endDate = elements.syncEndDate.value;

    if (!startDate || !endDate) {
        showToast(
            "Select both synchronization dates.",
            true
        );

        return;
    }

    const submitButton = (
        elements.syncForm.querySelector(
            'button[type="submit"]'
        )
    );

    const originalText = submitButton.textContent;

    submitButton.disabled = true;
    submitButton.textContent = "Synchronizing...";

    try {
        const result = await apiRequest(
            (
                `/assets/${state.selectedAssetId}/sync`
                + `?start_date=${encodeURIComponent(
                    startDate
                )}`
                + `&end_date=${encodeURIComponent(
                    endDate
                )}`
            ),
            {
                method: "POST",
            }
        );

        elements.syncResult.innerHTML = `
            <strong>
                ${escapeHtml(result.symbol)}
                synchronization complete.
            </strong>

            <br>

            Received ${result.received_count},
            created ${result.created_count},
            updated ${result.updated_count}.
        `;

        elements.syncResult.classList.remove("hidden");

        showToast(
            `${result.symbol} market data synchronized.`
        );

        await loadAssets();

        await selectAsset(
            state.selectedAssetId,
            false
        );
    } catch (error) {
        showToast(error.message, true);
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = originalText;
    }
}


function getSortedPriceBarsAscending() {
    return [...state.priceBars].sort(
        (first, second) => (
            first.trading_date.localeCompare(
                second.trading_date
            )
        )
    );
}


function getSortedPriceBarsDescending() {
    return [...state.priceBars].sort(
        (first, second) => (
            second.trading_date.localeCompare(
                first.trading_date
            )
        )
    );
}


function renderLatestPrice(asset) {
    const priceBars = getSortedPriceBarsDescending();

    if (priceBars.length === 0) {
        elements.latestPriceSummary.innerHTML = `
            <p class="empty-state">
                No price data available.
            </p>
        `;

        return;
    }

    const latest = priceBars[0];
    const previous = priceBars[1];

    let changeText = "—";

    if (previous) {
        const latestClose = Number(
            latest.close_price
        );

        const previousClose = Number(
            previous.close_price
        );

        const difference = (
            latestClose - previousClose
        );

        const percentage = previousClose === 0
            ? 0
            : (
                difference
                / previousClose
            ) * 100;

        const sign = difference > 0 ? "+" : "";

        changeText = (
            `${sign}${difference.toFixed(2)} `
            + `(${sign}${percentage.toFixed(2)}%)`
        );
    }

    elements.latestPriceSummary.innerHTML = `
        <div class="price-metric">
            <span>Trading Date</span>

            <strong>
                ${formatDate(latest.trading_date)}
            </strong>
        </div>

        <div class="price-metric">
            <span>Close</span>

            <strong>
                ${formatPrice(
                    latest.close_price,
                    asset.currency
                )}
            </strong>
        </div>

        <div class="price-metric">
            <span>Daily Change</span>

            <strong>
                ${escapeHtml(changeText)}
            </strong>
        </div>

        <div class="price-metric">
            <span>Daily High</span>

            <strong>
                ${formatPrice(
                    latest.high_price,
                    asset.currency
                )}
            </strong>
        </div>

        <div class="price-metric">
            <span>Daily Low</span>

            <strong>
                ${formatPrice(
                    latest.low_price,
                    asset.currency
                )}
            </strong>
        </div>

        <div class="price-metric">
            <span>Volume</span>

            <strong>
                ${formatVolume(latest.volume)}
            </strong>
        </div>
    `;
}


function renderPriceTable(asset) {
    const priceBars = getSortedPriceBarsDescending();

    if (priceBars.length === 0) {
        elements.priceTableBody.innerHTML = `
            <tr>
                <td colspan="7">
                    No price data available.
                </td>
            </tr>
        `;

        return;
    }

    elements.priceTableBody.innerHTML = priceBars
        .map(
            (price) => `
                <tr>
                    <td>
                        ${formatDate(
                            price.trading_date
                        )}
                    </td>

                    <td>
                        ${formatPrice(
                            price.open_price,
                            asset.currency
                        )}
                    </td>

                    <td>
                        ${formatPrice(
                            price.high_price,
                            asset.currency
                        )}
                    </td>

                    <td>
                        ${formatPrice(
                            price.low_price,
                            asset.currency
                        )}
                    </td>

                    <td>
                        ${formatPrice(
                            price.close_price,
                            asset.currency
                        )}
                    </td>

                    <td>
                        ${formatPrice(
                            price.adjusted_close,
                            asset.currency
                        )}
                    </td>

                    <td>
                        ${formatVolume(price.volume)}
                    </td>
                </tr>
            `
        )
        .join("");
}


function renderPriceChart(asset) {
    const priceBars = getSortedPriceBarsAscending();

    if (priceBars.length === 0) {
        elements.priceChart.innerHTML = `
            <text
                x="500"
                y="150"
                text-anchor="middle"
                class="chart-label"
            >
                No price history available
            </text>
        `;

        return;
    }

    const chartWidth = 1000;
    const chartHeight = 300;
    const leftPadding = 65;
    const rightPadding = 25;
    const topPadding = 25;
    const bottomPadding = 48;

    const prices = priceBars.map(
        (bar) => Number(bar.close_price)
    );

    let minimumPrice = Math.min(...prices);
    let maximumPrice = Math.max(...prices);

    if (minimumPrice === maximumPrice) {
        minimumPrice -= 1;
        maximumPrice += 1;
    }

    const priceRange = (
        maximumPrice - minimumPrice
    );

    const usableWidth = (
        chartWidth
        - leftPadding
        - rightPadding
    );

    const usableHeight = (
        chartHeight
        - topPadding
        - bottomPadding
    );

    const points = priceBars.map(
        (bar, index) => {
            const x = priceBars.length === 1
                ? leftPadding + usableWidth / 2
                : (
                    leftPadding
                    + (
                        index
                        / (priceBars.length - 1)
                    ) * usableWidth
                );

            const y = (
                topPadding
                + (
                    1
                    - (
                        Number(bar.close_price)
                        - minimumPrice
                                            ) / priceRange
                ) * usableHeight
            );

            return {
                x,
                y,
                bar,
            };
        }
    );

    const pointString = points
        .map(
            (point) => (
                `${point.x.toFixed(2)},`
                + `${point.y.toFixed(2)}`
            )
        )
        .join(" ");

    const areaPointString = [
        `${leftPadding},${chartHeight - bottomPadding}`,
        pointString,
        (
            `${leftPadding + usableWidth},`
            + `${chartHeight - bottomPadding}`
        ),
    ].join(" ");

    const firstDate = priceBars[0].trading_date;

    const lastDate = (
        priceBars[
            priceBars.length - 1
        ].trading_date
    );

    const pointElements = points
        .map(
            (point) => `
                <circle
                    class="chart-point"
                    cx="${point.x.toFixed(2)}"
                    cy="${point.y.toFixed(2)}"
                    r="5"
                >
                    <title>
                        ${formatDate(
                            point.bar.trading_date
                        )}: ${formatPrice(
                            point.bar.close_price,
                            asset.currency
                        )}
                    </title>
                </circle>
            `
        )
        .join("");

    elements.priceChart.innerHTML = `
        <defs>
            <linearGradient
                id="priceAreaGradient"
                x1="0"
                y1="0"
                x2="0"
                y2="1"
            >
                <stop
                    offset="0%"
                    stop-color="#8b5cf6"
                    stop-opacity="0.35"
                ></stop>

                <stop
                    offset="100%"
                    stop-color="#8b5cf6"
                    stop-opacity="0"
                ></stop>
            </linearGradient>
        </defs>

        <line
            x1="${leftPadding}"
            y1="${topPadding}"
            x2="${leftPadding}"
            y2="${chartHeight - bottomPadding}"
            stroke="#2d3045"
            stroke-width="2"
        ></line>

        <line
            x1="${leftPadding}"
            y1="${chartHeight - bottomPadding}"
            x2="${chartWidth - rightPadding}"
            y2="${chartHeight - bottomPadding}"
            stroke="#2d3045"
            stroke-width="2"
        ></line>

        <polygon
            class="chart-area"
            points="${areaPointString}"
        ></polygon>

        <polyline
            class="chart-line"
            points="${pointString}"
        ></polyline>

        ${pointElements}

        <text
            x="${leftPadding}"
            y="${chartHeight - 14}"
            text-anchor="start"
            class="chart-label"
        >
            ${escapeHtml(formatDate(firstDate))}
        </text>

        <text
            x="${chartWidth - rightPadding}"
            y="${chartHeight - 14}"
            text-anchor="end"
            class="chart-label"
        >
            ${escapeHtml(formatDate(lastDate))}
        </text>

        <text
            x="${leftPadding - 12}"
            y="${topPadding + 8}"
            text-anchor="end"
            class="chart-label"
        >
            ${escapeHtml(
                formatPrice(
                    maximumPrice,
                    asset.currency
                )
            )}
        </text>

        <text
            x="${leftPadding - 12}"
            y="${chartHeight - bottomPadding}"
            text-anchor="end"
            class="chart-label"
        >
            ${escapeHtml(
                formatPrice(
                    minimumPrice,
                    asset.currency
                )
            )}
        </text>
    `;
}


async function deleteAsset(assetId) {
    const asset = state.assets.find(
        (item) => item.id === assetId
    );

    if (!asset) {
        return;
    }

    const confirmed = window.confirm(
        (
            `Delete ${asset.symbol} and all of its `
            + "stored price history?"
        )
    );

    if (!confirmed) {
        return;
    }

    try {
        await apiRequest(
            `/assets/${assetId}`,
            {
                method: "DELETE",
            }
        );

        if (state.selectedAssetId === assetId) {
            closeWorkspace();
        }

        showToast(
            `${asset.symbol} was deleted.`
        );

        await loadAssets();
    } catch (error) {
        showToast(error.message, true);
    }
}


function handleAssetListClick(event) {
    const button = event.target.closest(
        "[data-action]"
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

    const action = button.dataset.action;

    if (action === "view") {
        selectAsset(assetId);
    }

    if (action === "sync") {
        selectAsset(assetId).then(
            () => {
                elements.syncStartDate.focus();
            }
        );
    }

    if (action === "delete") {
        deleteAsset(assetId);
    }
}


function renderSignals(asset) {
    const signals = [...state.signals].sort(
        (firstSignal, secondSignal) => {
            if (
                firstSignal.is_triggered
                !== secondSignal.is_triggered
            ) {
                return firstSignal.is_triggered ? -1 : 1;
            }

            return secondSignal.id - firstSignal.id;
        }
    );

    const activeCount = signals.filter(
        (signal) => signal.is_active
    ).length;

    const triggeredCount = signals.filter(
        (signal) => signal.is_triggered
    ).length;

    elements.activeSignalCount.textContent = activeCount;

    elements.triggeredSignalCount.textContent = (
        triggeredCount
    );

    elements.totalSignalCount.textContent = (
        signals.length
    );

    if (signals.length === 0) {
        elements.signalList.innerHTML = `
            <p class="empty-state">
                No market signals have been created.
            </p>
        `;

        return;
    }

    elements.signalList.innerHTML = signals
        .map((signal) => {
            const hasPriceTrigger = (
                signal.target_price !== null
                && signal.trigger_direction !== null
            );

            const triggerText = hasPriceTrigger
                ? (
                    `${signal.trigger_direction} `
                    + formatPrice(
                        signal.target_price,
                        asset.currency
                    )
                )
                : "Manual monitoring";

            const statusText = signal.is_triggered
                ? "Triggered"
                : signal.is_active
                    ? "Active"
                    : "Inactive";

            const statusClass = signal.is_triggered
                ? "triggered"
                : signal.is_active
                    ? "active"
                    : "inactive";

            const rationale = (
                signal.rationale
                || "No analytical rationale recorded."
            );

            const conditionStatus = signal.is_triggered
                ? formatTimestamp(
                    signal.triggered_at
                )
                : signal.is_active
                    ? "Awaiting conditions"
                    : "Monitoring paused";

            return `
                <article
                    class="signal-card ${statusClass}"
                >
                    <div class="signal-card-heading">
                        <div>
                            <span class="signal-type">
                                ${escapeHtml(
                                    signal.signal_type
                                )}
                            </span>

                            <strong>
                                ${escapeHtml(triggerText)}
                            </strong>
                        </div>

                        <span
                            class="signal-status ${statusClass}"
                        >
                            ${escapeHtml(statusText)}
                        </span>
                    </div>

                    <p class="signal-rationale">
                        ${escapeHtml(rationale)}
                    </p>

                    <div class="signal-card-footer">
                        <span>
                            ${escapeHtml(conditionStatus)}
                        </span>

                        <button
                            class="danger-button compact-button"
                            type="button"
                            data-signal-action="delete"
                            data-signal-id="${signal.id}"
                        >
                            Delete
                        </button>
                    </div>
                </article>
            `;
        })
        .join("");
}


async function createSignal(event) {
    event.preventDefault();

    if (state.selectedAssetId === null) {
        showToast(
            "Select an asset before creating a signal.",
            true
        );

        return;
    }

    const direction = (
        elements.signalDirection.value
    );

    const targetPrice = (
        elements.signalTargetPrice.value.trim()
    );

    if (
        (direction && !targetPrice)
        || (!direction && targetPrice)
    ) {
        showToast(
            (
                "Target price and trigger direction "
                + "must be provided together."
            ),
            true
        );

        return;
    }

    const payload = {
        signal_type: elements.signalType.value,

        target_price: (
            targetPrice || null
        ),

        trigger_direction: (
            direction || null
        ),

        rationale: (
            elements.signalRationale.value.trim()
            || null
        ),

        is_active: (
            elements.signalStatus.value === "true"
        ),
    };

    const submitButton = (
        elements.signalForm.querySelector(
            'button[type="submit"]'
        )
    );

    const originalText = submitButton.textContent;

    submitButton.disabled = true;
    submitButton.textContent = "Creating...";

    try {
        const signal = await apiRequest(
            `/assets/${state.selectedAssetId}/signals`,
            {
                method: "POST",
                body: JSON.stringify(payload),
            }
        );

        elements.signalForm.reset();
        elements.signalType.value = "Watch";
        elements.signalStatus.value = "true";

        await refreshSignals(false);

        showToast(
            signal.is_triggered
                ? (
                    "Signal created and immediately "
                    + "triggered."
                )
                : "Market signal created."
        );
    } catch (error) {
        showToast(error.message, true);
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = originalText;
    }
}


async function refreshSignals(
    showConfirmation = true
) {
    if (state.selectedAssetId === null) {
        return;
    }

    try {
        state.signals = await apiRequest(
            `/assets/${state.selectedAssetId}/signals`
        );

        const asset = state.assetDetails.get(
            state.selectedAssetId
        );

        if (asset) {
            renderSignals(asset);
        }

        if (showConfirmation) {
            showToast("Market signals refreshed.");
        }
    } catch (error) {
        showToast(error.message, true);
    }
}


async function deleteSignal(signalId) {
    if (state.selectedAssetId === null) {
        return;
    }

    const signal = state.signals.find(
        (item) => item.id === signalId
    );

    if (!signal) {
        return;
    }

    const confirmed = window.confirm(
        `Delete this ${signal.signal_type} signal?`
    );

    if (!confirmed) {
        return;
    }

    try {
        await apiRequest(
            (
                `/assets/${state.selectedAssetId}`
                + `/signals/${signalId}`
            ),
            {
                method: "DELETE",
            }
        );

        await refreshSignals(false);

        showToast("Market signal deleted.");
    } catch (error) {
        showToast(error.message, true);
    }
}


function handleSignalListClick(event) {
    const button = event.target.closest(
        "[data-signal-action]"
    );

    if (!button) {
        return;
    }

    const signalId = Number(
        button.dataset.signalId
    );

    if (!Number.isInteger(signalId)) {
        return;
    }

    if (
        button.dataset.signalAction === "delete"
    ) {
        deleteSignal(signalId);
    }
}


function setPortfolioValue(element, value, currency) {
    const numericValue = Number(value || 0);

    element.textContent = formatPrice(
        numericValue,
        currency
    );

    element.classList.remove(
        "positive-value",
        "negative-value",
        "neutral-value"
    );

    if (numericValue > 0) {
        element.classList.add("positive-value");
    } else if (numericValue < 0) {
        element.classList.add("negative-value");
    } else {
        element.classList.add("neutral-value");
    }
}


function getFilteredPositions() {
    const filter = elements.positionStatusFilter.value;

    if (filter === "open") {
        return state.positions.filter(
            (position) => position.is_open
        );
    }

    if (filter === "closed") {
        return state.positions.filter(
            (position) => !position.is_open
        );
    }

    return state.positions;
}


function renderPositions(asset) {
    const openPositions = state.positions.filter(
        (position) => position.is_open
    );

    const entryValue = openPositions.reduce(
        (total, position) => (
            total + Number(position.entry_value || 0)
        ),
        0
    );

    const marketValue = openPositions.reduce(
        (total, position) => (
            total + Number(position.market_value || 0)
        ),
        0
    );

    const unrealizedGainLoss = openPositions.reduce(
        (total, position) => (
            total
            + Number(position.unrealized_gain_loss || 0)
        ),
        0
    );

    const realizedGainLoss = state.positions.reduce(
        (total, position) => (
            total
            + Number(position.realized_gain_loss || 0)
        ),
        0
    );

    elements.openPositionCount.textContent = (
        openPositions.length
    );
        elements.portfolioEntryValue.textContent = formatPrice(
        entryValue,
        asset.currency
    );

    elements.portfolioMarketValue.textContent = formatPrice(
        marketValue,
        asset.currency
    );

    setPortfolioValue(
        elements.portfolioUnrealizedGainLoss,
        unrealizedGainLoss,
        asset.currency
    );

    setPortfolioValue(
        elements.portfolioRealizedGainLoss,
        realizedGainLoss,
        asset.currency
    );

    const positions = getFilteredPositions();

    if (positions.length === 0) {
        elements.positionList.innerHTML = `
            <p class="empty-state">
                No paper positions match this view.
            </p>
        `;

        return;
    }

    elements.positionList.innerHTML = positions
        .map((position) => {
            const gainLoss = position.is_open
                ? position.unrealized_gain_loss
                : position.realized_gain_loss;

            const gainLossValue = Number(gainLoss || 0);
            const gainLossClass = gainLossValue > 0
                ? "positive-value"
                : gainLossValue < 0
                    ? "negative-value"
                    : "neutral-value";

            const statusText = position.is_open
                ? "Open"
                : "Closed";

            const valuationLabel = position.is_open
                ? "Market Value"
                : "Exit Value";

            const valuation = position.is_open
                ? position.market_value
                : (
                    Number(position.quantity)
                    * Number(position.exit_price || 0)
                );

            const notes = (
                position.notes
                || "No position notes recorded."
            );

            return `
                <article class="position-card ${
                    position.is_open ? "open" : "closed"
                }">
                    <div class="position-card-heading">
                        <div>
                            <span class="position-type">
                                ${escapeHtml(
                                    position.position_type
                                )}
                            </span>

                            <strong>
                                ${escapeHtml(
                                    String(position.quantity)
                                )} units at ${escapeHtml(
                                    formatPrice(
                                        position.entry_price,
                                        asset.currency
                                    )
                                )}
                            </strong>
                        </div>

                        <span class="position-status ${
                            position.is_open ? "open" : "closed"
                        }">
                            ${statusText}
                        </span>
                    </div>

                    <div class="position-metrics">
                        <div>
                            <span>Entry Value</span>
                            <strong>
                                ${escapeHtml(
                                    formatPrice(
                                        position.entry_value,
                                        asset.currency
                                    )
                                )}
                            </strong>
                        </div>

                        <div>
                            <span>${valuationLabel}</span>
                            <strong>
                                ${escapeHtml(
                                    formatPrice(
                                        valuation,
                                        asset.currency
                                    )
                                )}
                            </strong>
                        </div>

                        <div>
                            <span>Gain / Loss</span>
                            <strong class="${gainLossClass}">
                                ${escapeHtml(
                                    formatPrice(
                                        gainLossValue,
                                        asset.currency
                                    )
                                )}
                            </strong>
                        </div>

                        <div>
                            <span>Return</span>
                            <strong class="${gainLossClass}">
                                ${position.return_percent === null
                                    ? "—"
                                    : escapeHtml(
                                        formatAnalyticsPercent(
                                            position.return_percent,
                                            true
                                        )
                                    )}
                            </strong>
                        </div>
                    </div>

                    <p class="position-notes">
                        ${escapeHtml(notes)}
                    </p>

                    <div class="position-card-footer">
                        <span>
                            Opened ${escapeHtml(
                                formatDate(position.opened_date)
                            )}${position.closed_date
                                ? ` · Closed ${escapeHtml(
                                    formatDate(
                                        position.closed_date
                                    )
                                )}`
                                : ""}
                        </span>

                        <div class="position-actions">
                            ${position.is_open
                                ? `
                                    <button
                                        class="secondary-button compact-button"
                                        type="button"
                                        data-position-action="close"
                                        data-position-id="${position.id}"
                                    >
                                        Close Position
                                    </button>
                                `
                                : ""}

                            <button
                                class="danger-button compact-button"
                                type="button"
                                data-position-action="delete"
                                data-position-id="${position.id}"
                            >
                                Delete
                            </button>
                        </div>
                    </div>
                </article>
            `;
        })
        .join("");
}


async function createPosition(event) {
    event.preventDefault();

    if (state.selectedAssetId === null) {
        showToast(
            "Select an asset before opening a position.",
            true
        );
        return;
    }

    const payload = {
        position_type: elements.positionType.value,
        quantity: elements.positionQuantity.value,
        entry_price: elements.positionEntryPrice.value,
        opened_date: elements.positionOpenedDate.value,
        notes: elements.positionNotes.value.trim() || null,
    };

    const submitButton = elements.positionForm.querySelector(
        'button[type="submit"]'
    );
    const originalText = submitButton.textContent;

    submitButton.disabled = true;
    submitButton.textContent = "Opening...";

    try {
        await apiRequest(
            `/assets/${state.selectedAssetId}/positions`,
            {
                method: "POST",
                body: JSON.stringify(payload),
            }
        );

        elements.positionForm.reset();
        elements.positionType.value = "Long";
        setDefaultPositionDate();

        await refreshPositions(false);
        showToast("Paper position opened.");
    } catch (error) {
        showToast(error.message, true);
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = originalText;
    }
}


async function refreshPositions(showConfirmation = true) {
    if (state.selectedAssetId === null) {
        return;
    }

    try {
        state.positions = await apiRequest(
            `/assets/${state.selectedAssetId}/positions`
        );

        const asset = state.assetDetails.get(
            state.selectedAssetId
        );

        if (asset) {
            renderPositions(asset);
        }

        if (showConfirmation) {
            showToast("Paper positions refreshed.");
        }
    } catch (error) {
        showToast(error.message, true);
    }
}


async function closePosition(positionId) {
    const position = state.positions.find(
        (item) => item.id === positionId
    );

    if (!position || !position.is_open) {
        return;
    }

    const defaultExitPrice = (
        position.current_price
        || position.entry_price
    );

    const exitPrice = window.prompt(
        "Enter the exit price:",
        Number(defaultExitPrice).toFixed(2)
    );

    if (exitPrice === null) {
        return;
    }

    const numericExitPrice = Number(exitPrice);

    if (!Number.isFinite(numericExitPrice) || numericExitPrice <= 0) {
        showToast("Enter a valid exit price.", true);
        return;
    }

    const closedDate = window.prompt(
        "Enter the closing date (YYYY-MM-DD):",
        toDateInputValue(new Date())
    );

    if (closedDate === null) {
        return;
    }

    try {
        await apiRequest(
            (
                `/assets/${state.selectedAssetId}`
                + `/positions/${positionId}/close`
            ),
            {
                method: "POST",
                body: JSON.stringify({
                    exit_price: String(numericExitPrice),
                    closed_date: closedDate,
                }),
            }
        );

        await refreshPositions(false);
        showToast("Paper position closed.");
    } catch (error) {
        showToast(error.message, true);
    }
}


async function deletePosition(positionId) {
    const position = state.positions.find(
        (item) => item.id === positionId
    );

    if (!position) {
        return;
    }

    if (!window.confirm("Delete this paper position?")) {
        return;
    }

    try {
        await apiRequest(
            (
                `/assets/${state.selectedAssetId}`
                + `/positions/${positionId}`
            ),
            { method: "DELETE" }
        );

        await refreshPositions(false);
        showToast("Paper position deleted.");
    } catch (error) {
        showToast(error.message, true);
    }
}


function handlePositionListClick(event) {
    const button = event.target.closest(
        "[data-position-action]"
    );

    if (!button) {
        return;
    }

    const positionId = Number(button.dataset.positionId);

    if (!Number.isInteger(positionId)) {
        return;
    }

    if (button.dataset.positionAction === "close") {
        closePosition(positionId);
    }

    if (button.dataset.positionAction === "delete") {
        deletePosition(positionId);
    }
}


function filterPositions() {
    if (state.selectedAssetId === null) {
        return;
    }

    const asset = state.assetDetails.get(
        state.selectedAssetId
    );

    if (asset) {
        renderPositions(asset);
    }
}


async function refreshSelectedPrices() {
    if (state.selectedAssetId === null) {
        return;
    }

    await selectAsset(
        state.selectedAssetId,
        false
    );

    showToast(
        "Price history and analytics refreshed."
    );
}


function registerEventListeners() {
    elements.assetForm.addEventListener(
        "submit",
        createAsset
    );

    elements.assetSearch.addEventListener(
        "input",
        renderAssetList
    );

    elements.assetTypeFilter.addEventListener(
        "change",
        renderAssetList
    );

    elements.assetList.addEventListener(
        "click",
        handleAssetListClick
    );

    elements.refreshAssetsButton.addEventListener(
        "click",
        loadAssets
    );

    elements.closeWorkspaceButton.addEventListener(
        "click",
        closeWorkspace
    );

    elements.syncForm.addEventListener(
        "submit",
        synchronizePrices
    );

    elements.signalForm.addEventListener(
        "submit",
        createSignal
    );

    elements.refreshSignalsButton.addEventListener(
        "click",
        () => refreshSignals()
    );

    elements.signalList.addEventListener(
        "click",
        handleSignalListClick
    );

    elements.positionForm.addEventListener(
        "submit",
        createPosition
    );

    elements.positionStatusFilter.addEventListener(
        "change",
        filterPositions
    );

    elements.refreshPositionsButton.addEventListener(
        "click",
        () => refreshPositions()
    );

    elements.positionList.addEventListener(
        "click",
        handlePositionListClick
    );

    elements.refreshPricesButton.addEventListener(
        "click",
        refreshSelectedPrices
    );
}


async function initializeApplication() {
    setDefaultSyncDates();
    setDefaultPositionDate();
    registerEventListeners();
    await loadAssets();
}


initializeApplication();