// Global State
let appData = {
    predictions: {},
    last_updated: ""
};
let selectedAsset = null;
let currentFilter = "all";
let statusPollingInterval = null;
let selectedPeriod = "30d"; // Ausgewählter Zeitraum
let historyCache = {}; // Cache für geladene Kursverläufe
let portfolio = [];
let selectedStrategy = "Ausgewogen";
let portfolioInitialized = false;

// Premium Features Global State
let currentCurrency = "USD";
let exchangeRate = 0.92;
let activeAlerts = [];
let triggeredAlertsInterval = null;



// Dynamische API-Basis-URL: Falls lokal oder auf abweichendem Port (z.B. Live Server 5500) ausgeführt,
// verweise auf den FastAPI-Server auf Port 8000. Sonst relative Pfade nutzen.
const API_BASE = (window.location.protocol === 'file:' || window.location.port !== '8000') 
    ? 'http://127.0.0.1:8000' 
    : '';


// Dynamic toast helpers
function showToast(message, type = "info", title = "") {
    let container = document.getElementById("toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        container.className = "toast-container";
        document.body.appendChild(container);
    }
    
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    
    let iconSvg = "";
    if (type === "success") {
        iconSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>`;
        if (!title) title = "Erfolg";
    } else if (type === "error") {
        iconSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`;
        if (!title) title = "Fehler";
    } else if (type === "warning") {
        iconSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>`;
        if (!title) title = "Warnung";
    } else {
        iconSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`;
        if (!title) title = "Info";
    }
    
    toast.innerHTML = `
        <div class="toast-icon">${iconSvg}</div>
        <div class="toast-body">
            <div class="toast-title">${title}</div>
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close" type="button" aria-label="Schließen">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
        </button>
    `;
    
    container.appendChild(toast);
    
    // Force reflow and show
    toast.offsetHeight;
    toast.classList.add("show");
    
    const autoRemoveTimeout = setTimeout(() => {
        dismissToast(toast);
    }, 5000);
    
    toast.querySelector(".toast-close").addEventListener("click", () => {
        clearTimeout(autoRemoveTimeout);
        dismissToast(toast);
    });
}

function dismissToast(toast) {
    toast.classList.add("hide");
    toast.addEventListener("transitionend", () => {
        toast.remove();
    });
}

// DOM Elements
const elements = {
    statusDot: document.getElementById('status-dot'),
    statusText: document.getElementById('status-text'),
    lastUpdateTime: document.getElementById('last-update-time'),
    refreshBtn: document.getElementById('refresh-btn'),
    timeframeBtns: document.querySelectorAll('#timeframe-selector .tf-btn'),
    chartContainer: document.querySelector('.chart-container'),
    
    // Overview
    marketSentiment: document.getElementById('market-sentiment-val'),
    totalAssets: document.getElementById('total-assets-val'),
    topPick: document.getElementById('top-pick-val'),
    
    // Lists
    assetsList: document.getElementById('assets-list'),
    filterBtns: document.querySelectorAll('.filter-tabs .tab-btn'),
    
    // Detail Panels
    noSelectionMsg: document.getElementById('no-selection-msg'),
    detailContent: document.getElementById('detail-content'),
    
    // Detail Fields
    assetName: document.getElementById('detail-asset-name'),
    assetType: document.getElementById('detail-asset-type'),
    assetSymbol: document.getElementById('detail-asset-symbol'),
    assetPrice: document.getElementById('detail-asset-price'),
    assetChange: document.getElementById('detail-asset-change'),
    
    recBadge: document.getElementById('detail-rec-badge'),
    scoreText: document.getElementById('detail-score'),
    scoreRing: document.getElementById('score-ring-progress'),
    riskText: document.getElementById('detail-risk'),
    sentimentText: document.getElementById('detail-sentiment'),
    
    // Tabs
    tabBtns: document.querySelectorAll('.detail-tabs button'),
    tabPanes: document.querySelectorAll('.tab-panes .tab-pane'),
    
    // Indicators
    indRsi: document.getElementById('ind-rsi'),
    indTrend: document.getElementById('ind-trend'),
    indMacd: document.getElementById('ind-macd'),
    
    // AI Pane
    aiExplanation: document.getElementById('detail-ai-explanation'),
    aiDrivers: document.getElementById('detail-ai-drivers'),
    aiRisks: document.getElementById('detail-ai-risks'),
    
    // News Pane
    newsList: document.getElementById('detail-news-list'),
    
    // Portfolio Navigation & Views
    navMarkets: document.getElementById('nav-markets'),
    navPortfolio: document.getElementById('nav-portfolio'),
    marketsView: document.getElementById('markets-view'),
    portfolioView: document.getElementById('portfolio-view'),
    
    // Portfolio Overview
    portTotalValue: document.getElementById('port-total-value'),
    portTotalCost: document.getElementById('port-total-cost'),
    portTotalProfit: document.getElementById('port-total-profit'),
    portPerformanceCard: document.getElementById('port-performance-card'),
    
    // Portfolio Form & Table
    addInvestmentForm: document.getElementById('add-investment-form'),
    invAsset: document.getElementById('inv-asset'),
    invQty: document.getElementById('inv-qty'),
    invPrice: document.getElementById('inv-price'),
    holdingsListBody: document.getElementById('holdings-list-body'),
    
    // Portfolio AI Advisor
    strategyBtns: document.querySelectorAll('.strategy-btn'),
    analyzePortfolioBtn: document.getElementById('analyze-portfolio-btn'),
    portfolioAiReport: document.getElementById('portfolio-ai-report'),
    
    portScoreRing: document.getElementById('port-score-ring-progress'),
    portAiScore: document.getElementById('port-ai-score'),
    portAiSummary: document.getElementById('port-ai-summary'),
    portAiSuggestions: document.getElementById('port-ai-suggestions'),
    portAiDividends: document.getElementById('port-ai-dividends'),
    portAiTips: document.getElementById('port-ai-tips'),
    portAiForecastsBody: document.getElementById('port-ai-forecasts-body'),
    
    // Watchlist Elements
    toggleAddAssetBtn: document.getElementById('toggle-add-asset-btn'),
    addAssetForm: document.getElementById('add-asset-form'),
    addAssetSymbol: document.getElementById('add-asset-symbol'),
    addAssetName: document.getElementById('add-asset-name'),
    addAssetType: document.getElementById('add-asset-type'),
    deleteAssetBtn: document.getElementById('delete-asset-btn')
};

// Initialize Application
document.addEventListener("DOMContentLoaded", () => {
    // Lucide initialisieren
    if (window.lucide) {
        window.lucide.createIcons();
    }
    
    setupEventListeners();
    fetchData();
    checkServerStatus();
    fetchAccuracy();
    initBacktestModal();
    initChatWidget();
    
    // Premium Features
    initCurrencyToggle();
    initAlerts();
    
    // Request notification permission (DSGVO compliant - user is asked, local only)
    if (Notification && Notification.permission === "default") {
        Notification.requestPermission();
    }
});


// Setup Listeners
function setupEventListeners() {
    // Refresh Button
    elements.refreshBtn.addEventListener("click", triggerRefresh);
    
    // Timeframe Buttons
    elements.timeframeBtns.forEach(btn => {
        btn.addEventListener("click", (e) => {
            elements.timeframeBtns.forEach(b => b.classList.remove("active"));
            e.currentTarget.classList.add("active");
            
            const newPeriod = e.currentTarget.dataset.period;
            if (newPeriod !== selectedPeriod) {
                selectedPeriod = newPeriod;
                if (selectedAsset) {
                    loadAssetHistory(selectedAsset, selectedPeriod);
                }
            }
        });
    });
    
    // Filter Tabs
    elements.filterBtns.forEach(btn => {
        btn.addEventListener("click", (e) => {
            elements.filterBtns.forEach(b => b.classList.remove("active"));
            e.currentTarget.classList.add("active");
            currentFilter = e.currentTarget.dataset.filter;
            renderAssetsList();
        });
    });
    
    // Detail Tabs
    elements.tabBtns.forEach(btn => {
        btn.addEventListener("click", (e) => {
            elements.tabBtns.forEach(b => b.classList.remove("active"));
            e.currentTarget.classList.add("active");
            
            const targetPane = e.currentTarget.dataset.tab;
            elements.tabPanes.forEach(pane => {
                pane.classList.remove("active");
                if (pane.id === targetPane) {
                    pane.classList.add("active");
                }
            });
        });
    });

    // View Panel Navigation
    const navAlerts = document.getElementById("nav-alerts");
    if (elements.navMarkets && elements.navPortfolio) {
        elements.navMarkets.addEventListener("click", () => switchView("markets-view"));
        elements.navPortfolio.addEventListener("click", () => switchView("portfolio-view"));
        if (navAlerts) navAlerts.addEventListener("click", () => switchView("alerts-view"));
    }

    // Portfolio Form Submit
    if (elements.addInvestmentForm) {
        elements.addInvestmentForm.addEventListener("submit", handleAddInvestment);
    }

    // Strategy Pills
    elements.strategyBtns.forEach(btn => {
        btn.addEventListener("click", (e) => {
            elements.strategyBtns.forEach(b => b.classList.remove("active"));
            const clicked = e.currentTarget;
            clicked.classList.add("active");
            selectedStrategy = clicked.dataset.strategy;
        });
    });

    // Analyze Portfolio
    if (elements.analyzePortfolioBtn) {
        elements.analyzePortfolioBtn.addEventListener("click", analyzePortfolioWithAI);
    }

    // Watchlist Event Listeners
    if (elements.toggleAddAssetBtn && elements.addAssetForm) {
        elements.toggleAddAssetBtn.addEventListener("click", () => {
            elements.addAssetForm.classList.toggle("collapsed");
            const icon = elements.toggleAddAssetBtn.querySelector("i, svg");
            const text = elements.toggleAddAssetBtn.querySelector("span");
            if (elements.addAssetForm.classList.contains("collapsed")) {
                if (icon) icon.setAttribute("data-lucide", "plus-circle");
                if (text) text.innerText = "Asset beobachten";
            } else {
                if (icon) icon.setAttribute("data-lucide", "minus-circle");
                if (text) text.innerText = "Schließen";
            }
            if (window.lucide) window.lucide.createIcons();
        });
    }

    if (elements.addAssetForm) {
        elements.addAssetForm.addEventListener("submit", handleAddAsset);
    }

    if (elements.deleteAssetBtn) {
        elements.deleteAssetBtn.addEventListener("click", handleDeleteAsset);
    }

    if (elements.addAssetSymbol) {
        elements.addAssetSymbol.addEventListener("blur", handleAutocompleteSymbol);
        elements.addAssetSymbol.addEventListener("input", (e) => {
            const val = e.target.value.trim().toUpperCase();
            const datalist = document.getElementById('popular-tickers');
            if (datalist) {
                const options = Array.from(datalist.options).map(o => o.value);
                if (options.includes(val)) {
                    handleAutocompleteSymbol();
                }
            }
        });
    }

    const sma20Btn = document.getElementById('toggle-sma20');
    const sma50Btn = document.getElementById('toggle-sma50');
    
    if (sma20Btn) {
        sma20Btn.addEventListener('click', () => {
            const active = sma20Btn.getAttribute('data-active') === 'true';
            sma20Btn.setAttribute('data-active', !active ? 'true' : 'false');
            if (selectedAsset) {
                const cached = historyCache[selectedAsset]?.[selectedPeriod] || appData.predictions[selectedAsset]?.history;
                renderChart(cached, selectedAsset, getRecColorHex(appData.predictions[selectedAsset]?.recommendation));
            }
        });
    }
    
    if (sma50Btn) {
        sma50Btn.addEventListener('click', () => {
            const active = sma50Btn.getAttribute('data-active') === 'true';
            sma50Btn.setAttribute('data-active', !active ? 'true' : 'false');
            if (selectedAsset) {
                const cached = historyCache[selectedAsset]?.[selectedPeriod] || appData.predictions[selectedAsset]?.history;
                renderChart(cached, selectedAsset, getRecColorHex(appData.predictions[selectedAsset]?.recommendation));
            }
        });
    }

    // Registrierung der neuen Premium Feature Listener
    setupPortfolioSubTabs();
    initExportButtons();
    setupNotificationTestButtons();
    
    const targetAllocForm = document.getElementById("target-allocation-form");
    if (targetAllocForm) {
        targetAllocForm.addEventListener("submit", handleSaveTargetAllocation);
    }
    
    const rebalanceBtn = document.getElementById("rebalance-analyze-btn");
    if (rebalanceBtn) {
        rebalanceBtn.addEventListener("click", analyzeRebalancing);
    }
    
    const settingsForm = document.getElementById("settings-form");
    if (settingsForm) {
        settingsForm.addEventListener("submit", handleSaveSettings);
    }
    
    const profileSelect = document.getElementById("portfolio-profile-select");
    if (profileSelect) {
        profileSelect.addEventListener("change", async (e) => {
            currentPortfolioId = parseInt(e.target.value);
            await loadPortfolioData();
            renderPortfolio();
            loadTransactions();
            loadChatHistory();
        });
    }
    
    const btnCreateProfile = document.getElementById("btn-create-portfolio");
    if (btnCreateProfile) {
        btnCreateProfile.addEventListener("click", handleCreatePortfolio);
    }
    
    const btnDeleteProfile = document.getElementById("btn-delete-portfolio");
    if (btnDeleteProfile) {
        btnDeleteProfile.addEventListener("click", handleDeletePortfolio);
    }
    
    const addTxForm = document.getElementById("add-transaction-form");
    if (addTxForm) {
        addTxForm.addEventListener("submit", handleAddTransaction);
    }
    
    const taxSimForm = document.getElementById("tax-simulator-form");
    if (taxSimForm) {
        taxSimForm.addEventListener("submit", handleTaxSimulation);
    }

    const targetAllocForm = document.getElementById("target-allocation-form");
    if (targetAllocForm) {
        targetAllocForm.addEventListener("submit", handleSaveTargetAllocation);
    }
    
    const rebalanceBtn = document.getElementById("rebalance-analyze-btn");
    if (rebalanceBtn) {
        rebalanceBtn.addEventListener("click", analyzeRebalancing);
    }
}

// Fetch Data from API
async function fetchData() {
    try {
        const response = await fetch(`${API_BASE}/api/predictions`);
        if (!response.ok) {
            throw new Error(`Server antwortete mit Status: ${response.status}`);
        }
        const data = await response.json();
        
        if (data.predictions && Object.keys(data.predictions).length > 0) {
            appData = data;
            elements.lastUpdateTime.innerText = data.last_updated;
            
            // Berechne aggregierte Werte
            updateOverviewWidgets();
            
            // Liste rendern
            renderAssetsList();
            
            // Erstes Asset standardmäßig selektieren, falls keines ausgewählt ist
            if (!selectedAsset) {
                const firstSymbol = Object.keys(data.predictions)[0];
                selectAsset(firstSymbol);
            } else {
                // Selektion aktualisieren
                selectAsset(selectedAsset);
            }
            
            // Initialize and render Portfolio
            await initPortfolio();
            populateAssetDropdown();
            populateTransactionDropdowns();
            renderPortfolio();
        } else {
            // Keine Daten vorhanden (z.B. initialer Zustand)
            elements.assetsList.innerHTML = `
                <div class="loading-state">
                    <div class="spinner"></div>
                    <p>Erstelle initiale Marktanalyse. Bitte kurz warten...</p>
                </div>
            `;
            // Versuche es in 5 Sekunden erneut
            setTimeout(fetchData, 5000);
        }
    } catch (error) {
        console.error("Fehler beim Laden der Prognosen:", error);
        elements.assetsList.innerHTML = `
            <div class="error-state">
                <i data-lucide="alert-triangle" class="text-red"></i>
                <p>Verbindung zum Server fehlgeschlagen. Versuche erneut zu verbinden...</p>
            </div>
        `;
        if (window.lucide) window.lucide.createIcons();
        setTimeout(fetchData, 5000);
    }
}

// Server Status & Polling
async function checkServerStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/status`);
        if (!response.ok) {
            throw new Error(`Server-Status-Anfrage fehlgeschlagen (HTTP ${response.status})`);
        }
        const status = await response.json();
        
        if (status.is_updating) {
            setUpdatingUI(true);
            if (!statusPollingInterval) {
                // Starte Polling, falls Aktualisierung läuft
                statusPollingInterval = setInterval(pollStatus, 3000);
            }
        } else {
            setUpdatingUI(false);
            if (statusPollingInterval) {
                clearInterval(statusPollingInterval);
                statusPollingInterval = null;
            }
        }
    } catch (error) {
        console.error("Fehler beim Prüfen des Serverstatus:", error);
        if (!statusPollingInterval) {
            setUpdatingUI(false);
        }
    }
}

async function pollStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/status`);
        if (!response.ok) {
            throw new Error(`Server-Status-Anfrage fehlgeschlagen (HTTP ${response.status})`);
        }
        const status = await response.json();
        
        if (!status.is_updating) {
            // Aktualisierung abgeschlossen!
            clearInterval(statusPollingInterval);
            statusPollingInterval = null;
            setUpdatingUI(false);
            historyCache = {}; // Cache nach Update verwerfen
            fetchData(); // Neue Daten holen
            fetchAccuracy(); // Neue Erfolgsquote holen
        }
    } catch (error) {
        console.error("Fehler beim Pollen des Status:", error);
    }
}

