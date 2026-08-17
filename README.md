# 📈 AlphaPulse AI - Automatisierter KI-Finanzanalyse- & Portfolio-Bot

AlphaPulse AI ist ein hochmoderner Investment-Bot und Portfolio-Planer, der eigenständig und regelmäßig weltweite Aktien-, Krypto- und Rohstoffmärkte beobachtet, Finanznachrichten analysiert und mittels der offiziellen Google Gemini API (`google-genai`) fundierte Kauf-, Halte- oder Verkaufsprognosen inklusive konkreter **Stop-Loss-**, **Take-Profit-** und **Zielkurs-Niveaus** berechnet.

Das System kombiniert ein hochperformantes **Python FastAPI-Backend** mit einer **SQLite-Datenbank** (`aiosqlite`) und einem **reaktiven Dark-Mode Web-Dashboard** mit Glassmorphism-Design, Echtzeit-Liveupdates (Server-Sent Events) und PWA-Unterstützung.

---

## 🌟 Hauptfunktionen (Features)

*   **🤖 KI-gestützte Marktanalysen**: Einsatz des aktuellen Google Gemini SDK (`google-genai`) für tiefgehende Sentiment- und Fundamentalanalyse in anpassbarer Tonalität (Professionell, Humorvoll, Defensiv, Aggressiv).
*   **🎯 KI Stop-Loss & Take-Profit Preisziele**: Automatische Berechnung von konkreten Stop-Loss-, Take-Profit- und Zielkursen für jede analysierte Position.
*   **📊 Technische & Fundamental-Indikatoren**: RSI (14), MACD, SMA 20/50, EMA 200, Bollinger Bands, Stochastik %K, KGV (P/E), Marktkapitalisierung, 52-Wochen-Range, Beta & EPS.
*   **🎲 Monte-Carlo-Portfolio-Simulation**: Berechnet 500 bis 1.000 stochastische Zukunfts-Trajektorien für das Nutzerportfolio inklusive Konfidenz-Perzentilen (P5, P50, P95).
*   **📐 Markowitz Efficient Frontier**: Berechnet die optimale Risiko-Rendite-Allokation zur Maximierung der Sharpe-Ratio.
*   **💸 Dividenden-Ertrags-Tracker & DRIP-Simulator**: Simuliert das Zinseszins-Wachstum durch reinvestierte Dividenden (Dividend Reinvestment Plan) über bis zu 30 Jahre.
*   **🔄 Flexible Broker CSV-Imports**: Unterstützt Importe und automatische Spaltenerkennung für Trade Republic, Scalable Capital, Coinbase, Parqet und individuelle Broker-Dateien.
*   **⚡ Echtzeit-Liveupdates (SSE)**: Server-Sent Events (`/api/events`) für sofortige Benachrichtigungen und UI-Refreshes im Browser ohne Polling.
*   **📱 Progressive Web App (PWA)**: Mit `manifest.json` und Service Worker (`sw.js`) installierbar auf iOS & Android sowie WebPush-Benachrichtigungen mit automatischer VAPID-Schlüssel-Generierung.
*   **🔔 Multi-Kanal Alarmierung**: Benachrichtigungen über Telegram Bots, Discord Webhooks, E-Mail (SMTP) und Browser Push bei Preis-, RSI- oder Empfehlungsänderungen.
*   **💼 Multi-Portfolios & FIFO-Steuerrechner**: Verwalte mehrere Unterportfolios mit Cash-Beständen, Zielallokationen, Transaktionshistorie und automatischer Kapitalertragsteuer-Berechnung nach dem FIFO-Prinzip.

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
*Hinweis: Falls kein API-Key hinterlegt ist, startet der Bot automatisch im **Demo-Modus** mit simulierten Prognosen (Mock-Daten).*

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
| `GET` | `/api/status` | Liefert den aktuellen Scheduler- & Update-Status |
| `GET` | `/api/events` | Server-Sent Events (SSE) Stream für Echtzeit-Updates |
| `GET` | `/api/predictions` | Alle aktuellen KI-Analysen & Marktprognosen |
| `GET` | `/api/history/{symbol}` | Historische Kursdaten & Indikatoren |
| `GET` | `/api/search/{symbol}` | Ticker-Suche & Ticker-Lookup |
| `GET` | `/api/accuracy` | KI-Trefferquote & historische Auswertung |
| `POST` | `/api/portfolio/{id}/drip-simulation` | DRIP Dividenden-Reinvestitions-Simulation |
| `POST` | `/api/portfolio/{id}/monte-carlo` | Monte-Carlo Zukunfts-Simulation |
| `GET` | `/api/portfolio/{id}/efficient-frontier` | Markowitz Efficient Frontier Berechnung |
| `POST` | `/api/portfolio/{id}/import-csv` | Broker CSV-Import (Trade Republic, Scalable etc.) |
| `GET` | `/api/notifications/vapid-key` | Abruf des öffentlichen WebPush VAPID-Schlüssels |

---

## 📁 Projektstruktur

