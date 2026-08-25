# 📈 AlphaPulse AI - Automatisierter KI-Finanzanalyse- & Institutional Portfolio-Bot

AlphaPulse AI ist ein hochmoderner Investment-Bot und institutional-grade Portfolio-Planer, der eigenständig weltweite Aktien-, Krypto- und Rohstoffmärkte überwacht, Finanznachrichten analysiert und mittels modernster KI-Technologie (**Google Gemini 2.5**, Multi-Agent-Debatten) sowie quantitativer Finanzmathematik (**Black-Litterman**, **Hierarchical Risk Parity**, **DCF-Fair-Value**, **Makro-Stresstests**) fundierte Anlageentscheidungen inklusive konkreter **Stop-Loss-**, **Take-Profit-** und **Bracket-Order-Niveaus** berechnet.

Das System kombiniert ein performantes **Python FastAPI-Backend** mit einer **SQLite-Datenbank** (`aiosqlite`), fortschrittlichem **Order Management System (OMS)** und einem **reaktiven Dark-Mode Web-Dashboard** mit Glassmorphism-Design, Echtzeit-Liveupdates (Server-Sent Events) und PWA-Unterstützung.

---

## 🌟 Hauptfunktionen & Enterprise Module

### 1. 🤖 Multi-Agent Deliberation & 3-Runden-Debattier-Engine
*   **5-Rollen KI-Komitee**: *Bullen-Analyst (Growth)*, *Bären-Analyst (Value & Risk)*, *Quant-Analyst (Momentum & Stats)*, *Makro-Ökonom (Fed & FX)* und *Chief Risk Officer (CRO)*.
*   **Strukturierte Debatte**: Eröffnungs-Plädoyers, Rebuttals & Makro-Stresstests gefolgt vom verbindlichen **CIO-Konsens-Urteil** mit Katalysatoren und Absicherungsauflagen.

### 2. 📊 Quantitative Finanzmathematik & Institutional Allocation
*   **Black-Litterman Modell**: Kombiniert das CAPM-Marktgleichgewicht mit KI-Renditeerwartungen und Unsicherheitsmatrizen ($\Omega$) zur Vermeidung von Extremallokationen.
*   **Hierarchical Risk Parity (HRP)**: Graphbasiertes maschinelles Clustering der Korrelationsdistanzmatrix ohne fehleranfällige Matrix-Inversion.
*   **DCF Fair Value & 5x5 Sensitivitätsmatrix**: 5-Jahres-FCF-Projektion, WACC nach CAPM, ewiges Wachstum und Margin of Safety.
*   **Makro-Stresstest- & Krisen-Simulator**: Stresstests gegen historische Krisen (*2020 COVID Flash Crash*, *2008 Lehman-Pleite*, *2022 Stagflation & Fed Zinsschock*, *2000 Dotcom-Crash*) und benutzerdefinierte Schocks.
*   **Nicht-linearer Cornish-Fisher VaR & Expected Shortfall (CVaR)**: Berücksichtigt Schiefe (*Skewness*) und Wölbung (*Kurtosis/Fat Tails*).

### 3. ⚡ Advanced Order Management System (OMS)
*   **Bracket Orders**: Automatischer gekoppelter Kaufauftrag mit verknüpftem Take-Profit- und Stop-Loss-Exit.
*   **OCO (One-Cancels-Other)**: Zeitgleiche Platzierung von Gewinnmitnahme und Verluststopp mit automatischer Löschung der Gegenseite bei Ausführung.
*   **Realistische Ausführungssimulation**: Berücksichtigung von Slippage ($0.05\%$) und Broker-Gebühren.

### 4. 🧭 Fear & Greed Index & Sentiment Radar
*   **Live Fear & Greed Index**: Aggregierter Marktstimmungs-Tacho (0-100 Skala: Extreme Fear bis Extreme Greed) mit Sentiment-Klassifikation und 7-Tage-Historie.
*   **Social Sentiment Radar**: Diskussionsvolumen, Bullish/Bearish-Ratio und Trendthemen aus `r/stocks`, FinTwit und Trading-Foren.