function setUpdatingUI(isUpdating) {
    if (isUpdating) {
        elements.statusDot.className = "status-dot updating";
        elements.statusText.innerText = "Aktualisiere...";
        elements.refreshBtn.disabled = true;
        const icon = elements.refreshBtn.querySelector("i, svg");
        if (icon) icon.classList.add("icon-spin-hover");
        elements.refreshBtn.querySelector("span").innerText = "Berechne...";
    } else {
        elements.statusDot.className = "status-dot";
        elements.statusText.innerText = "Bereit";
        elements.refreshBtn.disabled = false;
        const icon = elements.refreshBtn.querySelector("i, svg");
        if (icon) icon.classList.remove("icon-spin-hover");
        elements.refreshBtn.querySelector("span").innerText = "Analysieren";
    }
}

async function triggerRefresh() {
    try {
        console.log("DEBUG: triggerRefresh wurde aufgerufen!");
        setUpdatingUI(true);
        const response = await fetch(`${API_BASE}/api/refresh`, { method: "POST" });
        if (!response.ok) {
            throw new Error(`HTTP-Fehler! Status: ${response.status}`);
        }
        const result = await response.json();
        
        if (result.status === "started" || result.status === "updating") {
            if (!statusPollingInterval) {
                statusPollingInterval = setInterval(pollStatus, 3000);
            }
        } else {
            setUpdatingUI(false);
        }
    } catch (error) {
        console.error("Fehler beim Starten des Updates:", error);
        setUpdatingUI(false);
        showToast("Fehler beim Starten des Updates: " + error.message, "error");
    }
}

// Overview Widgets berechnen
function updateOverviewWidgets() {
    const list = Object.values(appData.predictions);
    
    // 1. Total Assets count
    elements.totalAssets.innerText = list.length;
    
    // 2. Average Sentiment
    let totalSentiment = 0;
    list.forEach(a => totalSentiment += (a.sentiment_score !== undefined && a.sentiment_score !== null ? a.sentiment_score : 0));
    const avgSentiment = list.length > 0 ? totalSentiment / list.length : 0;
    
    let sentimentLabel = "Neutral";
    let sentimentColorClass = "";
    if (avgSentiment > 0.4) {
        sentimentLabel = "Optimistisch";
        sentimentColorClass = "text-green";
    } else if (avgSentiment > 0.15) {
        sentimentLabel = "Leicht Optimistisch";
        sentimentColorClass = "text-green";
    } else if (avgSentiment < -0.4) {
        sentimentLabel = "Pessimistisch";
        sentimentColorClass = "text-red";
    } else if (avgSentiment < -0.15) {
        sentimentLabel = "Leicht Pessimistisch";
        sentimentColorClass = "text-red";
    }
    
    elements.marketSentiment.className = `stat-value ${sentimentColorClass}`;
    elements.marketSentiment.innerText = `${sentimentLabel} (${avgSentiment.toFixed(2)})`;
    
    // 3. Top Pick (Highest Confidence Buy/Strong Buy)
    let bestPick = null;
    let maxConfidence = -1;
    
    list.forEach(a => {
        if ((a.recommendation === "Starker Kauf" || a.recommendation === "Kauf") && a.confidence > maxConfidence) {
            maxConfidence = a.confidence;
            bestPick = a;
        }
    });
    
    if (bestPick) {
        elements.topPick.innerText = `${bestPick.symbol} (${bestPick.confidence}%)`;
    } else {
        elements.topPick.innerText = "Keine";
    }
}

// Left side list builder
function renderAssetsList() {
    elements.assetsList.innerHTML = "";
    const list = Object.values(appData.predictions);
    
    const filtered = list.filter(item => {
        if (currentFilter === "all") return true;
        return item.type === currentFilter;
    });
    
    if (filtered.length === 0) {
        elements.assetsList.innerHTML = `
            <div class="loading-state">
                <p>Keine Assets für diesen Filter vorhanden.</p>
            </div>
        `;
        return;
    }
    
    // Nach Confidence-Score absteigend sortieren
    filtered.sort((a, b) => b.confidence - a.confidence);
    
    filtered.forEach(item => {
        const card = document.createElement("div");
        card.className = `asset-card ${selectedAsset === item.symbol ? 'selected' : ''}`;
        card.dataset.symbol = item.symbol;
        
        const priceChange = (item.price_change_1d !== undefined && item.price_change_1d !== null) ? item.price_change_1d : 0;
        const changeClass = priceChange >= 0 ? "text-green" : "text-red";
        const sign = priceChange >= 0 ? "+" : "";
        
        let recBadgeClass = "badge-hold";
        if (item.recommendation === "Starker Kauf") recBadgeClass = "badge-strong-buy";
        else if (item.recommendation === "Kauf") recBadgeClass = "badge-buy";
        else if (item.recommendation === "Verkauf") recBadgeClass = "badge-sell";
        else if (item.recommendation === "Starker Verkauf") recBadgeClass = "badge-strong-sell";
        
        card.innerHTML = `
            <div class="card-left">
                <div class="symbol-row">
                    <span class="card-symbol">${item.symbol}</span>
                    <span class="card-type">${item.type === 'crypto' ? 'Krypto' : (item.type === 'stock' ? 'Aktie' : 'Rohstoff')}</span>
                </div>
                <span class="card-name">${item.name}</span>
            </div>
            <div class="card-right">
                <span class="card-price">${formatCurrency(item.price, item.type)}</span>
                <span class="card-change ${changeClass}">${sign}${priceChange.toFixed(2)}%</span>
                <span class="card-badge ${recBadgeClass}">${item.recommendation || "Halten"}</span>
            </div>
        `;
        
        card.addEventListener("click", () => selectAsset(item.symbol));
        elements.assetsList.appendChild(card);
    });
}

// Select Asset and Render Detail
function selectAsset(symbol) {
    selectedAsset = symbol;
    
    // Highlight list item
    document.querySelectorAll(".asset-card").forEach(c => {
        if (c.dataset.symbol === symbol) {
            c.classList.add("selected");
        } else {
            c.classList.remove("selected");
        }
    });
    
    const asset = appData.predictions[symbol];
    if (!asset) return;
    
    // Show detail pane
    elements.noSelectionMsg.classList.add("hidden");
    elements.detailContent.classList.remove("hidden");
    
    // Top Infos
    elements.assetName.innerText = asset.name;
    elements.assetSymbol.innerText = asset.symbol;
    elements.assetType.innerText = asset.type === 'crypto' ? 'Kryptowährung' : (asset.type === 'stock' ? 'Aktie' : 'Rohstoff');
    elements.assetPrice.innerText = formatCurrency(asset.price, asset.type);
    
    const priceChange = (asset.price_change_1d !== undefined && asset.price_change_1d !== null) ? asset.price_change_1d : 0;
    const changeClass = priceChange >= 0 ? "text-green" : "text-red";
    const sign = priceChange >= 0 ? "+" : "";
    elements.assetChange.className = `detail-change ${changeClass}`;
    elements.assetChange.innerText = `${sign}${priceChange.toFixed(2)}% (24h)`;
    
    // Recommendation Hero
    elements.recBadge.innerText = asset.recommendation || "Halten";
    // Set Badge Color
    let recClass = "badge-hold";
    let colorHex = "#f59e0b";
    if (asset.recommendation === "Starker Kauf") { recClass = "badge-strong-buy"; colorHex = "#10b981"; }
    else if (asset.recommendation === "Kauf") { recClass = "badge-buy"; colorHex = "#34d399"; }
    else if (asset.recommendation === "Verkauf") { recClass = "badge-sell"; colorHex = "#f43f5e"; }
    else if (asset.recommendation === "Starker Verkauf") { recClass = "badge-strong-sell"; colorHex = "#e11d48"; }
    
    elements.recBadge.className = `rec-badge ${recClass}`;
    elements.recBadge.style.color = colorHex;
    
    // Confidence ring update
    const confidence = (asset.confidence !== undefined && asset.confidence !== null) ? asset.confidence : 50;
    elements.scoreText.innerText = `${confidence}%`;
    updateConfidenceRing(confidence, colorHex);
    
    // Risk & Sentiment
    elements.riskText.innerText = asset.risk_level || "Mittel";
    
    let sentimentLabel = "Neutral";
    const sentimentScore = (asset.sentiment_score !== undefined && asset.sentiment_score !== null) ? asset.sentiment_score : 0.0;
    if (sentimentScore > 0.3) sentimentLabel = "Sehr Positiv";
    else if (sentimentScore > 0.05) sentimentLabel = "Positiv";
    else if (sentimentScore < -0.3) sentimentLabel = "Sehr Negativ";
    else if (sentimentScore < -0.05) sentimentLabel = "Negativ";
    elements.sentimentText.innerText = `${sentimentLabel} (${sentimentScore.toFixed(2)})`;
    
    // Target Levels (Zielkurs, Stop Loss, Take Profit)
    const targetEl = document.getElementById("detail-target-price");
    const stopEl = document.getElementById("detail-stop-loss");
    const takeEl = document.getElementById("detail-take-profit");
    if (targetEl) targetEl.innerText = asset.target_price ? formatCurrency(asset.target_price, asset.type) : "-";
    if (stopEl) stopEl.innerText = asset.stop_loss ? formatCurrency(asset.stop_loss, asset.type) : "-";
    if (takeEl) takeEl.innerText = asset.take_profit ? formatCurrency(asset.take_profit, asset.type) : "-";
    
    // Technical Indicators
    const rsiVal = (asset.rsi !== undefined && asset.rsi !== null) ? asset.rsi : 50.0;
    elements.indRsi.innerText = rsiVal.toFixed(1);
    
    let rsiLabel = "Neutral";
    if (rsiVal < 30) rsiLabel = "Überverkauft";
    else if (rsiVal > 70) rsiLabel = "Überkauft";
    elements.indRsi.className = `ind-value ${rsiVal < 30 ? 'text-green' : (rsiVal > 70 ? 'text-red' : '')}`;
    
    elements.indTrend.innerText = asset.technical_trend || "Neutral";
    elements.indTrend.className = `ind-value ${asset.technical_trend === 'Bullish' ? 'text-green' : (asset.technical_trend === 'Bearish' ? 'text-red' : '')}`;
    
    const macdVal = (asset.macd !== undefined && asset.macd !== null) ? asset.macd : 0.0;
    elements.indMacd.innerText = macdVal.toFixed(3);
    
    // AI Explanation
    elements.aiExplanation.innerText = asset.ai_explanation;
    
    // Drivers List
    elements.aiDrivers.innerHTML = "";
    if (asset.key_drivers && asset.key_drivers.length > 0) {
        asset.key_drivers.forEach(d => {
            const li = document.createElement("li");
            li.innerText = d;
            elements.aiDrivers.appendChild(li);
        });
    } else {
        elements.aiDrivers.innerHTML = "<li>Keine wesentlichen Treiber identifiziert.</li>";
    }
    
    // Risks List
    elements.aiRisks.innerHTML = "";
    if (asset.key_risks && asset.key_risks.length > 0) {
        asset.key_risks.forEach(r => {
            const li = document.createElement("li");
            li.innerText = r;
            elements.aiRisks.appendChild(li);
        });
    } else {
        elements.aiRisks.innerHTML = "<li>Keine wesentlichen Risiken identifiziert.</li>";
    }
    
    // News list builder
    elements.newsList.innerHTML = "";
    if (asset.news && asset.news.length > 0) {
        asset.news.forEach(n => {
            const item = document.createElement("div");
            item.className = "news-item";
            item.innerHTML = `
                <div class="news-meta">
                    <span class="news-publisher">${n.publisher}</span>
                    <span>${n.time}</span>
                </div>
                <a href="${n.link}" target="_blank" class="news-title">${n.title}</a>
                ${n.summary ? `<p class="news-summary">${n.summary.substring(0, 150)}${n.summary.length > 150 ? '...' : ''}</p>` : ''}
            `;
            elements.newsList.appendChild(item);
        });
    } else {
        elements.newsList.innerHTML = `
            <div class="loading-state">
                <p>Keine aktuellen Nachrichten zu diesem Asset gefunden.</p>
            </div>
        `;
    }
    
    // Render Chart based on selected timeframe
    if (selectedPeriod === "30d" && asset.history) {
        renderChart(asset.history, asset.symbol, colorHex);
    } else {
        loadAssetHistory(symbol, selectedPeriod);
    }
}

// Update SVG Progress Ring
function updateConfidenceRing(percent, color) {
    const circle = elements.scoreRing;
    const radius = circle.r.baseVal.value;
    const circumference = radius * 2 * Math.PI;
    
    circle.style.strokeDasharray = `${circumference} ${circumference}`;
    const offset = circumference - (percent / 100 * circumference);
    circle.style.strokeDashoffset = offset;
    circle.style.stroke = color;
}

