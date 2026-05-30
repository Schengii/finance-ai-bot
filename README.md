# 📈 AlphaPulse AI - Automatisierter KI-Finanzanalyse-Bot

AlphaPulse AI ist ein intelligenter Investment-Bot, der eigenständig und regelmäßig aktuelle Aktien- und Kryptomärkte beobachtet, die neuesten Nachrichten zu den Unternehmen und Assets analysiert und mittels der Gemini API (LLM) fundierte Kauf-, Halte- oder Verkaufsprognosen erstellt.

Das Projekt besteht aus einem robusten **Python FastAPI-Backend** (welches Kurse, technische Indikatoren und Nachrichten sammelt und per KI bewertet) und einem **modernen, reaktiven Web-Dashboard** (HTML/CSS/JS), das direkt vom Backend mitserviert wird.

---

## 🌟 Features

*   **Echtzeit- & Marktdaten**: Automatischer Abruf von Aktien- und Kryptowährungsverläufen über Yahoo Finance.
*   **Technische Indikatoren**: Berechnung wichtiger Marktindikatoren wie RSI (Relative Strength Index), SMA 20/50 (Gleitende Durchschnitte) und MACD.
*   **KI-Sentimentanalyse**: Auswertung der neuesten Finanznachrichten bezüglich Sentiment (Stimmungsbild) und Auswirkung auf den Kurs.
*   **Strukturierte Prognosen**: Generierung von konkreten Empfehlungen (Starker Kauf, Kauf, Halten, Verkauf, Starker Verkauf) inklusive eines Konfidenz-Scores und detaillierten Begründungstexten auf Deutsch.
*   **Automatischer Hintergrund-Scheduler**: Die Analysen aktualisieren sich im Hintergrund (standardmäßig alle 24 Stunden). Ein manueller "Jetzt Analysieren"-Button ermöglicht sofortige Updates.
*   **Premium Web-Dashboard**: Wunderschönes Dark-Mode-Design mit Glassmorphismus-Effekten, interaktiven Kurs-Charts (Chart.js) und detaillierten KI-Berichten.

---

## 🛠️ Installationsanleitung

### 1. Voraussetzungen
Stellen Sie sicher, dass **Python (Version 3.9 oder neuer)** auf Ihrem System installiert ist. Sie können dies in Ihrem Terminal/Eingabeaufforderung überprüfen:
```bash
python --version
```

### 2. Projekt-Abhängigkeiten installieren
Klonen Sie das Projekt oder navigieren Sie in den Projektordner und installieren Sie die benötigten Bibliotheken:
```bash
pip install -r backend/requirements.txt
```

### 3. API-Key Konfiguration
Der Bot benötigt einen **Gemini API-Key** für die KI-Analysen.
1. Erstellen Sie eine Datei namens `.env` im Hauptverzeichnis des Projekts (`finance-ai-bot/.env`).
2. Fügen Sie Ihren Gemini API-Key wie folgt hinzu:
   ```env
   GEMINI_API_KEY=IHR_GEMINI_API_KEY_HIER
   ```
   *Hinweis: Falls kein API-Key hinterlegt ist, startet der Bot automatisch im **Demo-Modus** mit simulierten Prognosen (Mock-Daten), damit Sie das Dashboard sofort testen können.*

---

## 🚀 Starten des Bots

Führen Sie das Backend im Hauptverzeichnis aus:
```bash
python backend/main.py
```
*Alternativ:*
```bash
python -m backend.main
```

Sobald der Server läuft, öffnen Sie einfach Ihren Webbrowser und rufen Sie die folgende Adresse auf:
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

Das Dashboard wird geladen, und der Bot beginnt im Hintergrund mit der ersten echten Marktanalyse für Ihre Assets!

---

## 📁 Projektstruktur

```text
finance-ai-bot/
├── backend/
│   ├── data/
│   │   └── predictions.json     # Gespeicherte Analyseergebnisse
│   ├── config.py                # Konfiguration (Assets, Intervalle)
│   ├── data_fetcher.py          # Yahoo Finance & RSS News-Scraper
│   ├── ai_analyzer.py           # Gemini LLM Integration & Prompting
│   ├── scheduler.py             # APScheduler Hintergrund-Tasks
│   ├── main.py                  # FastAPI Server & API-Endpunkte
│   ├── requirements.txt         # Python-Abhängigkeiten
│   └── test_backend.py          # Lokales Testskript
├── frontend/
│   ├── index.html               # Dashboard-Struktur
│   ├── style.css                # Premium Dark-Theme Styling
│   └── app.js                   # Frontend Logik, Charts & Polling
├── .env                         # Umgebungsvariablen (nicht committen)
└── README.md                    # Dokumentation (diese Datei)
```

---

## ⚙️ Anpassungsmöglichkeiten

In der Datei [backend/config.py](file:///c:/Users/sche-/Desktop/Developer%20Akademie/finance-ai-bot/backend/config.py) können Sie die Einstellungen des Bots leicht anpassen:
*   **Assets erweitern**: Fügen Sie neue Ticker-Symbole (z.B. `TSLA` für Tesla, `BTC-USD` für Bitcoin) einfach zur Liste `DEFAULT_ASSETS` hinzu.
*   **Aktualisierungsintervall**: Ändern Sie `UPDATE_INTERVAL_HOURS` (z.B. auf `1` für stündliche Checks).
*   **Historischer Zeitraum**: Passen Sie `HISTORICAL_DAYS` an, um längere oder kürzere Zeiträume in den Charts anzuzeigen (standardmäßig 90 Tage).