### 5. 🛡️ Risikomanagement & Bilanz-Check
*   **Piotroski F-Score (0-9)**: Umfassende Bilanzanalyse zu Profitabilität, Liquidität und operativer Effizienz.
*   **Altman Z-Score**: Quantitative Insolvenzrisiko-Früherkennung (Sicher / Neutral / Gefahr).
*   **Black-Scholes Options-Hedging**: Greeks (Delta, Gamma, Vega, Theta) und Absicherungsstrategien (Protective Put, Covered Call, Zero-Cost Collar).
*   **Deutscher FIFO-Steuerrechner**: Automatische Berücksichtigung des Sparerpauschbetrags (1.000 € nach § 20 EStG) und Kapitalertragsteuer (26,375%).

---

## 🛠️ Installationsanleitung

### 1. Voraussetzungen
Stellen Sie sicher, dass **Python (Version 3.9 oder neuer)** installiert ist:
```bash
python --version
```

### 2. Projekt-Abhängigkeiten installieren
```bash
pip install -r backend/requirements.txt
```

### 3. API-Key Konfiguration
Erstellen Sie eine Datei namens `.env` im Hauptverzeichnis des Projekts:
```env
GEMINI_API_KEY=IHR_GEMINI_API_KEY_HIER
```
*Hinweis: Falls kein API-Key hinterlegt ist, startet der Bot automatisch im **Demo-Modus** mit vollumfänglichen Simulationen aller Modelle.*

---

## 🚀 Starten des Bots

Führen Sie das Backend im Hauptverzeichnis aus:
```bash
python backend/main.py
```

Sobald der Server läuft, öffnen Sie Ihren Browser unter:
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 🔌 API Endpunkte Übersicht

| Methode | Endpunkt | Beschreibung |
|---|---|---|
| `GET` | `/api/committee/{symbol}/debate` | 5-Rollen Multi-Agenten Deliberation & 3-Runden-Debatte |
| `GET` | `/api/valuation/dcf/{symbol}` | DCF Fair Value Berechnung & 5x5 Sensitivitätsmatrix |
| `POST` | `/api/portfolio/{id}/stress-test` | Makro-Krisen-Stresstest (2008, 2020, 2022, Dotcom) |
| `GET` | `/api/portfolio/{id}/black-litterman` | Black-Litterman Asset Allocation (AI-Enhanced CAPM) |
| `GET` | `/api/portfolio/{id}/hrp` | Hierarchical Risk Parity (HRP) Allokation |
| `GET` | `/api/orders` | Abruf offener & historischer Advanced Orders |
| `POST` | `/api/orders` | Erstellung von Limit-, Stop-, OCO- & Bracket-Orders |
| `DELETE` | `/api/orders/{order_id}` | Stornierung einer offenen Order |
| `POST` | `/api/orders/evaluate` | Manuelle/Hintergrund-Auswertung gegen Marktpreise |
| `GET` | `/api/sentiment/fear-and-greed` | Live Fear & Greed Marktstimmungs-Index |
| `GET` | `/api/sentiment/social/{symbol}` | Social Media Sentiment Radar & Diskussionsvolumen |
| `GET` | `/api/status` | Liefert den aktuellen Scheduler- & Update-Status |
| `GET` | `/api/events` | Server-Sent Events (SSE) Stream für Echtzeit-Updates |
| `GET` | `/api/predictions` | Alle aktuellen KI-Analysen & Marktprognosen |
| `GET` | `/api/history/{symbol}` | Historische Kursdaten & Indikatoren |
| `GET` | `/api/accuracy` | KI-Trefferquote & historische Auswertung |
| `POST` | `/api/portfolio/{id}/drip-simulation` | DRIP Dividenden-Reinvestitions-Simulation |
| `POST` | `/api/portfolio/{id}/monte-carlo` | Monte-Carlo Zukunfts-Simulation |
| `GET` | `/api/portfolio/{id}/efficient-frontier` | Markowitz Efficient Frontier Berechnung |
| `POST` | `/api/portfolio/{id}/import-csv` | Broker CSV-Import (Trade Republic, Scalable etc.) |
| `GET` | `/api/reports/pdf` | Strukturierter Datenexport für PDF-Steuerberichte |