// Render Chart
function renderChart(historyData, symbol, accentColor) {
    if (!historyData || historyData.length === 0) return;
    
    if (typeof Chart === 'undefined') {
        console.error("Chart.js is not loaded.");
        const chartContainer = document.querySelector('.chart-container');
        if (chartContainer) {
            chartContainer.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-secondary);">Chart.js-Bibliothek konnte nicht geladen werden. Bitte Internetverbindung prüfen.</div>';
        }
        return;
    }
    
    const labels = historyData.map(h => {
        const d = new Date(h.date);
        if (selectedPeriod === "24h") {
            return d.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
        } else if (selectedPeriod === "7d") {
            const weekday = d.toLocaleDateString("de-DE", { weekday: "short" });
            const time = d.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
            return `${weekday} ${time}`;
        } else if (selectedPeriod === "5y" || selectedPeriod === "10y") {
            return d.toLocaleDateString("de-DE", { year: "numeric", month: "short" });
        } else {
            return d.toLocaleDateString("de-DE", { month: "short", day: "numeric" });
        }
    });
    const prices = historyData.map(h => h.price);
    
    const ctx = document.getElementById('priceChart').getContext('2d');
    
    // Alten Chart zerstören falls vorhanden
    if (window.priceChartInstance) {
        window.priceChartInstance.destroy();
    }
    
    // Gradient für Fill erstellen
    const gradient = ctx.createLinearGradient(0, 0, 0, 300);
    // Transparentere Version der Akzentfarbe erstellen
    const rgbAccent = hexToRgb(accentColor);
    gradient.addColorStop(0, `rgba(${rgbAccent.r}, ${rgbAccent.g}, ${rgbAccent.b}, 0.25)`);
    gradient.addColorStop(1, `rgba(${rgbAccent.r}, ${rgbAccent.g}, ${rgbAccent.b}, 0)`);
    
    const datasets = [{
        label: `${symbol} Preis`,
        data: prices,
        borderColor: accentColor,
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        pointHoverBackgroundColor: accentColor,
        pointHoverBorderColor: '#fff',
        fill: true,
        backgroundColor: gradient,
        tension: 0.15
    }];
    
    const showSma20 = document.getElementById('toggle-sma20')?.getAttribute('data-active') === 'true';
    const showSma50 = document.getElementById('toggle-sma50')?.getAttribute('data-active') === 'true';
    
    if (showSma20) {
        const sma20Data = historyData.map(h => h.sma_20);
        datasets.push({
            label: 'SMA 20',
            data: sma20Data,
            borderColor: '#3b82f6',
            borderWidth: 1.5,
            pointRadius: 0,
            fill: false,
            tension: 0.1
        });
    }
    
    if (showSma50) {
        const sma50Data = historyData.map(h => h.sma_50);
        datasets.push({
            label: 'SMA 50',
            data: sma50Data,
            borderColor: '#f59e0b',
            borderWidth: 1.5,
            pointRadius: 0,
            fill: false,
            tension: 0.1
        });
    }
    
    window.priceChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: (showSma20 || showSma50),
                    position: 'top',
                    labels: {
                        color: '#9ca3af',
                        font: {
                            family: 'Inter',
                            size: 10
                        }
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: '#1e293b',
                    titleColor: '#f3f4f6',
                    bodyColor: '#f3f4f6',
                    borderColor: 'rgba(255,255,255,0.08)',
                    borderWidth: 1,
                    displayColors: true,
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${context.parsed.y.toLocaleString("de-DE", {minimumFractionDigits: 2, maximumFractionDigits: 2})} $`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.02)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#9ca3af',
                        font: {
                            size: 10
                        },
                        maxTicksLimit: 8
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.03)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#9ca3af',
                        font: {
                            size: 10
                        },
                        callback: function(value) {
                            return value.toLocaleString("de-DE") + ' $';
                        }
                    }
                }
            }
        }
    });
}

// Helpers
function formatCurrency(value, type) {
    if (value === undefined || value === null || isNaN(value)) {
        return "$ --";
    }
    return value.toLocaleString(type === "crypto" ? "en-US" : "de-DE", {
        style: "currency",
        currency: "USD",
        minimumFractionDigits: type === "crypto" ? (value < 10 ? 4 : 2) : 2,
        maximumFractionDigits: type === "crypto" ? (value < 10 ? 4 : 2) : 2
    });
}

function hexToRgb(hex) {
    // Einfache Hex-zu-RGB Konvertierung
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16)
    } : { r: 99, g: 102, b: 241 };
}

async function loadAssetHistory(symbol, period) {
    // Prüfe Cache
    if (historyCache[symbol] && historyCache[symbol][period]) {
        const cachedData = historyCache[symbol][period];
        const asset = appData.predictions[symbol];
        let colorHex = "#f59e0b";
        if (asset) {
            if (asset.recommendation === "Starker Kauf") colorHex = "#10b981";
            else if (asset.recommendation === "Kauf") colorHex = "#34d399";
            else if (asset.recommendation === "Verkauf") colorHex = "#f43f5e";
            else if (asset.recommendation === "Starker Verkauf") colorHex = "#e11d48";
        }
        renderChart(cachedData, symbol, colorHex);
        return;
    }
    
    showChartLoading(true);
    
    try {
        const response = await fetch(`${API_BASE}/api/history/${symbol}?period=${period}`);
        if (!response.ok) {
            throw new Error(`Fehler beim Laden der Kursdaten (HTTP ${response.status})`);
        }
        const data = await response.json();
        
        // Im Cache sichern
        if (!historyCache[symbol]) historyCache[symbol] = {};
        historyCache[symbol][period] = data.history;
        
        const asset = appData.predictions[symbol];
        let colorHex = "#f59e0b";
        if (asset) {
            if (asset.recommendation === "Starker Kauf") colorHex = "#10b981";
            else if (asset.recommendation === "Kauf") colorHex = "#34d399";
            else if (asset.recommendation === "Verkauf") colorHex = "#f43f5e";
            else if (asset.recommendation === "Starker Verkauf") colorHex = "#e11d48";
        }
        
        if (selectedAsset === symbol && selectedPeriod === period) {
            renderChart(data.history, symbol, colorHex);
        }
    } catch (error) {
        console.error("Fehler beim Laden der historischen Kursdaten:", error);
        // Fallback: Nutze die in den Predictions eingebettete Standard-Historie
        const asset = appData.predictions[symbol];
        if (asset && asset.history) {
            let colorHex = "#f59e0b";
            if (asset.recommendation === "Starker Kauf") colorHex = "#10b981";
            else if (asset.recommendation === "Kauf") colorHex = "#34d399";
            else if (asset.recommendation === "Verkauf") colorHex = "#f43f5e";
            else if (asset.recommendation === "Starker Verkauf") colorHex = "#e11d48";
            renderChart(asset.history, symbol, colorHex);
        }
    } finally {
        showChartLoading(false);
    }
}

function showChartLoading(isLoading) {
    let overlay = document.getElementById('chart-loading-overlay');
    if (isLoading) {
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'chart-loading-overlay';
            overlay.className = 'chart-loading-overlay';
            overlay.innerHTML = `<div class="spinner"></div>`;
            elements.chartContainer.appendChild(overlay);
        }
    } else {
        if (overlay) {
            overlay.remove();
        }
    }
}

// ==========================================
// Portfolio Planner & AI Advisor Functions
// ==========================================

let portfolioInitialized = false;

function switchView(viewId) {
    const navAlerts = document.getElementById("nav-alerts");
    const alertsView = document.getElementById("alerts-view");
    const navSettings = document.getElementById("nav-settings");
    const settingsView = document.getElementById("settings-view");
    
    elements.navMarkets.classList.remove("active");
    elements.navPortfolio.classList.remove("active");
    if (navAlerts) navAlerts.classList.remove("active");
    if (navSettings) navSettings.classList.remove("active");
    
    elements.marketsView.classList.add("hidden");
    elements.marketsView.classList.remove("active");
    elements.portfolioView.classList.add("hidden");
    elements.portfolioView.classList.remove("active");
    if (alertsView) {
        alertsView.classList.add("hidden");
        alertsView.classList.remove("active");
    }
    if (settingsView) {
        settingsView.classList.add("hidden");
        settingsView.classList.remove("active");
    }
    
    if (viewId === "markets-view") {
        elements.navMarkets.classList.add("active");
        elements.marketsView.classList.add("active");
        elements.marketsView.classList.remove("hidden");
    } else if (viewId === "portfolio-view") {
        elements.navPortfolio.classList.add("active");
        elements.portfolioView.classList.add("active");
        elements.portfolioView.classList.remove("hidden");
        renderPortfolio();
        loadRiskSummary();
        loadEconomicCalendar();
        loadDailySummary();
    } else if (viewId === "alerts-view" && alertsView) {
        if (navAlerts) navAlerts.classList.add("active");
        alertsView.classList.add("active");
        alertsView.classList.remove("hidden");
        renderAlerts();
    } else if (viewId === "settings-view" && settingsView) {
        if (navSettings) navSettings.classList.add("active");
        settingsView.classList.add("active");
        settingsView.classList.remove("hidden");
        loadSettings();
    }
}

async function initPortfolio() {
    if (portfolioInitialized) return;
    
    try {
        await loadPortfolios();
        const response = await fetch(`${API_BASE}/api/portfolio?portfolio_id=${currentPortfolioId}`);
        if (!response.ok) {
            throw new Error(`Fehler beim Laden des Portfolios vom Server (HTTP ${response.status})`);
        }
        portfolio = await response.json();
        
        // Fallback-Seeding falls die DB noch leer ist
        if (!portfolio || portfolio.length === 0) {
            console.log("Portfolio ist leer in der DB. Seeding Standard-Werte...");
            const defaultHoldings = [
                { symbol: "AAPL", quantity: 10, buy_price: 175.0 },
                { symbol: "BTC-USD", quantity: 0.1, buy_price: 60000.0 },
                { symbol: "GC=F", quantity: 2.0, buy_price: 2000.0 }
            ];
            for (const item of defaultHoldings) {
                await fetch(`${API_BASE}/api/portfolio?portfolio_id=${currentPortfolioId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(item)
                });
            }
            // Nochmals abrufen nach dem Seeding
            const response2 = await fetch(`${API_BASE}/api/portfolio?portfolio_id=${currentPortfolioId}`);
            portfolio = await response2.json();
        }
        
    } catch (e) {
        console.error("Fehler beim Initialisieren des Server-Portfolios, Fallback auf localStorage...", e);
        // Fallback zu localStorage falls Server nicht erreichbar oder Fehler auftritt
        const stored = localStorage.getItem('finance_ai_portfolio');
        if (stored) {
            try {
                portfolio = JSON.parse(stored);
            } catch (e2) {
                portfolio = [];
            }
        }
        if (!portfolio || portfolio.length === 0) {
            portfolio = [
                { symbol: "AAPL", quantity: 10, buy_price: 175.0 },
                { symbol: "BTC-USD", quantity: 0.1, buy_price: 60000.0 },
                { symbol: "GC=F", quantity: 2.0, buy_price: 2000.0 }
            ];
        }
    }
    
    portfolioInitialized = true;
}

function populateAssetDropdown() {
    if (!elements.invAsset) return;
    elements.invAsset.innerHTML = '';
    
    const assets = Object.values(appData.predictions);
    assets.sort((a, b) => a.symbol.localeCompare(b.symbol));
    
    assets.forEach(asset => {
        const option = document.createElement('option');
        option.value = asset.symbol;
        const typeText = asset.type === 'crypto' ? 'Krypto' : (asset.type === 'stock' ? 'Aktie' : 'Rohstoff');
        option.textContent = `${asset.symbol} - ${asset.name} (${typeText})`;
        elements.invAsset.appendChild(option);
    });
}

function renderPortfolio() {
    if (!elements.holdingsListBody) return;
    
    if (portfolio.length === 0) {
        elements.holdingsListBody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">
                    Keine Investments erfasst. Fügen Sie oben ein Wertpapier hinzu.
                </td>
            </tr>
        `;
        elements.portTotalValue.innerText = formatCurrency(0, 'stock');
        elements.portTotalCost.innerText = formatCurrency(0, 'stock');
        elements.portTotalProfit.innerText = `${formatCurrency(0, 'stock')} (+0.00%)`;
        elements.portTotalProfit.className = "stat-value";
        elements.portPerformanceCard.style.border = '';
        elements.portPerformanceCard.style.background = '';
        return;
    }
    
    elements.holdingsListBody.innerHTML = '';
    let totalValue = 0;
    let totalCost = 0;
    
    portfolio.forEach((item, index) => {
        const asset = appData.predictions[item.symbol];
        const currentPrice = asset ? asset.price : item.buy_price;
        const assetType = asset ? asset.type : 'stock';
        const assetName = asset ? asset.name : item.symbol;
        
        const cost = item.quantity * item.buy_price;
        const value = item.quantity * currentPrice;
        
        totalCost += cost;
        totalValue += value;
        
        const profitLoss = value - cost;
        const profitLossPct = cost > 0 ? (profitLoss / cost) * 100 : 0;
        const sign = profitLoss >= 0 ? '+' : '';
        const colorClass = profitLoss >= 0 ? 'text-green' : 'text-red';
        
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>
                <div style="display: flex; flex-direction: column;">
                    <span style="font-weight: 600; color: white;">${item.symbol}</span>
                    <span style="font-size: 0.75rem; color: var(--text-muted);">${assetName}</span>
                </div>
            </td>
            <td>${item.quantity.toLocaleString('de-DE', { maximumFractionDigits: 6 })}</td>
            <td>${formatCurrency(item.buy_price, assetType)}</td>
            <td>${formatCurrency(currentPrice, assetType)}</td>
            <td style="font-weight: 600; color: white;">${formatCurrency(value, assetType)}</td>
            <td class="${colorClass}" style="font-weight: 500;">
                ${sign}${formatCurrency(profitLoss, assetType)}<br>
                <span style="font-size: 0.75rem; font-weight: normal;">${sign}${profitLossPct.toFixed(2)}%</span>
            </td>
            <td>
                <button class="btn-delete-inv" data-index="${index}" title="Löschen">
                    <i data-lucide="trash-2" style="width: 16px; height: 16px;"></i>
                </button>
            </td>
        `;
        elements.holdingsListBody.appendChild(tr);
    });
    
    // Register delete handlers
    elements.holdingsListBody.querySelectorAll('.btn-delete-inv').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const idx = parseInt(e.currentTarget.dataset.index);
            deleteHolding(idx);
        });
    });
    
    // Reinitialize Lucide Icons for dynamic content
    if (window.lucide) {
        window.lucide.createIcons();
    }
    
    // Recalculate portfolio metrics
    const totalProfitLoss = totalValue - totalCost;
    const totalProfitLossPct = totalCost > 0 ? (totalProfitLoss / totalCost) * 100 : 0;
    
    elements.portTotalValue.innerText = formatCurrency(totalValue, 'stock');
    elements.portTotalCost.innerText = formatCurrency(totalCost, 'stock');
    
    const overallSign = totalProfitLoss >= 0 ? '+' : '';
    const overallColorClass = totalProfitLoss >= 0 ? 'text-green' : 'text-red';
    
    elements.portTotalProfit.className = `stat-value ${overallColorClass}`;
    elements.portTotalProfit.innerText = `${overallSign}${formatCurrency(totalProfitLoss, 'stock')} (${overallSign}${totalProfitLossPct.toFixed(2)}%)`;
    
    // Performance card aesthetics
    if (totalProfitLoss >= 0) {
        elements.portPerformanceCard.style.border = '1px solid rgba(16, 185, 129, 0.2)';
        elements.portPerformanceCard.style.background = 'linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(255, 255, 255, 0.01) 100%)';
    } else {
        elements.portPerformanceCard.style.border = '1px solid rgba(244, 63, 94, 0.2)';
        elements.portPerformanceCard.style.background = 'linear-gradient(135deg, rgba(244, 63, 94, 0.1) 0%, rgba(255, 255, 255, 0.01) 100%)';
    }
    
    // Render charts row
    const chartsRow = document.getElementById("portfolio-charts-row");
    if (chartsRow) {
        if (portfolio.length > 0) {
            chartsRow.classList.remove("hidden");
            renderAllocationChart();
            renderDividendCalendar();
        } else {
            chartsRow.classList.add("hidden");
        }
    }
}

async function handleAddInvestment(e) {
    e.preventDefault();
    const symbol = elements.invAsset.value;
    const qty = parseFloat(elements.invQty.value);
    const buyPrice = parseFloat(elements.invPrice.value);
    
    if (!symbol || isNaN(qty) || qty <= 0 || isNaN(buyPrice) || buyPrice <= 0) {
        showToast("Bitte geben Sie eine gültige Menge und einen Kaufpreis ein.", "warning");
        return;
    }
    
    // Check if it's already in the portfolio
    let finalQty = qty;
    let finalBuyPrice = buyPrice;
    
    const existing = portfolio.find(item => item.symbol === symbol);
    if (existing) {
        finalQty = existing.quantity + qty;
        finalBuyPrice = ((existing.quantity * existing.buy_price) + (qty * buyPrice)) / finalQty;
    }
    
    const item = { symbol, quantity: finalQty, buy_price: finalBuyPrice };
    
    try {
        const response = await fetch(`${API_BASE}/api/portfolio?portfolio_id=${currentPortfolioId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(item)
        });
        
        if (!response.ok) {
            throw new Error(`Fehler beim Speichern des Investments auf dem Server (HTTP ${response.status})`);
        }
        
        // Reload portfolio from server
        const reloadResponse = await fetch(`${API_BASE}/api/portfolio?portfolio_id=${currentPortfolioId}`);
        if (reloadResponse.ok) {
            portfolio = await reloadResponse.json();
        }
        
        localStorage.setItem('finance_ai_portfolio', JSON.stringify(portfolio));
        renderPortfolio();
        
        // Clear inputs
        elements.invQty.value = '';
        elements.invPrice.value = '';
        
    } catch (error) {
        console.error("Fehler beim Hinzufügen des Investments:", error);
        showToast(error.message, "error");
    }
}

async function deleteHolding(idx) {
    const item = portfolio[idx];
    if (!item) return;
    
    try {
        const response = await fetch(`${API_BASE}/api/portfolio/${item.symbol}?portfolio_id=${currentPortfolioId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error(`Fehler beim Löschen des Investments auf dem Server (HTTP ${response.status})`);
        }
        
        portfolio.splice(idx, 1);
        localStorage.setItem('finance_ai_portfolio', JSON.stringify(portfolio));
        renderPortfolio();
    } catch (error) {
        console.error("Fehler beim Löschen des Investments:", error);
        showToast(error.message, "error");
    }
}

async function handleAddAsset(e) {
    e.preventDefault();
    const symbol = elements.addAssetSymbol.value.trim().toUpperCase();
    const name = elements.addAssetName.value.trim();
    const type = elements.addAssetType.value;
    
    if (!symbol || !name || !type) {
        showToast("Bitte füllen Sie alle Felder aus.", "warning");
        return;
    }
    
    // Disable form submission button while adding
    const submitBtn = elements.addAssetForm.querySelector("button[type='submit']");
    const originalHTML = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<div class="spinner" style="width: 14px; height: 14px; border-width: 2px; display: inline-block;"></div> Hinzufügen...`;
    
    try {
        const response = await fetch(`${API_BASE}/api/assets`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ symbol, name, type })
        });
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Fehler beim Hinzufügen des Assets.");
        }
        
        // Clear inputs and collapse form
        elements.addAssetSymbol.value = "";
        elements.addAssetName.value = "";
        elements.addAssetForm.classList.add("collapsed");
        
        // Reset toggle button state
        const icon = elements.toggleAddAssetBtn.querySelector("i, svg");
        const text = elements.toggleAddAssetBtn.querySelector("span");
        if (icon) icon.setAttribute("data-lucide", "plus-circle");
        if (text) text.innerText = "Asset beobachten";
        if (window.lucide) window.lucide.createIcons();
        
        // Show status as updating and fetch updated predictions/status
        setUpdatingUI(true);
        if (!statusPollingInterval) {
            statusPollingInterval = setInterval(pollStatus, 3000);
        }
        
        // Refresh local predictions
        fetchData();
        
        // Success notification
        showToast(`Asset ${symbol} wurde erfolgreich zur Watchlist hinzugefügt. Analyse läuft im Hintergrund.`, "success");
    } catch (error) {
        console.error("Fehler beim Hinzufügen des Assets:", error);
        showToast(error.message, "error");
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalHTML;
    }
}

async function handleDeleteAsset() {
    if (!selectedAsset) return;
    
    const confirmDelete = confirm(`Möchten Sie das Asset ${selectedAsset} wirklich aus der Watchlist löschen?`);
    if (!confirmDelete) return;
    
    try {
        const response = await fetch(`${API_BASE}/api/assets/${selectedAsset}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error(`Fehler beim Löschen des Assets (HTTP ${response.status})`);
        }
        
        // Clear selected asset and load the list again
        selectedAsset = null;
        elements.detailContent.classList.add("hidden");
        elements.noSelectionMsg.classList.remove("hidden");
        
        // Refresh local predictions
        fetchData();
        
        // Success notification
        showToast("Asset erfolgreich aus Watchlist gelöscht.", "success");
    } catch (error) {
        console.error("Fehler beim Löschen des Assets:", error);
        showToast(error.message, "error");
    }
}