```text
finance-ai-bot/
├── backend/
│   ├── data/
│   │   └── finance_bot.db       # SQLite Datenbank (Assets, Portfolios, Predictions, Settings)
│   ├── config.py                # System-Konfiguration (Settings)
│   ├── data_fetcher.py          # Yahoo Finance, Indikatoren (RSI, MACD, EMA) & News Parser
│   ├── ai_analyzer.py           # Gemini LLM Integration (google-genai), Prompts & Stopps
│   ├── db.py                    # aiosqlite Tabellen, Migrations & Datenbank-Methoden
│   ├── notifications.py         # WebPush (VAPID), Telegram, Discord & E-Mail
│   ├── scheduler.py             # APScheduler Hintergrund-Tasks & Alarme
│   ├── auth.py & auth_endpoints # JWT Auth & Rechteverwaltung
│   ├── main.py                  # FastAPI Hauptserver & API-Endpunkte
│   └── requirements.txt         # Python-Bibliotheken
├── frontend/
│   ├── index.html               # Glassmorphism Dashboard UI & Modals
│   ├── style.css                # Premium Dark-Theme Styling
│   ├── app.js                   # Reactive Dashboard Logic, Chart.js, SSE & PWA
│   ├── manifest.json            # PWA Web App Manifest
│   └── sw.js                    # Service Worker für Caching & Push Notifications
├── tests/
│   ├── test_backend.py          # Standalone Backend Testskript
│   └── test_endpoints.py        # Automatisierte FastAPI Endpunkt-Tests
├── .env                         # API-Keys & Konfiguration (lokal)
└── README.md                    # Projekt-Dokumentation & Changelog
```

---

## 📝 Logbuch der Änderungen (Changelog)

*   **v1.9.0 (Aktuell)**:
    *   ✅ **Multi-Condition Alert-Engine**: Zusammengesetzte Alarmregeln wie `RSI < 35 AND KI-Kauf` (Überverkauft mit Trendwende) oder `RSI > 70 AND KI-Verkauf` im Alarm-Manager und Cron-Scheduler.
    *   ✅ **4-Experten KI-Investment-Komitee & Social Sentiment**: Integration eines Social-Media & Reddit-Stimmungsanalysten (`r/stocks`, `r/wallstreetbets`, FinTwit) direkt im Komitee-Panel.
    *   ✅ **Bilanz- & Insolvenz-Check Tab**: Eigene Benutzeroberfläche zur Live-Visualisierung des Piotroski F-Scores und Altman Z-Scores im Asset-Detailbereich.
    *   ✅ **Deutsche Steuerberechnung nach § 20 EStG**: Automatisierte Anrechnung des 1.000 € Sparerpauschbetrags und Ausweisung der Ersparnis.
    *   ✅ **100% Test-Validierung**: Alle 22 automatisierten Endpunkt- und Workflow-Tests grün.

*   **v1.8.0**:
    *   ✅ **Deutscher FIFO-Steuerrechner & Sparerpauschbetrag**: Automatische Berücksichtigung des gesetzlichen Sparerpauschbetrags (1.000 € nach § 20 Abs. 9 EStG) sowie Berechnung von Freibetrag-Ersparnissen in Simulationen und Portfolio-Reports.
    *   ✅ **LLM JSON-Stabilität**: Bereinigung und Härtung des Gemini KI-Rebalancing-Prompts zur Vermeidung von Parsing-Exceptions.
    *   ✅ **TradingView Lightweight Candlesticks**: Nahtlose Umschaltung zwischen Linien- & Kerzencharts inklusive OHLC-Berechnung und SMA/EMA/Bollinger-Overlays.

*   **v1.7.0**:
    *   ✅ **Interaktive Candlestick-Charts**: Integration von TradingView Lightweight Charts mit dynamischem Umschalter zwischen Linien- und Kerzen-Chart (OHLC-Kurse).
    *   ✅ **Indikator-Interaktion**: Vollständige Umschaltung und Anzeige von SMA 20, SMA 50, EMA 200 und Bollinger Bändern.
    *   ✅ **Router-Modularisierung**: Backend-Endpunkte für Analyse und Portfolio unter `backend/routes/` aufgeteilt.

*   **v1.6.0**:
    *   ✅ Vollständige Behebung von Notification-DB-Imports (`get_notifications`, `add_notification`) mit 100% grünen Testläufen.
    *   ✅ Modernisierung des FastAPI Lifespan Handlers (Ersatz der veralteten `@app.on_event("startup")` API).
    *   ✅ Robustes JSON-Parsing in der Gemini KI-Rebalancing-Engine mit automatischer Markdown-Bereinigung.
    *   ✅ Interaktiver KI-Copilot ("AlphaChat") mit Portfolio-Direktabfragen und Quick-Actions.
    *   ✅ Performance-Benchmark-Berechnung (Alpha & Beta vs. S&P 500 & MSCI World).
    *   ✅ Multi-Kanal Alarmsystem (Browser Push, Webhooks, Telegram, Discord, E-Mail).
