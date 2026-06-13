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
    if (elements.navMarkets && elements.navPortfolio) {
        elements.navMarkets.addEventListener("click", () => switchView("markets-view"));
        elements.navPortfolio.addEventListener("click", () => switchView("portfolio-view"));
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
    if (viewId === "markets-view") {
        elements.navMarkets.classList.add("active");
        elements.navPortfolio.classList.remove("active");
        elements.marketsView.classList.add("active");
        elements.marketsView.classList.remove("hidden");
        elements.portfolioView.classList.add("hidden");
        elements.portfolioView.classList.remove("active");
    } else {
        elements.navPortfolio.classList.add("active");
        elements.navMarkets.classList.remove("active");
        elements.portfolioView.classList.add("active");
        elements.portfolioView.classList.remove("hidden");
        elements.marketsView.classList.add("hidden");
        elements.marketsView.classList.remove("active");
        // Ensure portfolio stats and holdings render
        renderPortfolio();
    }
}

async function initPortfolio() {
    if (portfolioInitialized) return;
    
    try {
        const response = await fetch(`${API_BASE}/api/portfolio`);
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
                await fetch(`${API_BASE}/api/portfolio`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(item)
                });
            }
            // Nochmals abrufen nach dem Seeding
            const response2 = await fetch(`${API_BASE}/api/portfolio`);
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
    
    // Render allocation chart
    renderAllocationChart();
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
        const response = await fetch(`${API_BASE}/api/portfolio`, {
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
        const reloadResponse = await fetch(`${API_BASE}/api/portfolio`);
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
        const response = await fetch(`${API_BASE}/api/portfolio/${item.symbol}`, {
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