async function analyzePortfolioWithAI() {
    if (portfolio.length === 0) {
        showToast("Fügen Sie Ihrem Portfolio mindestens ein Investment hinzu, bevor Sie die Analyse starten.", "warning");
        return;
    }
    
    elements.analyzePortfolioBtn.disabled = true;
    const originalBtnHTML = elements.analyzePortfolioBtn.innerHTML;
    elements.analyzePortfolioBtn.innerHTML = `<div class="spinner" style="width: 16px; height: 16px; border-width: 2px; display: inline-block;"></div> &nbsp; Analysiere...`;
    
    try {
        const response = await fetch(`${API_BASE}/api/portfolio/analyze`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                holdings: portfolio,
                strategy: selectedStrategy
            })
        });
        
        if (!response.ok) {
            throw new Error(`Fehler bei der KI-Analyse: ${response.statusText}`);
        }
        
        const report = await response.json();
        renderAiReport(report);
    } catch (error) {
        console.error("Fehler bei der KI-Portfolio-Analyse:", error);
        showToast("Die Portfolio-Analyse konnte nicht durchgeführt werden. Bitte überprüfen Sie Ihre Internetverbindung oder ob der Server läuft.", "error");
    } finally {
        elements.analyzePortfolioBtn.disabled = false;
        elements.analyzePortfolioBtn.innerHTML = originalBtnHTML;
    }
}

function renderAiReport(report) {
    if (!elements.portfolioAiReport) return;
    
    elements.portfolioAiReport.classList.remove('hidden');
    
    const score = report.portfolio_score !== undefined ? report.portfolio_score : 80;
    elements.portAiScore.innerText = `${score}%`;
    
    let colorHex = "#f59e0b"; // Yellow
    if (score >= 80) colorHex = "#10b981"; // Green
    else if (score < 50) colorHex = "#f43f5e"; // Red
    
    updatePortScoreRing(score, colorHex);
    
    elements.portAiSummary.innerText = report.advice_summary || "Keine Zusammenfassung verfügbar.";
    
    // Suggestions
    elements.portAiSuggestions.innerHTML = '';
    if (report.suggestions && report.suggestions.length > 0) {
        report.suggestions.forEach(s => {
            const li = document.createElement('li');
            li.innerText = s;
            elements.portAiSuggestions.appendChild(li);
        });
    } else {
        elements.portAiSuggestions.innerHTML = '<li>Keine Verbesserungsvorschläge. Das Portfolio entspricht der gewählten Strategie.</li>';
    }
    
    // Expected yields / dividends
    elements.portAiDividends.innerText = report.estimated_dividends || "Keine Dividenden-Schätzung verfügbar.";
    
    // Tips
    elements.portAiTips.innerHTML = '';
    if (report.tips && report.tips.length > 0) {
        report.tips.forEach(t => {
            const li = document.createElement('li');
            li.innerText = t;
            elements.portAiTips.appendChild(li);
        });
    } else {
        elements.portAiTips.innerHTML = '<li>Keine Tipps verfügbar.</li>';
    }
    
    // Forecasts buy/sell
    elements.portAiForecastsBody.innerHTML = '';
    if (report.forecasts && Object.keys(report.forecasts).length > 0) {
        Object.entries(report.forecasts).forEach(([symbol, info]) => {
            const tr = document.createElement('tr');
            
            let actionColorClass = 'text-yellow';
            let actionText = info.action || 'Halten';
            if (actionText === 'Kauf') actionColorClass = 'text-green';
            else if (actionText === 'Verkauf') actionColorClass = 'text-red';
            
            tr.innerHTML = `
                <td style="font-weight: 600; color: white;">${symbol}</td>
                <td class="${actionColorClass}" style="font-weight: 600;">${actionText}</td>
                <td style="font-weight: 500; color: var(--text-secondary);">${info.buy_percentage}%</td>
            `;
            elements.portAiForecastsBody.appendChild(tr);
        });
    } else {
        elements.portAiForecastsBody.innerHTML = `
            <tr>
                <td colspan="3" style="text-align: center; color: var(--text-muted);">
                    Keine Prognosen vorhanden.
                </td>
            </tr>
        `;
    }
    
    // Smooth scroll into view
    elements.portfolioAiReport.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

async function runPaperTradingSummary() {
    const summaryEl = document.getElementById('paper-trading-summary');
    if (!summaryEl) return;

    const trades = portfolio.map(item => ({
        symbol: item.symbol,
        type: 'BUY',
        quantity: item.quantity,
        price: item.buy_price
    }));

    try {
        const response = await fetch(`${API_BASE}/api/paper-trading/portfolio`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ portfolio_id: currentPortfolioId, trades })
        });
        if (!response.ok) throw new Error('Paper Trading konnte nicht geladen werden.');
        const data = await response.json();
        summaryEl.innerText = data.summary;
    } catch (error) {
        summaryEl.innerText = error.message;
    }
}

async function loadRiskSummary() {
    const container = document.getElementById('risk-summary-card');
    if (!container) return;

    try {
        const response = await fetch(`${API_BASE}/api/risk/summary?portfolio_id=${currentPortfolioId}`);
        if (!response.ok) throw new Error('Risikodaten konnten nicht geladen werden.');
        const data = await response.json();
        container.innerHTML = `Risk-Level: <strong>${data.risk_level}</strong><br>Volatilität: <strong>${data.volatility}%</strong><br>Max. Drawdown: <strong>${data.max_drawdown}%</strong><br><small>${data.details}</small>`;
    } catch (error) {
        container.innerText = error.message;
    }
}

async function loadDailySummary() {
    const container = document.getElementById('daily-summary-card');
    if (!container) return;

    try {
        const response = await fetch(`${API_BASE}/api/portfolio/daily-summary`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ portfolio_id: currentPortfolioId, strategy: selectedStrategy })
        });
        if (!response.ok) throw new Error('Tageszusammenfassung konnte nicht geladen werden.');
        const data = await response.json();
        container.innerHTML = `<strong>${data.headline}</strong><br>${data.summary}<br><br><small>${(data.recommendations || []).join(' ')}</small>`;
    } catch (error) {
        container.innerText = error.message;
    }
}

async function loadEconomicCalendar() {
    const list = document.getElementById('economic-calendar-list');
    if (!list) return;

    try {
        const response = await fetch(`${API_BASE}/api/economic-calendar`);
        if (!response.ok) throw new Error('Wirtschaftskalender konnte nicht geladen werden.');
        const data = await response.json();
        list.innerHTML = (data.events || []).map(event => `<li><strong>${event.date}</strong> - ${event.title} (${event.impact})<br><small>${event.summary}</small></li>`).join('');
    } catch (error) {
        list.innerHTML = `<li>${error.message}</li>`;
    }
}

function updatePortScoreRing(percent, color) {
    const circle = elements.portScoreRing;
    if (!circle) return;
    const radius = circle.r.baseVal.value;
    const circumference = radius * 2 * Math.PI;
    
    circle.style.strokeDasharray = `${circumference} ${circumference}`;
    const offset = circumference - (percent / 100 * circumference);
    circle.style.strokeDashoffset = offset;
    circle.style.stroke = color;
}

// ==========================================
// New Feature Helper & Logic Functions
// ==========================================

function getRecColorHex(recommendation) {
    if (recommendation === "Starker Kauf") return "#10b981";
    if (recommendation === "Kauf") return "#34d399";
    if (recommendation === "Verkauf") return "#f43f5e";
    if (recommendation === "Starker Verkauf") return "#e11d48";
    return "#f59e0b"; // Halten / default
}

async function handleAutocompleteSymbol() {
    const symbol = elements.addAssetSymbol.value.trim().toUpperCase();
    if (!symbol) return;
    
    // Check local popular list first
    const popularAssets = {
        "AAPL": { name: "Apple Inc.", type: "stock" },
        "MSFT": { name: "Microsoft Corp.", type: "stock" },
        "NVDA": { name: "NVIDIA Corp.", type: "stock" },
        "TSLA": { name: "Tesla Inc.", type: "stock" },
        "AMZN": { name: "Amazon.com Inc.", type: "stock" },
        "GOOGL": { name: "Alphabet Inc.", type: "stock" },
        "META": { name: "Meta Platforms Inc.", type: "stock" },
        "NFLX": { name: "Netflix Inc.", type: "stock" },
        "AMD": { name: "Advanced Micro Devices", type: "stock" },
        "BTC-USD": { name: "Bitcoin", type: "crypto" },
        "ETH-USD": { name: "Ethereum", type: "crypto" },
        "SOL-USD": { name: "Solana", type: "crypto" },
        "GC=F": { name: "Gold", type: "commodity" },
        "SI=F": { name: "Silber", type: "commodity" },
        "CL=F": { name: "Rohöl", type: "commodity" }
    };
    
    if (popularAssets[symbol]) {
        elements.addAssetName.value = popularAssets[symbol].name;
        elements.addAssetType.value = popularAssets[symbol].type;
        return;
    }
    
    // Query backend search API
    try {
        const response = await fetch(`${API_BASE}/api/search/${symbol}`);
        if (response.ok) {
            const data = await response.json();
            if (data.name) elements.addAssetName.value = data.name;
            if (data.type) elements.addAssetType.value = data.type;
        }
    } catch (e) {
        console.error("Fehler beim Autovervollständigen des Symbols:", e);
    }
}

async function fetchAccuracy() {
    try {
        const response = await fetch(`${API_BASE}/api/accuracy`);
        const valElem = document.getElementById('ai-accuracy-val');
        const descElem = document.getElementById('ai-accuracy-desc');
        if (!valElem || !descElem) return;
        
        if (response.ok) {
            const data = await response.json();
            if (data.total_evaluated > 0) {
                valElem.innerText = `${data.accuracy}%`;
                descElem.innerText = `Erfolgsquote (${data.correct_count}/${data.total_evaluated} Prognosen)`;
                
                valElem.className = "stat-value";
                if (data.accuracy >= 75) {
                    valElem.classList.add("text-green");
                } else if (data.accuracy < 50) {
                    valElem.classList.add("text-red");
                }
            } else {
                valElem.innerText = "-";
                descElem.innerText = "Nicht genügend historische Daten";
            }
        } else {
            valElem.innerText = "-";
            descElem.innerText = "Fehler beim Laden";
        }
    } catch (e) {
        console.error("Fehler beim Laden der KI-Genauigkeit:", e);
    }
}

function renderAllocationChart() {
    const chartCard = document.getElementById('portfolio-chart-card');
    if (!chartCard) return;
    
    if (portfolio.length === 0) {
        chartCard.classList.add('hidden');
        return;
    }
    
    chartCard.classList.remove('hidden');
    
    const dataMap = {};
    let totalValue = 0;
    
    portfolio.forEach(item => {
        const asset = appData.predictions[item.symbol];
        const currentPrice = asset ? asset.price : item.buy_price;
        const value = item.quantity * currentPrice;
        
        if (dataMap[item.symbol]) {
            dataMap[item.symbol] += value;
        } else {
            dataMap[item.symbol] = value;
        }
        totalValue += value;
    });
    
    if (totalValue === 0) {
        chartCard.classList.add('hidden');
        return;
    }
    
    const labels = Object.keys(dataMap);
    const values = Object.values(dataMap);
    const percentages = values.map(v => ((v / totalValue) * 100).toFixed(1));
    
    const colorPalette = [
        '#6366f1', // Electric Indigo
        '#10b981', // Mint Green
        '#3b82f6', // Bright Blue
        '#f59e0b', // Amber
        '#ec4899', // Pink
        '#8b5cf6', // Purple
        '#f43f5e', // Rose Red
        '#14b8a6', // Teal
        '#06b6d4', // Cyan
        '#f97316'  // Orange
    ];
    
    const colors = labels.map((_, i) => colorPalette[i % colorPalette.length]);
    const ctx = document.getElementById('portfolioAllocationChart').getContext('2d');
    
    if (window.portfolioChartInstance) {
        window.portfolioChartInstance.destroy();
    }
    
    window.portfolioChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderWidth: 1,
                borderColor: '#0b0f19',
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: '#9ca3af',
                        font: {
                            family: 'Inter',
                            size: 11
                        },
                        boxWidth: 12,
                        padding: 10,
                        generateLabels: function(chart) {
                            const data = chart.data;
                            if (data.labels.length && data.datasets.length) {
                                return data.labels.map(function(label, i) {
                                    const percent = percentages[i];
                                    return {
                                        text: `${label}: ${percent}%`,
                                        fillStyle: data.datasets[0].backgroundColor[i],
                                        strokeStyle: data.datasets[0].backgroundColor[i],
                                        lineWidth: 0,
                                        hidden: false,
                                        index: i
                                    };
                                });
                            }
                            return [];
                        }
                    }
                },
                tooltip: {
                    backgroundColor: '#1e293b',
                    titleColor: '#f3f4f6',
                    bodyColor: '#f3f4f6',
                    borderColor: 'rgba(255,255,255,0.08)',
                    borderWidth: 1,
                    callbacks: {
                        label: function(context) {
                            const value = context.parsed;
                            const percent = percentages[context.dataIndex];
                            return ` ${context.label}: ${value.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})} $ (${percent}%)`;
                        }
                    }
                }
            },
            cutout: '65%'
        }
    });
}


// ==========================================================================
// PREMIUM FEATURES IMPLEMENTATIONS (EUR/USD, Alerts, Dividends, Simulator)
// ==========================================================================

// 1. Currency Toggle Logic
async function initCurrencyToggle() {
    const btn = document.getElementById("currency-toggle-btn");
    const label = document.getElementById("currency-toggle-label");
    if (!btn || !label) return;

    // Fetch initial exchange rate
    try {
        const res = await fetch(`${API_BASE}/api/exchange-rate`);
        if (res.ok) {
            const data = await res.json();
            exchangeRate = data.rate || 0.92;
        }
    } catch (e) {
        console.error("Fehler beim Laden des USD/EUR Wechselkurses:", e);
    }

    btn.addEventListener("click", () => {
        if (currentCurrency === "USD") {
            currentCurrency = "EUR";
            label.innerText = "EUR (€)";
            btn.setAttribute("aria-label", "Währung wechseln. Aktuell: EUR");
        } else {
            currentCurrency = "USD";
            label.innerText = "USD ($)";
            btn.setAttribute("aria-label", "Währung wechseln. Aktuell: USD");
        }
        
        // Re-render UI with new currency
        renderAssetsList();
        if (selectedAsset) {
            selectAsset(selectedAsset);
        }
        renderPortfolio();
    });
}

// 2. Alerts Logic (DSGVO compliant, WCAG legible)
async function initAlerts() {
    const form = document.getElementById("create-alert-form");
    if (!form) return;

    // Periodic check for triggered alerts (Simulate real-time checking every 10 seconds)
    if (!triggeredAlertsInterval) {
        triggeredAlertsInterval = setInterval(checkTriggeredAlerts, 10000);
    }

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const symbol = document.getElementById("alert-symbol").value;
        const alert_type = document.getElementById("alert-type").value;
        const target_value = document.getElementById("alert-value").value.trim();

        if (!symbol || !alert_type || !target_value) {
            showToast("Bitte füllen Sie alle Felder aus.", "warning");
            return;
        }

        try {
            const res = await fetch(`${API_BASE}/api/alerts`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ symbol, alert_type, target_value })
            });

            if (!res.ok) throw new Error("Alarm konnte nicht erstellt werden.");
            
            showToast(`Alarm für ${symbol} erfolgreich aktiviert!`, "success");
            form.reset();
            renderAlerts();
        } catch (err) {
            showToast(err.message, "error");
        }
    });
}

