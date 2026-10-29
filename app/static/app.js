const state = {
    assets: [],
    assetDetails: new Map(),
    selectedAssetId: null,
    priceBars: [],
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
            // Preserve the default message when no JSON exists.
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

            return matchesSearch && matchesType;
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


async function selectAsset(
    assetId,
    scrollToWorkspace = true
) {
    try {
        const [asset, priceBars] = await Promise.all([
            apiRequest(`/assets/${assetId}`),
            apiRequest(`/assets/${assetId}/prices`),
        ]);

        state.selectedAssetId = assetId;
        state.priceBars = priceBars;
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

    elements.analysisWorkspace.classList.add(
        "hidden"
    );

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

    const submitButton = elements.syncForm.querySelector(
        'button[type="submit"]'
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

    const priceRange = maximumPrice - minimumPrice;
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
        priceBars[priceBars.length - 1].trading_date
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

        showToast(`${asset.symbol} was deleted.`);

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


async function refreshSelectedPrices() {
    if (state.selectedAssetId === null) {
        return;
    }

    await selectAsset(
        state.selectedAssetId,
        false
    );

    showToast("Price history refreshed.");
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

    elements.refreshPricesButton.addEventListener(
        "click",
        refreshSelectedPrices
    );
}


async function initializeApplication() {
    setDefaultSyncDates();
    registerEventListeners();
    await loadAssets();
}


initializeApplication();