---

## 📁 Projektstruktur

```text
finance-ai-bot/
├── backend/
│   ├── data/
│   │   └── finance_bot.db       # SQLite Datenbank
│   ├── quant_engine.py          # DCF, Black-Litterman, HRP, Stress-Testing, VaR/CVaR
│   ├── sentiment_engine.py      # Multi-Agent Debate, Fear & Greed, Social Sentiment
│   ├── order_management.py     # Advanced OMS (Bracket, OCO, Slippage & Fee Simulation)
│   ├── fundamental_analyzer.py  # Piotroski F-Score & Altman Z-Score
│   ├── options_hedging.py       # Black-Scholes Greeks & Hedging-Strategien
│   ├── auto_trader.py           # Regelbasierter Auto-Trader & Trailing-Stops
│   ├── data_fetcher.py          # Yahoo Finance, ATR, SuperTrend, Ichimoku, News
│   ├── ai_analyzer.py           # Gemini LLM Integration & Rebalancing
│   ├── db.py                    # aiosqlite Tabellen, Migrations & DB-Methoden
│   ├── notifications.py         # WebPush (VAPID), Telegram, Discord & E-Mail
│   ├── scheduler.py             # APScheduler Hintergrund-Tasks & Alarme
│   ├── auth.py & auth_endpoints # JWT Auth & Rechteverwaltung
│   ├── main.py                  # FastAPI Hauptserver & Enterprise Endpunkte
│   └── requirements.txt         # Python-Bibliotheken
├── frontend/
│   ├── index.html               # Glassmorphism Dashboard UI, Debatten- & DCF-Panes
│   ├── style.css                # Premium Dark-Theme Styling
│   ├── app.js                   # Reactive Dashboard Logic, Chart.js, SSE & PWA
│   ├── manifest.json            # PWA Web App Manifest
│   └── sw.js                    # Service Worker für Caching & Push Notifications
├── tests/
│   ├── test_backend.py          # Standalone Backend Testskript
│   └── test_endpoints.py        # Automatisierte Testsuite (30 Tests, 100% Pass)
├── .env                         # API-Keys & Konfiguration (lokal)
└── README.md                    # Dokumentation & Changelog
```

---

## 📝 Logbuch der Änderungen (Changelog)

*   **v3.0.0 (Aktuell - Enterprise Upgrade)**:
    *   ✅ **Multi-Agent Deliberation & Debating Engine**: 5-Rollen KI-Komitee (*Growth, Value, Quant, Macro, Risk Officer*) mit 3 strukturierten Runden und verbindlichem CIO-Urteil.
    *   ✅ **DCF Fair Value & 5x5 Sensitivitätsmatrix**: Intrinsische Bewertung nach Free Cash Flow, CAPM-WACC und ewiger Wachstumsrate mit Sicherheitsmarge.
    *   ✅ **Black-Litterman Portfolio-Optimierung**: KI-gestützte CAPM-Gleichgewichts-Allokation ohne unrealistische Extrempositionen.
    *   ✅ **Hierarchical Risk Parity (HRP)**: Maschinelles Korrelations-Clustering für robuste Diversifikation.
    *   ✅ **Makro-Stresstests & Krisen-Simulator**: Historische Crash-Szenarien (2020 COVID, 2008 Lehman, 2022 Fed Shock, 2000 Dotcom) mit P&L-Auswertung.
    *   ✅ **Advanced Order Management System (OMS)**: Unterstützung für Bracket-Orders (Entry + Take-Profit + Stop-Loss), OCO-Orders und Slippage-Simulation.
    *   ✅ **Fear & Greed Index Live-Aggregator**: Stimmungsanzeige direkt im Dashboard-Header.
    *   ✅ **100% Test-Validierung**: Alle 30 automatisierten Endpunkt- und Workflow-Tests grün.

*   **v2.1.0**:
    *   ✅ Frei konfigurierbare Backtest-Hyperparameter (RSI-Schwellen, SMA-Perioden).
    *   ✅ Kombinierte Backtesting-Multistrategien.
    *   ✅ Dynamischer Wirtschaftskalender.