async function renderAlerts() {
    const tbody = document.getElementById("alerts-list-body");
    const select = document.getElementById("alert-symbol");
    const countElem = document.getElementById("total-alerts-val");
    if (!tbody || !select) return;

    // Fill select with watchlist assets
    select.innerHTML = "";
    Object.keys(appData.predictions).sort().forEach(sym => {
        const opt = document.createElement("option");
        opt.value = sym;
        opt.innerText = sym;
        select.appendChild(opt);
    });

    try {
        const res = await fetch(`${API_BASE}/api/alerts`);
        if (!res.ok) throw new Error("Fehler beim Laden der Alarme.");
        const alerts = await res.json();

        activeAlerts = alerts;
        if (countElem) countElem.innerText = alerts.length;

        if (alerts.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;padding:1.5rem;color:var(--text-muted)">Keine aktiven Alarme eingerichtet.</td></tr>`;
            return;
        }

        const typeMap = {
            "price_above": "Preis über",
            "price_below": "Preis unter",
            "rsi_above": "RSI über",
            "rsi_below": "RSI unter",
            "rec_change": "KI-Empfehlung ist"
        };

        tbody.innerHTML = alerts.map(alert => {
            let valStr = alert.target_value;
            if (alert.alert_type.startsWith("price")) {
                valStr = formatCurrency(parseFloat(alert.target_value), "stock");
            }
            
            return `<tr>
                <td><strong>${alert.symbol}</strong></td>
                <td>${typeMap[alert.alert_type] || alert.alert_type}</td>
                <td><span style="font-weight:600;color:white;">${valStr}</span></td>
                <td style="color:var(--text-secondary)">${alert.created_at}</td>
                <td>
                    <button class="btn-delete-asset" onclick="deleteAlert(${alert.id})" title="Alarm löschen">
                        <i data-lucide="trash-2" style="width:16px;height:16px;"></i>
                    </button>
                </td>
            </tr>`;
        }).join("");

        if (window.lucide) window.lucide.createIcons();
    } catch (err) {
        console.error("Fehler beim Rendern der Alarme:", err);
    }
}

async function deleteAlert(id) {
    try {
        const res = await fetch(`${API_BASE}/api/alerts/${id}`, { method: "DELETE" });
        if (!res.ok) throw new Error("Löschen fehlgeschlagen.");
        showToast("Alarm gelöscht.", "success");
        renderAlerts();
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function checkTriggeredAlerts() {
    try {
        const res = await fetch(`${API_BASE}/api/alerts/triggered`);
        if (!res.ok) return;
        const triggered = await res.json();

        triggered.forEach(alert => {
            const typeMap = {
                "price_above": "Preis über",
                "price_below": "Preis unter",
                "rsi_above": "RSI über",
                "rsi_below": "RSI unter",
                "rec_change": "KI-Empfehlung geändert auf"
            };

            let valStr = alert.target_value;
            if (alert.alert_type.startsWith("price")) {
                valStr = formatCurrency(parseFloat(alert.target_value), "stock");
            }

            const title = `🚨 ALARM AUSGELÖST: ${alert.symbol}`;
            const message = `${alert.symbol} hat die Bedingung '${typeMap[alert.alert_type]}' bei ${valStr} erfüllt!`;

            // Browser Notification
            if (Notification && Notification.permission === "granted") {
                new Notification(title, { body: message });
            }

            // In-app premium toast
            showToast(message, "warning", title);
        });

        if (triggered.length > 0) {
            // Update alerts panel if currently showing
            const alertsView = document.getElementById("alerts-view");
            if (alertsView && !alertsView.classList.contains("hidden")) {
                renderAlerts();
            }
        }
    } catch (err) {
        console.error("Fehler bei der Alarmprüfung:", err);
    }
}

// 3. Dividend Calendar rendering
async function renderDividendCalendar() {
    const canvas = document.getElementById("portfolioDividendChart");
    if (!canvas) return;

    try {
        const res = await fetch(`${API_BASE}/api/portfolio/dividends?portfolio_id=${currentPortfolioId}`);
        if (!res.ok) throw new Error("Fehler beim Laden des Dividendenplans.");
        const data = await res.json();

        const ctx = canvas.getContext("2d");
        if (window.portfolioDividendChartInstance) {
            window.portfolioDividendChartInstance.destroy();
        }

        const months = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"];
        const monthlyData = Object.values(data.monthly_dividends);
        
        // Convert to selected currency
        const convertedData = monthlyData.map(val => {
            if (currentCurrency === "EUR") {
                return val / exchangeRate;
            }
            return val;
        });

        // Set estimated dividend yield description
        const divDescElem = document.getElementById("port-ai-dividends");
        if (divDescElem) {
            const currencySymbol = currentCurrency === "EUR" ? "€" : "$";
            const formattedTotal = (data.annual_total / (currentCurrency === "EUR" ? exchangeRate : 1)).toLocaleString("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
            divDescElem.innerHTML = `Geschätzte jährliche Ausschüttung: <strong>${formattedTotal} ${currencySymbol}</strong>.<br><small style="color:var(--text-muted)">Die Verteilung basiert auf historischen Ausschüttungsmonaten des vergangenen Jahres.</small>`;
        }

        window.portfolioDividendChartInstance = new Chart(ctx, {
            type: "bar",
            data: {
                labels: months,
                datasets: [{
                    label: `Ertrag (${currentCurrency === "EUR" ? "€" : "$"})`,
                    data: convertedData,
                    backgroundColor: "rgba(99, 102, 241, 0.45)",
                    borderColor: "var(--accent)",
                    borderWidth: 1.5,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        grid: { color: "rgba(255, 255, 255, 0.02)" },
                        ticks: { color: "#9ca3af" }
                    },
                    y: {
                        grid: { color: "rgba(255, 255, 255, 0.03)" },
                        ticks: {
                            color: "#9ca3af",
                            callback: function(value) {
                                return value.toLocaleString("de-DE") + (currentCurrency === "EUR" ? " €" : " $");
                            }
                        }
                    }
                }
            }
        });
    } catch (e) {
        console.error("Fehler beim Laden des Dividenden-Charts:", e);
    }
}

// 4. Backtest Strategy Simulator tab logic
function initBacktestModal() {
    const card = document.getElementById("accuracy-card");
    const modal = document.getElementById("backtest-modal");
    const closeBtn = document.getElementById("close-backtest-modal");
    if (!card || !modal || !closeBtn) return;

    card.addEventListener("click", openBacktestModal);
    closeBtn.addEventListener("click", () => modal.classList.add("hidden"));
    modal.addEventListener("click", (e) => { if (e.target === modal) modal.classList.add("hidden"); });

    // Tabs inside modal
    const tabAccuracy = document.getElementById("modal-tab-accuracy");
    const tabSimulator = document.getElementById("modal-tab-simulator");
    const contentAccuracy = document.getElementById("tab-content-accuracy");
    const contentSimulator = document.getElementById("tab-content-simulator");

    if (tabAccuracy && tabSimulator) {
        tabAccuracy.addEventListener("click", () => {
            tabAccuracy.classList.add("active");
            tabSimulator.classList.remove("active");
            contentAccuracy.classList.add("active");
            contentAccuracy.classList.remove("hidden");
            contentSimulator.classList.add("hidden");
            contentSimulator.classList.remove("active");
        });

        tabSimulator.addEventListener("click", () => {
            tabSimulator.classList.add("active");
            tabAccuracy.classList.remove("active");
            contentSimulator.classList.add("active");
            contentSimulator.classList.remove("hidden");
            contentAccuracy.classList.add("hidden");
            contentAccuracy.classList.remove("active");
            
            // Setup simulator dropdown
            const simAssetSelect = document.getElementById("sim-asset");
            if (simAssetSelect) {
                simAssetSelect.innerHTML = "";
                Object.keys(appData.predictions).sort().forEach(sym => {
                    const opt = document.createElement("option");
                    opt.value = sym;
                    opt.innerText = sym;
                    simAssetSelect.appendChild(opt);
                });
            }
        });
    }

    const runSimBtn = document.getElementById("run-sim-btn");
    runSimBtn?.addEventListener("click", runSimulator);
}

async function openBacktestModal() {
    const modal = document.getElementById("backtest-modal");
    const tbody = document.getElementById("backtest-tbody");
    const summary = document.getElementById("backtest-summary");
    if (!modal) return;

    modal.classList.remove("hidden");
    if (window.lucide) window.lucide.createIcons();

    tbody.innerHTML = `<tr><td colspan="8" class="backtest-loading"><div class="spinner" style="width:18px;height:18px;border-width:2px;display:inline-block;"></div>&nbsp;Lade...</td></tr>`;
    summary.innerHTML = "";

    try {
        const res = await fetch(`${API_BASE}/api/backtest`);
        if (!res.ok) throw new Error("Backtest-Daten konnten nicht geladen werden.");
        const data = await res.json();

        if (!data || data.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:3rem;color:var(--text-secondary);">Noch keine Prognose-Historie vorhanden.<br><small>Starte eine Analyse, um Daten zu sammeln.</small></td></tr>`;
            summary.innerHTML = `<div class="backtest-stat-pill"><span class="pill-label">Einträge</span><span class="pill-value">0</span></div>`;
            return;
        }

        const total = data.length;
        const correct = data.filter(d => d.is_correct).length;
        const accuracy = total > 0 ? ((correct / total) * 100).toFixed(1) : 0;
        const accClass = parseFloat(accuracy) >= 60 ? "pill-success" : parseFloat(accuracy) >= 40 ? "pill-accent" : "pill-error";

        summary.innerHTML = `
            <div class="backtest-stat-pill pill-accent"><span class="pill-label">Prognosen gesamt</span><span class="pill-value">${total}</span></div>
            <div class="backtest-stat-pill pill-success"><span class="pill-label">Korrekt</span><span class="pill-value">${correct}</span></div>
            <div class="backtest-stat-pill pill-error"><span class="pill-label">Falsch</span><span class="pill-value">${total - correct}</span></div>
            <div class="backtest-stat-pill ${accClass}"><span class="pill-label">Trefferquote</span><span class="pill-value">${accuracy}%</span></div>
        `;

        const recColorMap = {
            "Starker Kauf": "var(--color-strong-buy)", "Kauf": "var(--color-buy)",
            "Halten": "var(--color-hold)", "Verkauf": "var(--color-sell)", "Starker Verkauf": "var(--color-strong-sell)"
        };

        const fmtPrice = (v) => v ? v.toLocaleString("de-DE", {minimumFractionDigits:2, maximumFractionDigits:2}) : "-";

        tbody.innerHTML = data.map(row => {
            const change = row.pred_price > 0 ? (((row.current_price - row.pred_price) / row.pred_price) * 100).toFixed(2) : 0;
            const changeColor = change >= 0 ? "var(--color-buy)" : "var(--color-sell)";
            const resultBadge = row.is_correct
                ? `<span class="backtest-result-badge correct">\u2713 Korrekt</span>`
                : `<span class="backtest-result-badge wrong">\u2717 Falsch</span>`;
            const recColor = recColorMap[row.recommendation] || "var(--text-primary)";
            const dateStr = row.last_updated ? new Date(row.last_updated).toLocaleDateString("de-DE") : "-";

            return `<tr>
                <td><strong>${row.symbol}</strong><br><small style="color:var(--text-muted)">${row.name}</small></td>
                <td><span style="color:${recColor};font-weight:600">${row.recommendation}</span></td>
                <td>${row.confidence}%</td>
                <td>${fmtPrice(row.pred_price)}</td>
                <td>${fmtPrice(row.current_price)}</td>
                <td style="color:${changeColor};font-weight:600">${change >= 0 ? "+" : ""}${change}%</td>
                <td>${resultBadge}</td>
                <td style="color:var(--text-secondary)">${dateStr}</td>
            </tr>`;
        }).join("");

    } catch (err) {
        console.error("Backtest Fehler:", err);
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:2rem;color:var(--color-sell);">Fehler beim Laden: ${err.message}</td></tr>`;
    }
}

async function runSimulator() {
    const symbol = document.getElementById("sim-asset").value;
    const strategy = document.getElementById("sim-strategy").value;
    const years = document.getElementById("sim-years").value;
    const resultsArea = document.getElementById("sim-results-area");
    const runBtn = document.getElementById("run-sim-btn");
    
    if (!symbol) return;
    
    runBtn.disabled = true;
    runBtn.innerHTML = `<div class="spinner" style="width:14px;height:14px;border-width:2px;display:inline-block;"></div> Rechnet...`;
    
    try {
        const res = await fetch(`${API_BASE}/api/backtest/simulate?symbol=${symbol}&strategy=${strategy}&years=${years}`);
        if (!res.ok) throw new Error("Fehler beim Simulieren.");
        const data = await res.json();
        
        resultsArea.classList.remove("hidden");
        
        const currencySymbol = currentCurrency === "EUR" ? "€" : "$";
        const convertMultiplier = currentCurrency === "EUR" ? (1 / exchangeRate) : 1;
        
        document.getElementById("sim-final-value").innerText = `${(data.final_value * convertMultiplier).toLocaleString("de-DE", {maximumFractionDigits:2})} ${currencySymbol}`;
        document.getElementById("sim-strat-return").innerText = `${data.strategy_return >= 0 ? "+" : ""}${data.strategy_return}%`;
        document.getElementById("sim-strat-return").className = `sim-stat-value ${data.strategy_return >= 0 ? "text-green" : "text-red"}`;
        document.getElementById("sim-bh-return").innerText = `${data.buy_hold_return >= 0 ? "+" : ""}${data.buy_hold_return}%`;
        document.getElementById("sim-bh-return").className = `sim-stat-value ${data.buy_hold_return >= 0 ? "text-green" : "text-red"}`;
        document.getElementById("sim-trades").innerText = data.total_trades;
        
        // Plot simulation chart
        const ctx = document.getElementById("simulatorChart").getContext("2d");
        if (window.simulatorChartInstance) {
            window.simulatorChartInstance.destroy();
        }
        
        const dates = data.history.map(h => new Date(h.date).toLocaleDateString("de-DE", {month: "short", year: "2-digit"}));
        const stratVals = data.history.map(h => h.strategy_val * convertMultiplier);
        const bhVals = data.history.map(h => h.buy_hold_val * convertMultiplier);
        
        window.simulatorChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: dates,
                datasets: [
                    {
                        label: 'Strategie',
                        data: stratVals,
                        borderColor: '#6366f1',
                        borderWidth: 2,
                        pointRadius: 0,
                        fill: false
                    },
                    {
                        label: 'Buy & Hold',
                        data: bhVals,
                        borderColor: 'rgba(255, 255, 255, 0.4)',
                        borderWidth: 1.5,
                        borderDash: [4, 4],
                        pointRadius: 0,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: { color: '#9ca3af' }
                    }
                },
                scales: {
                    x: {
                        grid: { color: "rgba(255, 255, 255, 0.02)" },
                        ticks: { color: "#9ca3af", maxTicksLimit: 12 }
                    },
                    y: {
                        grid: { color: "rgba(255, 255, 255, 0.03)" },
                        ticks: {
                            color: "#9ca3af",
                            callback: function(value) {
                                return value.toLocaleString("de-DE") + ` ${currencySymbol}`;
                            }
                        }
                    }
                }
            }
        });
        
    } catch (err) {
        showToast(err.message, "error");
    } finally {
        runBtn.disabled = false;
        runBtn.innerHTML = "Simulation starten";
    }
}

