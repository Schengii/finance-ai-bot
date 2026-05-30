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


// Dynamische API-Basis-URL: Falls lokal oder auf abweichendem Port (z.B. Live Server 5500) ausgeführt,
// verweise auf den FastAPI-Server auf Port 8000. Sonst relative Pfade nutzen.
const API_BASE = (window.location.protocol === 'file:' || window.location.port !== '8000') 
    ? 'http://127.0.0.1:8000' 
    : '';


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
    newsList: document.getElementById('detail-news-list')
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
        elements.refreshBtn.querySelector("i").classList.add("icon-spin-hover");
        elements.refreshBtn.querySelector("span").innerText = "Berechne...";
    } else {
        elements.statusDot.className = "status-dot";
        elements.statusText.innerText = "Bereit";
        elements.refreshBtn.disabled = false;
        elements.refreshBtn.querySelector("i").classList.remove("icon-spin-hover");
        elements.refreshBtn.querySelector("span").innerText = "Analysieren";
    }
}

async function triggerRefresh() {
    try {
        console.log("DEBUG: triggerRefresh wurde aufgerufen!");
        alert("DEBUG: Klick registriert! Sende Anfrage an den Server...");
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
        alert("Fehler beim Starten des Updates: " + error.message);
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
    
    window.priceChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
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
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: '#1e293b',
                    titleColor: '#f3f4f6',
                    bodyColor: '#f3f4f6',
                    borderColor: 'rgba(255,255,255,0.08)',
                    borderWidth: 1,
                    displayColors: false,
                    callbacks: {
                        label: function(context) {
                            return `${context.parsed.y.toLocaleString("de-DE", {minimumFractionDigits: 2, maximumFractionDigits: 2})} $`;
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
