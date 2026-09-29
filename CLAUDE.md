# CLAUDE.md - AlphaPulse AI Project Guide

Dieses Dokument dient als zentrale Anleitung und Wissensbasis für Claude / KI-Assistenten bei der Weiterentwicklung und Wartung des **AlphaPulse AI** Projekts.

---

## 📌 Projektüberblick

**AlphaPulse AI** ist ein hochmoderner Investment-Bot und institutional-grade Portfolio-Planer.
- **Backend:** Python 3.9+ mit **FastAPI**, `aiosqlite` (asynchrone SQLite-Datenbank), `APScheduler`, `yfinance`, `pydantic-settings`, Google Generative AI (Gemini 2.5).
- **Frontend:** Reaktives Dark-Mode Dashboard mit **Vanilla JavaScript** (`frontend/app.js`), **Vanilla CSS** mit Glassmorphism-Design (`frontend/style.css`), **HTML5** (`frontend/index.html`) und PWA-Funktionalität (`frontend/manifest.json`, `frontend/sw.js`).
- **Architektur:** Asynchrone REST-API & Server-Sent Events (SSE) für Echtzeit-Kurse, Sentiment-Radar und Trading-Signale.

---

## 📁 Projektstruktur

```text
finance-ai-bot/
├── .claudeignore             # Exkludiert Caches, venv, DBs und Secrets für Claude
├── .env                      # Lokale Konfiguration (NIEMALS committen!)
├── .env.example              # Vorlage für Umgebungsvariablen
├── .gitignore                # Git-Ausschlussregeln
├── CLAUDE.md                 # Diese Datei (Projektrichtlinien für Claude)
├── README.md                 # Projektdokumentation und Feature-Übersicht
├── backend/
│   ├── main.py               # FastAPI App-Initialisierung, Middleware, Routen & SSE
│   ├── config.py             # Pydantic Settings & ENV-Management
│   ├── db.py                 # SQLite DB Initialisierung, Migrationen & CRUD-Logik
│   ├── ai_analyzer.py        # Multi-Agent Deliberation (5 Rollen) & Gemini Integration
│   ├── quant_engine.py       # Black-Litterman, HRP, DCF Fair Value, Stresstests, VaR
│   ├── data_fetcher.py       # YFinance & Marktdatenbeschaffung
│   ├── order_management.py   # OMS: Bracket-Orders, OCO, Slippage-Simulation
│   ├── sentiment_engine.py   # Fear & Greed Index, Reddit/FinTwit Sentiment Radar
│   ├── fundamental_analyzer.py # Piotroski F-Score, Altman Z-Score
│   ├── options_hedging.py    # Black-Scholes Greeks & Hedging-Strategien
│   ├── scheduler.py          # APScheduler Hintergrund-Jobs
│   ├── auth.py & auth_endpoints.py # JWT Authentifizierung & Password Hashing
│   ├── notifications.py      # WebPush & SSE Notifications
│   └── requirements.txt      # Python Abhängigkeiten
├── frontend/
│   ├── index.html            # Dashboard Struktur & Komponenten
│   ├── style.css             # Glassmorphism Dark-Mode UI Tokens & Styles
│   ├── app.js                # State-Management, Chart-Rendering, API-Client & SSE
│   ├── manifest.json         # PWA Manifest
│   └── sw.js                 # Service Worker (Offline-Caching & Push-Handling)
└── tests/                    # Unit- und Integrationstests (pytest)
```

---

## 🛠️ Befehle & Entwicklungs-Workflow

### Lokale Umgebung & Installation
```powershell
# Virtuelle Umgebung erstellen (falls nicht vorhanden)
python -m venv .venv

# Virtuelle Umgebung aktivieren (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Abhängigkeiten installieren
pip install -r backend/requirements.txt
```

### Server starten
```powershell
# Server starten (aus Projekt-Root)
python backend/main.py

# Alternativ via uvicorn direkt:
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
Dashboard-URL: `http://127.0.0.1:8000`

### Tests ausführen
```powershell
# Alle Tests ausführen
pytest

# Mit detaillierter Ausgabe
pytest -v -s
```

---

## 🧭 Leitlinien für Code-Änderungen

### Backend (Python / FastAPI)
1. **Asynchronität:** Alle I/O- und Datenbank-Operationen müssen `async`/`await` nutzen (`aiosqlite`, `httpx`/`aiohttp`). Niemals synchrone Blocking-Aufrufe im Event-Loop durchführen.
2. **Datenbankintegrität:** Änderungen am Schema in `backend/db.py` stets defensiv mit `CREATE TABLE IF NOT EXISTS` oder kontrollierten Migrations-Schritten gestalten.
3. **Fehlerbehandlung:** Externe APIs (wie `yfinance` oder `Gemini`) können ratelimitiert sein oder temporär fehlschlagen. Stets mit `try...except`, Timeouts und Fallback-Werten bzw. Demo-Modus absichern.
4. **Typisierung:** Type-Hints (`typing`) und Pydantic-Modelle für API-Payloads konsequent verwenden.

### Frontend (Vanilla JS / CSS)
1. **Kein Framework-Zwang:** Das Frontend verwendet bewusst natives JavaScript und Vanilla CSS. Bitte keine unnötigen Frameworks (React, Vue, Tailwind) ohne expliziten Benutzerwunsch einführen.
2. **Design-Konsistenz:** Die bestehenden CSS-Variablen (`--bg-primary`, `--glass-bg`, `--accent-blue`, `--border-color` usw.) in `style.css` strikt wiederverwenden.
3. **Echtzeit-Updates:** Live-Daten werden über `EventSource` (`/api/events`) in `app.js` empfangen und in den UI-State eingepflegt.

---

## 🔒 Sicherheitsregeln
- **Niemals API-Keys hardcoden:** `GEMINI_API_KEY`, `JWT_SECRET_KEY` etc. müssen immer aus `backend/config.py` über Umgebungsvariablen (`.env`) geladen werden.
- **Keine Secrets in Git:** `.env` und `.db` Dateien dürfen niemals im Repository getrackt werden.