// 5. AlphaChat Quick Actions & Command Parser
function initChatWidget() {
    const bubbleBtn = document.getElementById("chat-bubble-btn");
    const chatPanel = document.getElementById("chat-panel");
    const closeChatBtn = document.getElementById("close-chat-btn");
    const chatForm = document.getElementById("chat-input-form");
    const chatInput = document.getElementById("chat-input");
    const sendBtn = document.getElementById("chat-send-btn");
    const clearChatBtn = document.getElementById("clear-chat-btn");

    if (!bubbleBtn || !chatPanel) return;

    bubbleBtn.addEventListener("click", () => {
        chatPanel.classList.toggle("hidden");
        if (!chatPanel.classList.contains("hidden")) {
            if (window.lucide) window.lucide.createIcons();
            loadChatHistory();
            setTimeout(() => chatInput.focus(), 50);
        }
    });

    closeChatBtn?.addEventListener("click", () => chatPanel.classList.add("hidden"));

    clearChatBtn?.addEventListener("click", async () => {
        if (confirm("Möchten Sie den Chatverlauf für dieses Portfolio wirklich löschen?")) {
            try {
                const res = await fetch(`${API_BASE}/api/portfolio/${currentPortfolioId}/chat`, {
                    method: "DELETE"
                });
                if (res.ok) {
                    showToast("Chatverlauf erfolgreich gelöscht.", "success");
                    loadChatHistory();
                }
            } catch (e) {
                showToast(e.message, "error");
            }
        }
    });

    // Quick Action Click Handlers
    document.querySelectorAll(".quick-action-chip").forEach(chip => {
        chip.addEventListener("click", () => {
            const query = chip.getAttribute("data-query");
            chatInput.value = query;
            chatForm.dispatchEvent(new Event("submit"));
        });
    });

    chatForm?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const msg = chatInput.value.trim();
        if (!msg) return;

        appendChatMessage(msg, "user");
        chatInput.value = "";
        sendBtn.disabled = true;

        const typingEl = appendTypingIndicator();

        try {
            const res = await fetch(`${API_BASE}/api/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: msg, portfolio_id: currentPortfolioId })
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            typingEl.remove();
            appendChatMessage(data.response || "Keine Antwort erhalten.", "bot");
            
            // If command executed successfully and asked for data reload
            if (data.trigger_refresh) {
                fetchData();
            }
        } catch (err) {
            typingEl.remove();
            appendChatMessage(`Entschuldigung, Fehler: ${err.message}`, "bot");
        } finally {
            sendBtn.disabled = false;
            chatInput.focus();
        }
    });
}

async function loadChatHistory() {
    const container = document.getElementById("chat-messages");
    if (!container) return;
    
    // Clear all messages except the first welcome message
    container.innerHTML = `
        <div class="chat-message bot-message">
            <div class="chat-msg-bubble">
                <strong>Hallo!</strong> Ich bin dein AlphaPulse KI-Berater. 👋<br><br>
                Frag mich z.B.: <em>„Wie steht mein Portfolio?“</em> oder <em>„Was denkst du über AAPL?“</em>
            </div>
        </div>
    `;
    
    try {
        const res = await fetch(`${API_BASE}/api/portfolio/${currentPortfolioId}/chat`);
        if (res.ok) {
            const history = await res.json();
            history.forEach(h => {
                appendChatMessage(h.message, h.sender);
            });
        }
    } catch (e) {
        console.error("Fehler beim Laden des Chatverlaufs:", e);
    }
}

function appendChatMessage(text, role) {
    const container = document.getElementById("chat-messages");
    if (!container) return null;

    const msgDiv = document.createElement("div");
    msgDiv.className = `chat-message ${role === "user" ? "user-message" : "bot-message"}`;
    const bubble = document.createElement("div");
    bubble.className = "chat-msg-bubble";
    bubble.innerHTML = text
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*(.+?)\*/g, "<em>$1</em>")
        .replace(/\n/g, "<br>");
    msgDiv.appendChild(bubble);
    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
    return msgDiv;
}

function appendTypingIndicator() {
    const container = document.getElementById("chat-messages");
    if (!container) return document.createElement("div");

    const msgDiv = document.createElement("div");
    msgDiv.className = "chat-message bot-message chat-typing-indicator";
    msgDiv.innerHTML = `<div class="chat-msg-bubble">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    </div>`;
    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
    return msgDiv;
}


// --- NEW PREMIUM FEATURES: PORTFOLIO MANAGEMENT, TAX SIMULATOR & SETTINGS ---

let currentPortfolioId = 1;

// Sub-Tab Switcher
function setupPortfolioSubTabs() {
    const tabs = document.querySelectorAll(".portfolio-sub-tab");
    tabs.forEach(tab => {
        tab.addEventListener("click", (e) => {
            tabs.forEach(t => t.classList.remove("active"));
            e.currentTarget.classList.add("active");
            
            const targetPane = e.currentTarget.dataset.portTab;
            document.querySelectorAll(".portfolio-tab-pane").forEach(pane => {
                pane.classList.remove("active");
                if (pane.id === targetPane) {
                    pane.classList.add("active");
                }
            });
            
            if (targetPane === "transactions-tab-content") {
                loadTransactions();
            } else if (targetPane === "rebalance-tab-content") {
                loadRebalanceData();
            }
        });
    });
}

// Load Portfolios & Setup Profile Dropdown
async function loadPortfolios() {
    try {
        const res = await fetch(`${API_BASE}/api/portfolios`);
        if (res.ok) {
            const list = await res.json();
            const select = document.getElementById("portfolio-profile-select");
            if (select) {
                select.innerHTML = list.map(p => `<option value="${p.id}">${p.name}</option>`).join("");
                select.value = currentPortfolioId;
            }
        }
    } catch (e) {
        console.error("Fehler beim Laden der Portfolio-Liste:", e);
    }
}

// Load Portfolio Data Helper
async function loadPortfolioData() {
    try {
        const response = await fetch(`${API_BASE}/api/portfolio?portfolio_id=${currentPortfolioId}`);
        if (!response.ok) {
            throw new Error(`Fehler beim Laden des Portfolios vom Server (HTTP ${response.status})`);
        }
        portfolio = await response.json();
    } catch (e) {
        console.error("Fehler beim Laden der Portfolio-Daten:", e);
    }
}

// Create Portfolio Profile
async function handleCreatePortfolio() {
    const name = prompt("Geben Sie einen Namen für das neue Portfolio ein:");
    if (!name || !name.trim()) return;
    try {
        const res = await fetch(`${API_BASE}/api/portfolios`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: name.trim() })
        });
        if (res.ok) {
            showToast(`Portfolio '${name}' erfolgreich erstellt.`, "success");
            await loadPortfolios();
            const listRes = await fetch(`${API_BASE}/api/portfolios`);
            if (listRes.ok) {
                const list = await listRes.json();
                const found = list.find(p => p.name === name.trim());
                if (found) {
                    const select = document.getElementById("portfolio-profile-select");
                    if (select) {
                        select.value = found.id;
                        select.dispatchEvent(new Event("change"));
                    }
                }
            }
        } else {
            const err = await res.json();
            showToast(err.detail || "Erstellen fehlgeschlagen.", "error");
        }
    } catch (e) {
        showToast(e.message, "error");
    }
}

// Delete Portfolio Profile
async function handleDeletePortfolio() {
    if (currentPortfolioId === 1) {
        showToast("Das Standard-Portfolio darf nicht gelöscht werden.", "warning");
        return;
    }
    const confirmDel = confirm("Möchten Sie dieses Portfolio-Profil wirklich löschen? Alle Bestände und Transaktionen werden unwiderruflich gelöscht.");
    if (!confirmDel) return;
    try {
        const res = await fetch(`${API_BASE}/api/portfolios/${currentPortfolioId}`, {
            method: "DELETE"
        });
        if (res.ok) {
            showToast("Portfolio erfolgreich gelöscht.", "success");
            currentPortfolioId = 1;
            await loadPortfolios();
            const select = document.getElementById("portfolio-profile-select");
            if (select) select.value = 1;
            await loadPortfolioData();
            renderPortfolio();
        } else {
            const err = await res.json();
            showToast(err.detail || "Löschen fehlgeschlagen.", "error");
        }
    } catch (e) {
        showToast(e.message, "error");
    }
}

// Populate watchlist dropdowns for transactions & tax simulator
function populateTransactionDropdowns() {
    const txSelect = document.getElementById("tx-asset");
    const taxSelect = document.getElementById("tax-asset");
    if (!appData.predictions) return;
    const assets = Object.values(appData.predictions);
    assets.sort((a, b) => a.symbol.localeCompare(b.symbol));
    
    [txSelect, taxSelect].forEach(select => {
        if (select) {
            select.innerHTML = assets.map(a => `<option value="${a.symbol}">${a.symbol} - ${a.name}</option>`).join("");
        }
    });
}

// Transactions list & add transaction
async function loadTransactions() {
    const tbody = document.getElementById("transactions-list-body");
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="7" class="text-center"><div class="spinner" style="width:16px;height:16px;border-width:2px;display:inline-block;"></div> Lade Transaktionen...</td></tr>`;
    try {
        const res = await fetch(`${API_BASE}/api/portfolio/${currentPortfolioId}/transactions`);
        if (res.ok) {
            const txs = await res.json();
            if (txs.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" class="text-center" style="color: var(--text-muted)">Keine Transaktionen erfasst.</td></tr>`;
                return;
            }
            tbody.innerHTML = txs.map(t => {
                const total = t.quantity * t.price;
                const typeText = t.type === "BUY" ? "Kauf" : "Verkauf";
                const typeClass = t.type === "BUY" ? "text-green" : "text-red";
                return `<tr>
                    <td>${t.date}</td>
                    <td><strong>${t.symbol}</strong><br><small style="color:var(--text-muted)">${t.name || ""}</small></td>
                    <td class="${typeClass}" style="font-weight:600">${typeText}</td>
                    <td>${t.quantity}</td>
                    <td>${formatCurrency(t.price, "stock")}</td>
                    <td>${formatCurrency(total, "stock")}</td>
                    <td>
                        <button class="btn-delete-inv" onclick="deleteTransaction(${t.id})" title="Löschen">
                            <i data-lucide="trash-2" style="width:16px;height:16px;"></i>
                        </button>
                    </td>
                </tr>`;
            }).join("");
            if (window.lucide) window.lucide.createIcons();
        }
    } catch (e) {
        console.error("Fehler beim Laden der Transaktionen:", e);
    }
}

async function handleAddTransaction(e) {
    e.preventDefault();
    const symbol = document.getElementById("tx-asset").value;
    const type = document.getElementById("tx-type").value;
    const quantity = parseFloat(document.getElementById("tx-qty").value);
    const price = parseFloat(document.getElementById("tx-price").value);
    const date = document.getElementById("tx-date").value;
    
    if (!symbol || !type || isNaN(quantity) || quantity <= 0 || isNaN(price) || price <= 0 || !date) {
        showToast("Bitte füllen Sie alle Felder aus.", "warning");
        return;
    }
    
    try {
        const res = await fetch(`${API_BASE}/api/portfolio/${currentPortfolioId}/transactions`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ symbol, type, quantity, price, date })
        });
        if (res.ok) {
            showToast("Transaktion erfolgreich gebucht.", "success");
            document.getElementById("add-transaction-form").reset();
            await loadPortfolioData();
            renderPortfolio();
            loadTransactions();
        }
    } catch (e) {
        showToast(e.message, "error");
    }
}

async function deleteTransaction(txId) {
    try {
        const res = await fetch(`${API_BASE}/api/portfolio/${currentPortfolioId}/transactions/${txId}`, {
            method: "DELETE"
        });
        if (res.ok) {
            showToast("Transaktion gelöscht.", "success");
            await loadPortfolioData();
            renderPortfolio();
            loadTransactions();
        }
    } catch (e) {
        showToast(e.message, "error");
    }
}

// FIFO Tax Simulation
async function handleTaxSimulation(e) {
    e.preventDefault();
    const symbol = document.getElementById("tax-asset").value;
    const sell_quantity = parseFloat(document.getElementById("tax-qty").value);
    const sell_price = parseFloat(document.getElementById("tax-price").value);
    
    if (!symbol || isNaN(sell_quantity) || sell_quantity <= 0 || isNaN(sell_price) || sell_price <= 0) {
        showToast("Bitte füllen Sie alle Felder aus.", "warning");
        return;
    }
    
    try {
        const res = await fetch(`${API_BASE}/api/portfolio/${currentPortfolioId}/tax-simulate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ symbol, sell_quantity, sell_price })
        });
        if (res.ok) {
            const data = await res.json();
            document.getElementById("tax-simulation-results").classList.remove("hidden");
            document.getElementById("tax-res-revenue").innerText = formatCurrency(data.revenue, "stock");
            document.getElementById("tax-res-cost").innerText = formatCurrency(data.total_cost, "stock");
            
            const profitClass = data.profit >= 0 ? "text-green" : "text-red";
            document.getElementById("tax-res-profit").innerText = formatCurrency(data.profit, "stock");
            document.getElementById("tax-res-profit").className = `tax-value ${profitClass}`;
            
            document.getElementById("tax-res-tax").innerText = formatCurrency(data.tax, "stock");
            
            const matchedList = document.getElementById("tax-res-matched-list");
            if (data.matched_buys && data.matched_buys.length > 0) {
                matchedList.innerHTML = data.matched_buys.map(b => 
                    `<li>Kauf am ${b.buy_date}: ${b.quantity} Stück für je ${formatCurrency(b.buy_price, "stock")} (Kosten: ${formatCurrency(b.cost, "stock")})</li>`
                ).join("");
            } else {
                matchedList.innerHTML = "<li>Keine passenden Käufe gefunden. Haben Sie ausreichend BUY Transaktionen verbucht?</li>";
            }
            if (data.unmatched_quantity > 0) {
                matchedList.innerHTML += `<li style="color:var(--color-hold)">Warnung: Für ${data.unmatched_quantity} Stück wurden keine passenden Käufe in der Historie gefunden! (Fehlbestand)</li>`;
            }
        }
    } catch (e) {
        showToast(e.message, "error");
    }
}

// Load & Save AI Settings
async function loadSettings() {
    try {
        const res = await fetch(`${API_BASE}/api/settings`);
        if (res.ok) {
            const data = await res.json();
            const toneEl = document.getElementById("setting-ai-tone");
            const promptEl = document.getElementById("setting-custom-prompt");
            if (toneEl) toneEl.value = data.ai_tone;
            if (promptEl) promptEl.value = data.custom_prompt;
            
            // Set notification configuration fields
            const tgToken = document.getElementById("visible-setting-tg-token");
            const tgChatId = document.getElementById("visible-setting-tg-chatid");
            const dcWebhook = document.getElementById("visible-setting-dc-webhook");
            const mailServer = document.getElementById("visible-setting-mail-server");
            const mailPort = document.getElementById("visible-setting-mail-port");
            const mailSender = document.getElementById("visible-setting-mail-sender");
            const mailPassword = document.getElementById("visible-setting-mail-password");
            const mailRecipient = document.getElementById("visible-setting-mail-recipient");

            if (tgToken) tgToken.value = data.telegram_bot_token || "";
            if (tgChatId) tgChatId.value = data.telegram_chat_id || "";
            if (dcWebhook) dcWebhook.value = data.discord_webhook_url || "";
            if (mailServer) mailServer.value = data.email_smtp_server || "";
            if (mailPort) mailPort.value = data.email_smtp_port || "";
            if (mailSender) mailSender.value = data.email_sender || "";
            if (mailPassword) mailPassword.value = data.email_password || "";
            if (mailRecipient) mailRecipient.value = data.email_recipient || "";
        }
    } catch (e) {
        console.error("Fehler beim Laden der Einstellungen:", e);
    }
}

async function handleSaveSettings(e) {
    if (e) e.preventDefault();
    const custom_prompt = document.getElementById("setting-custom-prompt").value;
    const ai_tone = document.getElementById("setting-ai-tone").value;
    
    const telegram_bot_token = document.getElementById("visible-setting-tg-token")?.value || "";
    const telegram_chat_id = document.getElementById("visible-setting-tg-chatid")?.value || "";
    const discord_webhook_url = document.getElementById("visible-setting-dc-webhook")?.value || "";
    const email_smtp_server = document.getElementById("visible-setting-mail-server")?.value || "";
    const email_smtp_port = document.getElementById("visible-setting-mail-port")?.value || "";
    const email_sender = document.getElementById("visible-setting-mail-sender")?.value || "";
    const email_password = document.getElementById("visible-setting-mail-password")?.value || "";
    const email_recipient = document.getElementById("visible-setting-mail-recipient")?.value || "";

    try {
        const res = await fetch(`${API_BASE}/api/settings`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                custom_prompt, ai_tone,
                telegram_bot_token, telegram_chat_id,
                discord_webhook_url,
                email_smtp_server, email_smtp_port,
                email_sender, email_password,
                email_recipient
            })
        });
        if (res.ok) {
            showToast("Einstellungen erfolgreich gespeichert. Die nächsten KI-Analysen verwenden dieses Profil.", "success");
        }
    } catch (e) {
        showToast(e.message, "error");
    }
}

async function saveAllSettingsSilently() {
    const custom_prompt = document.getElementById("setting-custom-prompt").value;
    const ai_tone = document.getElementById("setting-ai-tone").value;
    const telegram_bot_token = document.getElementById("visible-setting-tg-token")?.value || "";
    const telegram_chat_id = document.getElementById("visible-setting-tg-chatid")?.value || "";
    const discord_webhook_url = document.getElementById("visible-setting-dc-webhook")?.value || "";
    const email_smtp_server = document.getElementById("visible-setting-mail-server")?.value || "";
    const email_smtp_port = document.getElementById("visible-setting-mail-port")?.value || "";
    const email_sender = document.getElementById("visible-setting-mail-sender")?.value || "";
    const email_password = document.getElementById("visible-setting-mail-password")?.value || "";
    const email_recipient = document.getElementById("visible-setting-mail-recipient")?.value || "";

    const res = await fetch(`${API_BASE}/api/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            custom_prompt, ai_tone,
            telegram_bot_token, telegram_chat_id,
            discord_webhook_url,
            email_smtp_server, email_smtp_port,
            email_sender, email_password,
            email_recipient
        })
    });
    if (!res.ok) throw new Error("Konnte Einstellungen nicht zwischenspeichern.");
}

function setupNotificationTestButtons() {
    const btnTg = document.getElementById("btn-test-telegram");
    const btnDc = document.getElementById("btn-test-discord");
    const btnMail = document.getElementById("btn-test-email");

    btnTg?.addEventListener("click", async () => {
        const token = document.getElementById("visible-setting-tg-token").value;
        const chatId = document.getElementById("visible-setting-tg-chatid").value;
        if (!token || !chatId) {
            showToast("Bitte Bot Token und Chat ID ausfüllen.", "warning");
            return;
        }
        btnTg.disabled = true;
        try {
            await saveAllSettingsSilently();
            const res = await fetch(`${API_BASE}/api/settings/test-telegram`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: "AlphaPulse AI Telegram Testnachricht!" })
            });
            if (res.ok) {
                showToast("Telegram Testnachricht erfolgreich gesendet!", "success");
            } else {
                const err = await res.json();
                showToast(err.detail || "Telegram Test fehlgeschlagen.", "error");
            }
        } catch (e) {
            showToast(e.message, "error");
        } finally {
            btnTg.disabled = false;
        }
    });

    btnDc?.addEventListener("click", async () => {
        const webhook = document.getElementById("visible-setting-dc-webhook").value;
        if (!webhook) {
            showToast("Bitte Webhook URL ausfüllen.", "warning");
            return;
        }
        btnDc.disabled = true;
        try {
            await saveAllSettingsSilently();
            const res = await fetch(`${API_BASE}/api/settings/test-discord`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: "AlphaPulse AI Discord Testnachricht!" })
            });
            if (res.ok) {
                showToast("Discord Testnachricht erfolgreich gesendet!", "success");
            } else {
                const err = await res.json();
                showToast(err.detail || "Discord Test fehlgeschlagen.", "error");
            }
        } catch (e) {
            showToast(e.message, "error");
        } finally {
            btnDc.disabled = false;
        }
    });

    btnMail?.addEventListener("click", async () => {
        const server = document.getElementById("visible-setting-mail-server").value;
        const port = document.getElementById("visible-setting-mail-port").value;
        const sender = document.getElementById("visible-setting-mail-sender").value;
        const recipient = document.getElementById("visible-setting-mail-recipient").value;
        if (!server || !port || !sender || !recipient) {
            showToast("Bitte SMTP Server, Port, Absender und Empfänger ausfüllen.", "warning");
            return;
        }
        btnMail.disabled = true;
        try {
            await saveAllSettingsSilently();
            const res = await fetch(`${API_BASE}/api/settings/test-email`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: "AlphaPulse AI E-Mail Testnachricht!" })
            });
            if (res.ok) {
                showToast("E-Mail Testnachricht erfolgreich gesendet!", "success");
            } else {
                const err = await res.json();
                showToast(err.detail || "E-Mail Test fehlgeschlagen.", "error");
            }
        } catch (e) {
            showToast(e.message, "error");
        } finally {
            btnMail.disabled = false;
        }
    });
}

// Export triggers
function initExportButtons() {
    const btnCsv = document.getElementById("btn-export-csv");
    const btnPrint = document.getElementById("btn-export-print");
    
    if (btnCsv) {
        btnCsv.addEventListener("click", () => {
            window.location.href = `${API_BASE}/api/portfolio/${currentPortfolioId}/export/csv`;
        });
    }
    
    if (btnPrint) {
        btnPrint.addEventListener("click", () => {
            window.open(`${API_BASE}/api/portfolio/${currentPortfolioId}/export/print`, "_blank");
        });
    }
}

// ==========================================
// REBALANCING & ALLOCATION PLANER LOGIC
// ==========================================

async function loadRebalanceData() {
    try {
        const res = await fetch(`${API_BASE}/api/portfolio/${currentPortfolioId}/target-allocation`);
        if (res.ok) {
            const data = await res.json();
            document.getElementById("target-stock").value = data.stock || 50;
            document.getElementById("target-crypto").value = data.crypto || 30;
            document.getElementById("target-commodity").value = data.commodity || 20;
            
            updateRebalanceChart(data);
        }
    } catch (e) {
        console.error("Fehler beim Laden der Zielallokation:", e);
    }
}

function updateRebalanceChart(targetAlloc) {
    if (!appData.predictions) return;
    
    let totalVal = 0.0;
    let catValues = { stock: 0.0, crypto: 0.0, commodity: 0.0 };
    
    portfolio.forEach(item => {
        const symbol = item.symbol;
        const qty = item.quantity;
        const buyPrice = item.buy_price;
        
        const pred = appData.predictions[symbol] || {};
        const price = pred.price || buyPrice;
        const val = qty * price;
        totalVal += val;
        
        const atype = pred.type || "stock";
        if (catValues[atype] !== undefined) {
            catValues[atype] += val;
        }
    });
    
    const currentAlloc = {
        stock: totalVal > 0 ? (catValues.stock / totalVal * 100) : 0.0,
        crypto: totalVal > 0 ? (catValues.crypto / totalVal * 100) : 0.0,
        commodity: totalVal > 0 ? (catValues.commodity / totalVal * 100) : 0.0
    };
    
    const tStock = parseFloat(targetAlloc.stock) || 0.0;
    const tCrypto = parseFloat(targetAlloc.crypto) || 0.0;
    const tCommodity = parseFloat(targetAlloc.commodity) || 0.0;
    
    document.getElementById("bar-stock-current").style.width = `${currentAlloc.stock}%`;
    document.getElementById("bar-stock-target").style.left = `${tStock}%`;
    document.getElementById("alloc-stock-current-val").innerText = `${currentAlloc.stock.toFixed(1)}%`;
    document.getElementById("alloc-stock-target-val").innerText = `${tStock.toFixed(1)}%`;
    
    const diffStock = currentAlloc.stock - tStock;
    const stockDiffElem = document.getElementById("alloc-stock-diff");
    stockDiffElem.innerText = `${diffStock >= 0 ? "+" : ""}${diffStock.toFixed(1)}%`;
    stockDiffElem.className = diffStock >= 5.0 ? "text-positive bg-positive" : diffStock <= -5.0 ? "text-negative bg-negative" : "text-muted bg-neutral";

    document.getElementById("bar-crypto-current").style.width = `${currentAlloc.crypto}%`;
    document.getElementById("bar-crypto-target").style.left = `${tCrypto}%`;
    document.getElementById("alloc-crypto-current-val").innerText = `${currentAlloc.crypto.toFixed(1)}%`;
    document.getElementById("alloc-crypto-target-val").innerText = `${tCrypto.toFixed(1)}%`;
    
    const diffCrypto = currentAlloc.crypto - tCrypto;
    const cryptoDiffElem = document.getElementById("alloc-crypto-diff");
    cryptoDiffElem.innerText = `${diffCrypto >= 0 ? "+" : ""}${diffCrypto.toFixed(1)}%`;
    cryptoDiffElem.className = diffCrypto >= 5.0 ? "text-positive bg-positive" : diffCrypto <= -5.0 ? "text-negative bg-negative" : "text-muted bg-neutral";

    document.getElementById("bar-commodity-current").style.width = `${currentAlloc.commodity}%`;
    document.getElementById("bar-commodity-target").style.left = `${tCommodity}%`;
    document.getElementById("alloc-commodity-current-val").innerText = `${currentAlloc.commodity.toFixed(1)}%`;
    document.getElementById("alloc-commodity-target-val").innerText = `${tCommodity.toFixed(1)}%`;
    
    const diffCommodity = currentAlloc.commodity - tCommodity;
    const commodityDiffElem = document.getElementById("alloc-commodity-diff");
    commodityDiffElem.innerText = `${diffCommodity >= 0 ? "+" : ""}${diffCommodity.toFixed(1)}%`;
    commodityDiffElem.className = diffCommodity >= 5.0 ? "text-positive bg-positive" : diffCommodity <= -5.0 ? "text-negative bg-negative" : "text-muted bg-neutral";
}

async function handleSaveTargetAllocation(e) {
    e.preventDefault();
    const stock = parseFloat(document.getElementById("target-stock").value) || 0;
    const crypto = parseFloat(document.getElementById("target-crypto").value) || 0;
    const commodity = parseFloat(document.getElementById("target-commodity").value) || 0;
    
    const sum = stock + crypto + commodity;
    if (Math.abs(sum - 100) > 0.1) {
        showToast("Die Allokationswerte müssen in Summe genau 100% ergeben. (Aktuell: " + sum.toFixed(1) + "%)", "warning");
        return;
    }
    
    try {
        const res = await fetch(`${API_BASE}/api/portfolio/${currentPortfolioId}/target-allocation`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ stock, crypto, commodity })
        });
        if (res.ok) {
            showToast("Zielallokation erfolgreich gespeichert.", "success");
            updateRebalanceChart({ stock, crypto, commodity });
        } else {
            const err = await res.json();
            showToast(err.detail || "Fehler beim Speichern.", "error");
        }
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function analyzeRebalancing() {
    const reportPanel = document.getElementById("rebalance-ai-report");
    const summaryText = document.getElementById("rebalance-ai-summary");
    const tradesBody = document.getElementById("rebalance-trades-body");
    const tipsList = document.getElementById("rebalance-ai-tips");
    const btn = document.getElementById("rebalance-analyze-btn");
    
    if (!reportPanel || !btn) return;
    
    btn.disabled = true;
    btn.innerHTML = `<div class="spinner" style="width:14px;height:14px;border-width:2px;display:inline-block;"></div> Berechne...`;
    reportPanel.classList.remove("hidden");
    summaryText.innerText = "Lade Rebalancing-Bericht und KI-Ratschläge...";
    tradesBody.innerHTML = `<tr><td colspan="4" class="text-center">Analysiere Bestände...</td></tr>`;
    tipsList.innerHTML = "<li>Warte auf Antwort...</li>";
    
    try {
        const res = await fetch(`${API_BASE}/api/portfolio/${currentPortfolioId}/rebalance`);
        if (!res.ok) throw new Error("KI-Rebalancing-Dienst nicht erreichbar.");
        const data = await res.json();
        
        summaryText.innerHTML = data.advice_summary.replace(/\n/g, "<br>");
        
        if (data.recommended_trades && data.recommended_trades.length > 0) {
            tradesBody.innerHTML = data.recommended_trades.map(t => {
                const actionClass = t.action === "Kauf" ? "text-green" : "text-red";
                return `<tr>
                    <td><strong>${t.symbol}</strong></td>
                    <td class="${actionClass}" style="font-weight:600">${t.action}</td>
                    <td>${formatCurrency(t.amount_eur, "stock")}</td>
                    <td>${t.reason}</td>
                </tr>`;
            }).join("");
        } else {
            tradesBody.innerHTML = `<tr><td colspan="4" class="text-center" style="color:var(--text-muted)">Kein unmittelbarer Rebalancing-Bedarf vorhanden. Allokation liegt im Zielbereich.</td></tr>`;
        }
        
        if (data.rebalance_tips && data.rebalance_tips.length > 0) {
            tipsList.innerHTML = data.rebalance_tips.map(tip => `<li>${tip}</li>`).join("");
        } else {
            tipsList.innerHTML = "<li>Keine besonderen Hinweise.</li>";
        }
        
        if (data.target_allocation) {
            updateRebalanceChart(data.target_allocation);
        }
        
    } catch (e) {
        showToast(e.message, "error");
        summaryText.innerText = "Fehler beim Laden des Rebalancing-Berichts.";
        tradesBody.innerHTML = `<tr><td colspan="4" class="text-center text-red">Fehler: ${e.message}</td></tr>`;
        tipsList.innerHTML = `<li class="text-red">KI konnte keine Empfehlungen laden.</li>`;
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<i data-lucide="scale"></i> Rebalancing berechnen`;
        if (window.lucide) window.lucide.createIcons();
    }
}

/* ==========================================================================
   ENHANCED PHASE 1-3 FEATURES: HEATMAP, COMPARISON, CASH, CSV, BACKUP, CMD PALETTE
   ========================================================================== */

// --- 1. Heatmap View ---
function renderHeatmap() {
    const grid = document.getElementById("heatmap-grid");
    if (!grid) return;
    grid.innerHTML = "";
    
    const list = Object.values(appData.predictions || {});
    if (!list || list.length === 0) {
        grid.innerHTML = `<p class="text-center text-muted" style="padding: 20px;">Keine Daten für Heatmap vorhanden.</p>`;
        return;
    }
    
    list.forEach(asset => {
        const change = asset.price_change_1d || 0;
        const tile = document.createElement("div");
        tile.className = "heatmap-tile";
        
        let bgStyle = "rgba(255, 255, 255, 0.05)";
        if (change > 3) bgStyle = "rgba(16, 185, 129, 0.4)";
        else if (change > 0) bgStyle = "rgba(16, 185, 129, 0.2)";
        else if (change < -3) bgStyle = "rgba(239, 68, 68, 0.4)";
        else if (change < 0) bgStyle = "rgba(239, 68, 68, 0.2)";
        
        tile.style.background = bgStyle;
        tile.innerHTML = `
            <div class="heatmap-symbol">${asset.symbol}</div>
            <div class="heatmap-name">${asset.name}</div>
            <div class="heatmap-price">${formatCurrency(asset.price, asset.type)}</div>
            <div class="heatmap-change ${change >= 0 ? 'text-green' : 'text-red'}">${change >= 0 ? '+' : ''}${change.toFixed(2)}%</div>
        `;
        
        tile.addEventListener("click", () => {
            selectAsset(asset.symbol);
            document.getElementById("view-mode-list-btn")?.click();
        });
        
        grid.appendChild(tile);
    });
}

function setupViewModeToggles() {
    const listBtn = document.getElementById("view-mode-list-btn");
    const heatmapBtn = document.getElementById("view-mode-heatmap-btn");
    const assetsList = document.getElementById("assets-list");
    const heatmapGrid = document.getElementById("heatmap-grid");
    
    if (listBtn && heatmapBtn) {
        listBtn.addEventListener("click", () => {
            listBtn.classList.add("active");
            heatmapBtn.classList.remove("active");
            assetsList.classList.remove("hidden");
            heatmapGrid.classList.add("hidden");
        });
        
        heatmapBtn.addEventListener("click", () => {
            heatmapBtn.classList.add("active");
            listBtn.classList.remove("active");
            assetsList.classList.add("hidden");
            heatmapGrid.classList.remove("hidden");
            renderHeatmap();
        });
    }
}

// --- 2. Side-by-Side Asset Comparison Modal ---
function setupCompareModal() {
    const openBtn = document.getElementById("open-compare-btn");
    const modal = document.getElementById("compare-modal");
    const closeBtn = document.getElementById("close-compare-modal");
    const runBtn = document.getElementById("run-compare-btn");
    const input = document.getElementById("compare-symbols-input");
    
    if (openBtn && modal) {
        openBtn.addEventListener("click", () => {
            modal.classList.remove("hidden");
            if (input && !input.value) {
                input.value = "AAPL, MSFT, BTC-USD";
            }
            runAssetComparison();
        });
    }
    
    if (closeBtn && modal) {
        closeBtn.addEventListener("click", () => modal.classList.add("hidden"));
    }
    
    if (runBtn) {
        runBtn.addEventListener("click", runAssetComparison);
    }
}

async function runAssetComparison() {
    const input = document.getElementById("compare-symbols-input");
    const area = document.getElementById("compare-results-area");
    if (!input || !area) return;
    
    const symbols = input.value.trim();
    if (!symbols) {
        showToast("Bitte geben Sie mindestens ein Ticker-Symbol ein.", "warning");
        return;
    }
    
    area.innerHTML = `<div class="loading-state" style="padding: 30px;"><div class="spinner"></div><p>Lade Vergleichsdaten...</p></div>`;
    
    try {
        const res = await fetch(`${API_BASE}/api/compare?symbols=${encodeURIComponent(symbols)}`);
        if (!res.ok) throw new Error("Vergleichsdaten konnten nicht geladen werden.");
        const data = await res.json();
        
        if (!data || data.length === 0) {
            area.innerHTML = `<p class="text-center text-muted" style="padding: 20px;">Keine gültigen Assets für den Vergleich gefunden.</p>`;
            return;
        }
        
        let html = `<table class="compare-table"><thead><tr><th>Eigenschaft</th>`;
        data.forEach(item => {
            html += `<th><div class="compare-col-header"><strong>${item.symbol}</strong><br><small>${item.name}</small></div></th>`;
        });
        html += `</tr></thead><tbody>`;
        
        const rowsDef = [
            { label: "Aktueller Preis", key: "price", fmt: (v, item) => formatCurrency(v, item.type) },
            { label: "1D Veränderung", key: "price_change_1d", fmt: v => v != null ? `<span class="${v>=0?'text-green':'text-red'}">${v>=0?'+':''}${v.toFixed(2)}%</span>` : "--" },
            { label: "7D Veränderung", key: "price_change_7d", fmt: v => v != null ? `<span class="${v>=0?'text-green':'text-red'}">${v>=0?'+':''}${v.toFixed(2)}%</span>` : "--" },
            { label: "30D Veränderung", key: "price_change_30d", fmt: v => v != null ? `<span class="${v>=0?'text-green':'text-red'}">${v>=0?'+':''}${v.toFixed(2)}%</span>` : "--" },
            { label: "RSI (14)", key: "rsi", fmt: v => v != null ? v.toFixed(1) : "--" },
            { label: "SMA 20 / SMA 50", key: "sma_20", fmt: (v, item) => `${item.sma_20 ? '$'+item.sma_20.toFixed(2) : '--'} / ${item.sma_50 ? '$'+item.sma_50.toFixed(2) : '--'}` },
            { label: "EMA 200", key: "ema_200", fmt: v => v != null ? `$${v.toFixed(2)}` : "--" },
            { label: "KGV / P/E", key: "pe_ratio", fmt: v => v != null ? v.toFixed(2) : "--" },
            { label: "Marktkapitalisierung", key: "market_cap", fmt: v => v ? `$ ${(v/1e9).toFixed(2)} Mrd.` : "--" },
            { label: "52W Range", key: "fifty_two_high", fmt: (v, item) => (item.fifty_two_low && item.fifty_two_high) ? `$${item.fifty_two_low.toFixed(1)} - $${item.fifty_two_high.toFixed(1)}` : "--" },
            { label: "KI Empfehlung", key: "recommendation", fmt: (v, item) => `<strong>${v || 'Halten'}</strong> (${item.confidence || 50}%)` },
            { label: "Risiko Level", key: "risk_level", fmt: v => v || "Mittel" }
        ];
        
        rowsDef.forEach(row => {
            html += `<tr><td><strong>${row.label}</strong></td>`;
            data.forEach(item => {
                const val = item[row.key];
                html += `<td>${row.fmt(val, item)}</td>`;
            });
            html += `</tr>`;
        });
        
        html += `</tbody></table>`;
        area.innerHTML = html;
    } catch (e) {
        area.innerHTML = `<p class="text-center text-red" style="padding: 20px;">Fehler: ${e.message}</p>`;
    }
}

// --- 3. Cash Management & Performance Metrics ---
function setupCashManagement() {
    const cashCard = document.getElementById("cash-stat-card");
    const modal = document.getElementById("cash-modal");
    const closeBtn = document.getElementById("close-cash-modal");
    const form = document.getElementById("cash-form");
    
    if (cashCard && modal) {
        cashCard.addEventListener("click", () => {
            modal.classList.remove("hidden");
            fetchPortfolioCash();
        });
    }
    
    if (closeBtn && modal) {
        closeBtn.addEventListener("click", () => modal.classList.add("hidden"));
    }
    
    if (form) {
        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            const amount = parseFloat(document.getElementById("cash-input-amount").value);
            if (isNaN(amount) || amount < 0) {
                showToast("Bitte einen gültigen Betrag eingeben.", "warning");
                return;
            }
            try {
                const res = await fetch(`${API_BASE}/api/portfolio/${currentPortfolioId}/cash`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ cash_balance: amount })
                });
                if (!res.ok) throw new Error("Fehler beim Speichern des Cash-Bestands.");
                showToast("Cash-Bestand erfolgreich aktualisiert!", "success");
                modal.classList.add("hidden");
                loadPortfolioPerformanceMetrics();
            } catch (err) {
                showToast(err.message, "error");
            }
        });
    }
}

async function fetchPortfolioCash() {
    try {
        const res = await fetch(`${API_BASE}/api/portfolio/${currentPortfolioId}/cash`);
        if (!res.ok) return;
        const data = await res.json();
        const input = document.getElementById("cash-input-amount");
        if (input) input.value = data.cash_balance;
    } catch (e) {}
}

async function loadPortfolioPerformanceMetrics() {
    try {
        const res = await fetch(`${API_BASE}/api/portfolio/${currentPortfolioId}/performance-metrics`);
        if (!res.ok) return;
        const data = await res.json();
        
        const cashVal = document.getElementById("port-cash-val");
        if (cashVal) cashVal.innerText = formatCurrency(data.cash_balance, "stock");
        
        const sharpeDesc = document.getElementById("port-sharpe-desc");
        if (sharpeDesc) sharpeDesc.innerText = `Sharpe: ${data.sharpe_ratio.toFixed(2)} | CAGR: ${data.cagr.toFixed(1)}%`;
        
        const totalVal = document.getElementById("port-total-value");
        if (totalVal) totalVal.innerText = formatCurrency(data.total_portfolio_value, "stock");
    } catch (e) {}
}

// --- 4. Broker CSV Import Modal ---
function setupCsvImportModal() {
    const openBtn = document.getElementById("btn-import-csv");
    const modal = document.getElementById("csv-import-modal");
    const closeBtn = document.getElementById("close-csv-modal");
    const form = document.getElementById("csv-import-form");
    
    if (openBtn && modal) {
        openBtn.addEventListener("click", () => modal.classList.remove("hidden"));
    }
    if (closeBtn && modal) {
        closeBtn.addEventListener("click", () => modal.classList.add("hidden"));
    }
    
    if (form) {
        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            const text = document.getElementById("csv-textarea").value.trim();
            if (!text) {
                showToast("Bitte fügen Sie CSV-Text ein.", "warning");
                return;
            }
            try {
                const res = await fetch(`${API_BASE}/api/portfolio/${currentPortfolioId}/import-csv`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ csv_text: text })
                });
                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || "Fehler beim CSV-Import.");
                }
                const data = await res.json();
                showToast(data.message, "success");
                modal.classList.add("hidden");
                document.getElementById("csv-textarea").value = "";
                await loadPortfolioData();
                renderPortfolio();
                loadTransactions();
                fetchData();
            } catch (err) {
                showToast(err.message, "error");
            }
        });
    }
}

// --- 5. System Backup & Restore ---
function setupBackupRestore() {
    const backupBtn = document.getElementById("btn-backup-db");
    const restoreBtn = document.getElementById("btn-restore-db");
    
    if (backupBtn) {
        backupBtn.addEventListener("click", async () => {
            try {
                const res = await fetch(`${API_BASE}/api/system/backup`);
                if (!res.ok) throw new Error("Backup fehlgeschlagen.");
                const data = await res.json();
                const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `alphapulse_backup_${new Date().toISOString().slice(0,10)}.json`;
                a.click();
                URL.revokeObjectURL(url);
                showToast("Backup-Datei erfolgreich exportiert!", "success");
            } catch (e) {
                showToast(e.message, "error");
            }
        });
    }
    
    if (restoreBtn) {
        restoreBtn.addEventListener("click", () => {
            const input = document.createElement("input");
            input.type = "file";
            input.accept = ".json";
            input.onchange = async (e) => {
                const file = e.target.files[0];
                if (!file) return;
                const reader = new FileReader();
                reader.onload = async (evt) => {
                    try {
                        const json = JSON.parse(evt.target.result);
                        const res = await fetch(`${API_BASE}/api/system/restore`, {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify(json)
                        });
                        if (!res.ok) throw new Error("Wiederherstellung fehlgeschlagen.");
                        showToast("Datenbank erfolgreich wiederhergestellt!", "success");
                        fetchData();
                        await loadPortfolioData();
                        renderPortfolio();
                    } catch (err) {
                        showToast("Ungültige Backup-Datei: " + err.message, "error");
                    }
                };
                reader.readAsText(file);
            };
            input.click();
        });
    }
}

// --- 6. Command Palette (Ctrl + K) ---
function setupCommandPalette() {
    const modal = document.getElementById("command-palette-modal");
    const input = document.getElementById("palette-input");
    
    if (!modal || !input) return;
    
    document.addEventListener("keydown", (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
            e.preventDefault();
            modal.classList.remove("hidden");
            input.focus();
            input.value = "";
            renderPaletteResults("");
        } else if (e.key === "Escape" && !modal.classList.contains("hidden")) {
            modal.classList.add("hidden");
        }
    });
    
    modal.addEventListener("click", (e) => {
        if (e.target === modal) modal.classList.add("hidden");
    });
    
    input.addEventListener("input", (e) => {
        renderPaletteResults(e.target.value.trim().toLowerCase());
    });
}

function renderPaletteResults(query) {
    const results = document.getElementById("palette-results");
    if (!results) return;
    
    const actions = [
        { label: "Marktanalyse öffnen", icon: "line-chart", act: () => switchView("markets-view") },
        { label: "Portfolio Planer öffnen", icon: "wallet", act: () => switchView("portfolio-view") },
        { label: "Asset-Direktvergleich", icon: "columns", act: () => document.getElementById("open-compare-btn")?.click() },
        { label: "Broker CSV Import", icon: "upload", act: () => document.getElementById("btn-import-csv")?.click() },
        { label: "Einstellungen öffnen", icon: "settings", act: () => switchView("settings-view") }
    ];
    
    const list = Object.values(appData.predictions || {});
    list.forEach(asset => {
        actions.push({
            label: `${asset.symbol} - ${asset.name}`,
            icon: asset.type === 'crypto' ? 'coins' : 'bar-chart-2',
            act: () => {
                switchView("markets-view");
                selectAsset(asset.symbol);
            }
        });
    });
    
    const filtered = actions.filter(a => a.label.toLowerCase().includes(query));
    
    if (filtered.length === 0) {
        results.innerHTML = `<p class="text-center text-muted" style="padding:15px;">Keine Befehle oder Assets gefunden.</p>`;
        return;
    }
    
    results.innerHTML = `<div class="palette-group-title">Ergebnisse</div>` + filtered.map((a, i) => `
        <div class="palette-item ${i===0?'active':''}" data-index="${i}">
            <i data-lucide="${a.icon}"></i> ${a.label}
        </div>
    `).join("");
    
    if (window.lucide) window.lucide.createIcons();
    
    results.querySelectorAll(".palette-item").forEach((el, idx) => {
        el.addEventListener("click", () => {
            document.getElementById("command-palette-modal")?.classList.add("hidden");
            filtered[idx].act();
        });
    });
}

function switchView(viewId) {
    document.querySelectorAll(".nav-item").forEach(n => {
        if (n.dataset.view === viewId) n.click();
    });
}

// Auto-Initialize Enhanced Features on DOM Load
document.addEventListener("DOMContentLoaded", () => {
    setupViewModeToggles();
    setupCompareModal();
    setupCashManagement();
    setupCsvImportModal();
    setupBackupRestore();
    setupCommandPalette();
    
    ["toggle-ema200", "toggle-bollinger"].forEach(id => {
        const btn = document.getElementById(id);
        if (btn) {
            btn.addEventListener("click", () => {
                const active = btn.getAttribute("data-active") === "true";
                btn.setAttribute("data-active", !active);
                btn.classList.toggle("active");
                if (selectedAsset) renderChart(selectedAsset);
            });
        }
    });

    const tempInput = document.getElementById("setting-ai-temp");
    const tempValDisp = document.getElementById("temp-val-display");
    if (tempInput && tempValDisp) {
        tempInput.addEventListener("input", (e) => {
            tempValDisp.innerText = e.target.value;
        });
    }

    setupModalTabListeners();
    initSSEListener();
});


// Global Chart Instances for Monte-Carlo and DRIP
let mcChartInstance = null;
let dripChartInstance = null;

// PWA & Service Worker Registration
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js').then((reg) => {
            console.log('PWA Service Worker registriert:', reg);
        }).catch((err) => {
            console.warn('PWA Service Worker Fehler:', err);
        });
    });
}

// SSE Real-Time Updates Listener
function initSSEListener() {
    try {
        const evtSource = new EventSource(`${API_BASE}/api/events`);
        evtSource.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                if (data.event === 'update_completed') {
                    showToast("Marktdaten wurden im Hintergrund aktualisiert!", "info");
                    fetchData();
                    fetchAccuracy();
                }
            } catch (e) {
                console.error("SSE parse error", e);
            }
        };
    } catch (e) {
        console.warn("SSE event source error", e);
    }
}

// Monte-Carlo Simulation Runner
async function runMonteCarloSimulation() {
    const years = parseInt(document.getElementById("mc-years")?.value || "5");
    const numSims = parseInt(document.getElementById("mc-sims")?.value || "500");
    const resultsArea = document.getElementById("mc-results-area");

    try {
        const res = await fetch(`${API_BASE}/api/portfolio/1/monte-carlo`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ num_simulations: numSims, time_horizon_years: years })
        });
        if (!res.ok) throw new Error("Monte-Carlo Berechnung fehlgeschlagen");
        const data = await res.json();

        if (resultsArea) resultsArea.classList.remove("hidden");
        document.getElementById("mc-p5-val").innerText = formatCurrency(data.percentile_5);
        document.getElementById("mc-p50-val").innerText = formatCurrency(data.percentile_50_median);
        document.getElementById("mc-p95-val").innerText = formatCurrency(data.percentile_95);

        // Chart render
        const ctx = document.getElementById("monteCarloChart")?.getContext("2d");
        if (ctx) {
            if (mcChartInstance) mcChartInstance.destroy();
            const labels = data.sample_trajectories[0].map((_, i) => `T${i+1}`);
            const colors = ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444'];
            const datasets = data.sample_trajectories.map((traj, idx) => ({
                label: `Pfad ${idx+1}`,
                data: traj,
                borderColor: colors[idx % colors.length],
                borderWidth: 2,
                fill: false,
                tension: 0.2
            }));

            mcChartInstance = new Chart(ctx, {
                type: 'line',
                data: { labels, datasets },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { ticks: { color: '#94a3b8' } },
                        y: { ticks: { color: '#94a3b8' } }
                    }
                }
            });
        }
        showToast("Monte-Carlo Simulation erfolgreich berechnet!", "success");
    } catch (e) {
        showToast("Fehler bei Monte-Carlo: " + e.message, "error");
    }
}

// DRIP Simulation Runner
async function runDripSimulation() {
    const years = parseInt(document.getElementById("drip-years")?.value || "10");
    const contrib = parseFloat(document.getElementById("drip-contrib")?.value || "1200");
    const resultsArea = document.getElementById("drip-results-area");

    try {
        const res = await fetch(`${API_BASE}/api/portfolio/1/drip-simulation`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ years: years, annual_contribution: contrib, drip_enabled: true })
        });
        if (!res.ok) throw new Error("DRIP Simulation fehlgeschlagen");
        const data = await res.json();

        if (resultsArea) resultsArea.classList.remove("hidden");
        document.getElementById("drip-init-val").innerText = formatCurrency(data.initial_value);
        document.getElementById("drip-yield-val").innerText = `${data.average_dividend_yield_pct}%`;

        // Chart render
        const ctx = document.getElementById("dripChart")?.getContext("2d");
        if (ctx) {
            if (dripChartInstance) dripChartInstance.destroy();
            const labels = data.projections.map(p => `Jahr ${p.year}`);
            const dripData = data.projections.map(p => p.portfolio_value_drip);
            const noDripData = data.projections.map(p => p.portfolio_value_no_drip);

            dripChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels,
                    datasets: [
                        { label: 'Mit DRIP Reinvestition', data: dripData, borderColor: '#10b981', backgroundColor: 'rgba(16,185,129,0.1)', fill: true },
                        { label: 'Ohne DRIP', data: noDripData, borderColor: '#f59e0b', fill: false, borderDash: [5, 5] }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: { ticks: { color: '#94a3b8' } },
                        y: { ticks: { color: '#94a3b8' } }
                    }
                }
            });
        }
        showToast("DRIP-Reinvestition erfolgreich simuliert!", "success");
    } catch (e) {
        showToast("Fehler bei DRIP Simulation: " + e.message, "error");
    }
}

// Modal tab listeners setup
function setupModalTabListeners() {
    const mcTab = document.getElementById("modal-tab-montecarlo");
    const dripTab = document.getElementById("modal-tab-drip");
    const runMcBtn = document.getElementById("run-mc-btn");
    const runDripBtn = document.getElementById("run-drip-btn");

    if (mcTab) {
        mcTab.addEventListener("click", () => {
            document.querySelectorAll("#backtest-modal .modal-tabactive").forEach(t => t.classList.remove("active"));
            document.querySelectorAll("#backtest-modal .modal-tab-content").forEach(c => c.classList.add("hidden"));
            mcTab.classList.add("active");
            document.getElementById("tab-content-montecarlo")?.classList.remove("hidden");
        });
    }

    if (dripTab) {
        dripTab.addEventListener("click", () => {
            document.querySelectorAll("#backtest-modal .modal-tabactive").forEach(t => t.classList.remove("active"));
            document.querySelectorAll("#backtest-modal .modal-tab-content").forEach(c => c.classList.add("hidden"));
            dripTab.classList.add("active");
            document.getElementById("tab-content-drip")?.classList.remove("hidden");
        });
    }

    if (runMcBtn) runMcBtn.addEventListener("click", runMonteCarloSimulation);
    if (runDripBtn) runDripBtn.addEventListener("click", runDripSimulation);
}




