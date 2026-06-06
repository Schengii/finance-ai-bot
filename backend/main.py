import os
import sys
import json
import logging
# pyrefly: ignore [missing-import]
import yfinance as yf
# pyrefly: ignore [missing-import]
import uvicorn

# Übergeordnetes Verzeichnis zum Python-Pfad hinzufügen
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List
# pyrefly: ignore [missing-import]
from pydantic import BaseModel
# pyrefly: ignore [missing-import]
from fastapi import FastAPI, BackgroundTasks, HTTPException
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
# pyrefly: ignore [missing-import]
from fastapi.staticfiles import StaticFiles
# pyrefly: ignore [missing-import]
from backend.config import DATA_FILE, DATA_DIR
# pyrefly: ignore [missing-import]
from backend import scheduler

logger = logging.getLogger(__name__)

app = FastAPI(title="Finance AI Bot API", version="1.0.0")

# CORS-Konfiguration für das Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Für lokale Entwicklung; in Produktion einschränken
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Wird beim Starten des Servers ausgeführt und initialisiert den Scheduler."""
    # Logging-Konfiguration anpassen, nachdem uvicorn gestartet ist
    log_file = DATA_DIR / "backend.log"
    root_logger = logging.getLogger()
    
    # Entferne bestehende Handler, um Duplikate zu vermeiden
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    # Füge unsere Handler hinzu
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    root_logger.addHandler(file_handler)
    
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    root_logger.addHandler(stream_handler)
    
    logger.info("Logging-System in backend.log umgeleitet.")
    scheduler.start_scheduler()

@app.get("/api/status")
def get_status():
    """Gibt den aktuellen Status des Update-Prozesses zurück."""
    last_updated = "Nie"
    try:
        from backend.db import get_predictions_from_db
        db_data = get_predictions_from_db()
        last_updated = db_data.get("last_updated", "Unbekannt") or "Nie"
    except Exception as e:
        logger.error(f"Fehler beim Lesen des Update-Zeitstempels aus DB: {e}")
        
    return {
        "is_updating": scheduler.is_updating,
        "last_updated": last_updated
    }

@app.get("/api/predictions")
def get_predictions():
    """Gibt alle aktuellen Krypto- und Aktienprognosen aus der Datenbank zurück."""
    try:
        from backend.db import get_predictions_from_db
        db_data = get_predictions_from_db()
        if not db_data or not db_data.get("predictions"):
            return {
                "last_updated": "Nie",
                "predictions": {},
                "message": "Es wurden noch keine Daten generiert. Das erste Update läuft im Hintergrund."
            }
        return db_data
    except Exception as e:
        logger.error(f"Fehler beim Laden der Prognosen aus der DB: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Laden der Analysedaten.")

@app.get("/api/history/{symbol}")
def get_asset_history(symbol: str, period: str = "30d"):
    """Holt historische Kursdaten für ein bestimmtes Intervall."""
    yf_period = "3mo"
    yf_interval = "1d"
    
    if period == "24h":
        yf_period = "1d"
        yf_interval = "15m"
    elif period == "7d":
        yf_period = "7d"
        yf_interval = "1h"
    elif period == "30d":
        yf_period = "1mo"
        yf_interval = "1d"
    elif period == "1y":
        yf_period = "1y"
        yf_interval = "1d"
    elif period == "5y":
        yf_period = "5y"
        yf_interval = "1wk"
    elif period == "10y":
        yf_period = "10y"
        yf_interval = "1mo"
        
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=yf_period, interval=yf_interval)
        if df.empty:
            raise HTTPException(status_code=404, detail="Keine historischen Daten gefunden.")
            
        history = []
        for index, row in df.iterrows():
            if period in ["24h", "7d"]:
                date_str = index.strftime('%Y-%m-%d %H:%M')
            else:
                date_str = index.strftime('%Y-%m-%d')
                
            history.append({
                "date": date_str,
                "price": round(float(row['Close']), 2),
                "volume": int(row['Volume']) if 'Volume' in row else 0
            })
        return {"symbol": symbol, "period": period, "history": history}
    except Exception as e:
        logger.error(f"Fehler beim Laden der Historie für {symbol} ({period}): {e}")
        raise HTTPException(status_code=500, detail=str(e))


class WatchlistItem(BaseModel):
    symbol: str
    name: str
    type: str

class PortfolioItem(BaseModel):
    symbol: str
    quantity: float
    buy_price: float

class PortfolioAnalysisRequest(BaseModel):
    holdings: List[PortfolioItem]
    strategy: str


@app.get("/api/assets")
def get_watchlist():
    """Holt alle überwachten Assets aus der Watchlist."""
    try:
        from backend.db import get_all_assets
        return get_all_assets()
    except Exception as e:
        logger.error(f"Fehler beim Laden der Watchlist: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Laden der Watchlist.")


@app.post("/api/assets")
def add_watchlist_item(item: WatchlistItem, background_tasks: BackgroundTasks):
    """Fügt ein neues Asset zur Watchlist hinzu und stößt dessen Analyse an."""
    try:
        from backend.db import add_asset
        symbol = item.symbol.strip().upper()
        name = item.name.strip()
        asset_type = item.type.strip().lower()
        
        if not symbol or not name or asset_type not in ["stock", "crypto", "commodity"]:
            raise HTTPException(status_code=400, detail="Ungültige Asset-Daten.")
            
        success = add_asset(symbol, name, asset_type)
        if not success:
            raise HTTPException(status_code=500, detail="Fehler beim Speichern in der Watchlist.")
            
        # Asynchrone sofortige Hintergrund-Analyse starten
        from backend.scheduler import analyze_single_asset_background
        background_tasks.add_task(analyze_single_asset_background, {
            "symbol": symbol,
            "name": name,
            "type": asset_type
        })
        
        return {"status": "success", "message": f"Asset {symbol} hinzugefügt. Analyse läuft im Hintergrund."}
    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen des Assets {item.symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/assets/{symbol}")
def delete_watchlist_item(symbol: str):
    """Löscht ein Asset aus der Watchlist."""
    try:
        from backend.db import delete_asset, get_predictions_from_db
        symbol_upper = symbol.strip().upper()
        success = delete_asset(symbol_upper)
        if not success:
            raise HTTPException(status_code=500, detail=f"Fehler beim Löschen von {symbol_upper} aus Watchlist.")
            
        # Aktualisiere predictions.json (Kompatibilitäts-Fallback)
        try:
            from backend.config import DATA_FILE
            from datetime import datetime
            db_data = get_predictions_from_db()
            db_data["last_updated"] = datetime.now().strftime('%Y-%m-%d %H:%M')
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(db_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren der Fallback-JSON nach Löschung: {e}")
            
        return {"status": "success", "message": f"Asset {symbol_upper} gelöscht."}
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Assets {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/portfolio")
def get_portfolio():
    """Holt das Portfolio des Nutzers aus der Datenbank."""
    try:
        from backend.db import get_portfolio_from_db
        return get_portfolio_from_db()
    except Exception as e:
        logger.error(f"Fehler beim Laden des Portfolios: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Laden des Portfolios.")


@app.post("/api/portfolio")
def add_portfolio_item_route(item: PortfolioItem):
    """Speichert oder aktualisiert ein Asset im Portfolio."""
    try:
        from backend.db import save_portfolio_item
        success = save_portfolio_item(item.symbol, item.quantity, item.buy_price)
        if not success:
            raise HTTPException(status_code=500, detail="Fehler beim Speichern in der Datenbank.")
        return {"status": "success", "message": f"Asset {item.symbol} im Portfolio gespeichert."}
    except Exception as e:
        logger.error(f"Fehler beim Speichern des Portfolio-Items {item.symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/portfolio/{symbol}")
def delete_portfolio_item_route(symbol: str):
    """Löscht ein Asset aus dem Portfolio."""
    try:
        from backend.db import delete_portfolio_item
        success = delete_portfolio_item(symbol)
        if not success:
            raise HTTPException(status_code=500, detail="Fehler beim Löschen in der Datenbank.")
        return {"status": "success", "message": f"Asset {symbol} aus dem Portfolio gelöscht."}
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Portfolio-Items {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/portfolio/analyze")
def analyze_portfolio(request: PortfolioAnalysisRequest):
    """Analysiert das Nutzerportfolio und gibt Empfehlungen basierend auf einer Strategie."""
    # pyrefly: ignore [missing-import]
    from backend.ai_analyzer import client, HAS_NEW_GENAI, HAS_LEGACY_GENAI, GEMINI_API_KEY, get_mock_prediction
    # pyrefly: ignore [missing-import]
    from backend.data_fetcher import fetch_market_data
    
    if not request.holdings:
        return {
            "portfolio_score": 100,
            "advice_summary": "Fügen Sie Ihrem Portfolio Investments hinzu, um eine KI-Analyse zu erhalten.",
            "suggestions": [],
            "forecasts": {},
            "estimated_dividends": "Keine Investments vorhanden.",
            "tips": ["Erstellen Sie Ihre ersten Investments in der Tabelle links."]
        }
        
    # Marktdaten für die enthaltenen Assets sammeln
    holdings_summary = []
    total_value = 0.0
    total_cost = 0.0
    
    for item in request.holdings:
        symbol = item.symbol
        # Versuche aktuelle Preise zu holen
        market_data = fetch_market_data(symbol, days=30)
        current_price = market_data["current_price"] if market_data else item.buy_price
        
        value = current_price * item.quantity
        cost = item.buy_price * item.quantity
        total_value += value
        total_cost += cost
        
        holdings_summary.append({
            "symbol": symbol,
            "quantity": item.quantity,
            "buy_price": item.buy_price,
            "current_price": current_price,
            "rsi": market_data["rsi"] if market_data else 50,
            "trend": market_data["technical_trend"] if market_data else "Neutral"
        })
        
    # Prompt zusammenbauen
    holdings_text = ""
    for h in holdings_summary:
        holdings_text += f"- Ticker: {h['symbol']}, Menge: {h['quantity']}, Kaufpreis: {h['buy_price']} $, Aktueller Preis: {h['current_price']} $ (RSI: {h['rsi']}, Trend: {h['trend']})\n"
        
    prompt = f"""
Du bist ein erstklassiger KI-Finanzberater und Portfolio-Manager.
Ein Nutzer hat sein Portfolio mit folgenden Werten geladen:
{holdings_text}

Gesamtinvestition (Kosten): {total_cost:.2f} $
Aktueller Gesamtwert: {total_value:.2f} $
Gewählte Anlagestrategie des Nutzers: {request.strategy}

Analysiere dieses Portfolio im Hinblick auf die gewählte Anlagestrategie (z.B. Konservativ, Ausgewogen, Aggressiv, Dividenden-Fokus).
Deine Antwort MUSS ein gültiges JSON-Objekt sein. Antworte AUSSCHLIESSLICH mit diesem JSON-Objekt. Verwende genau folgendes Schema:

{{
  "portfolio_score": <Zahl zwischen 0 und 100, Bewertung der Portfolio-Qualität passend zur Strategie>,
  "advice_summary": "<Zusammenfassende Einschätzung und Begründung des Scores auf Deutsch (ca. 3-4 Sätze).>",
  "suggestions": ["Verbesserungsvorschlag 1", "Verbesserungsvorschlag 2", ...],
  "forecasts": {{
     "SYMBOL1": {{ "buy_percentage": <Zahl zwischen 0 und 100 für Kaufkonfidenz>, "action": "Kauf" | "Halten" | "Verkauf" }},
     "SYMBOL2": ...
  }},
  "estimated_dividends": "<Spezifische Schätzung der zu erwartenden Dividenden bzw. Erträge dieses Portfolios auf Deutsch.>",
  "tips": ["Hilfreicher allgemeiner Anlagetipp 1", "Hilfreicher allgemeiner Anlagetipp 2", ...]
}}
"""

    # Mock Fallback, falls kein Key vorhanden
    if not GEMINI_API_KEY or (not HAS_NEW_GENAI and not HAS_LEGACY_GENAI):
        score = 80 if request.strategy == "Ausgewogen" else 75
        forecasts = {}
        for h in holdings_summary:
            rsi = h["rsi"]
            if rsi < 40:
                action, pct = "Kauf", 85
            elif rsi > 70:
                action, pct = "Verkauf", 75
            else:
                action, pct = "Halten", 55
            forecasts[h["symbol"]] = {"buy_percentage": pct, "action": action}
            
        return {
            "portfolio_score": score,
            "advice_summary": f"Ihr Portfolio zeigt eine solide Grundlage für die Strategie '{request.strategy}'. Die Diversifikation über {len(request.holdings)} Asset(s) ist ein guter Anfang. Technische Indikatoren weisen auf kurzfristige Halte-Signale hin.",
            "suggestions": [
                "Erhöhen Sie den Anteil an Rohstoffen zur Inflationsabsicherung.",
                "Setzen Sie regelmäßige Sparpläne auf Krypto-Assets auf, um den Cost-Average-Effekt zu nutzen."
            ],
            "forecasts": forecasts,
            "estimated_dividends": f"Die geschätzte Dividendenrendite liegt bei ca. 1.5% - 2.2% p.a. (primär getrieben durch eventuelle Aktienanteile).",
            "tips": [
                "Diversifizieren Sie über verschiedene Assetklassen hinweg.",
                "Reinvestieren Sie erhaltene Ausschüttungen direkt wieder."
            ]
        }

    try:
        if HAS_NEW_GENAI and client:
            # pyrefly: ignore [missing-import]
            from google.genai import types
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                )
            )
            response_text = response.text
        elif HAS_LEGACY_GENAI:
            # pyrefly: ignore [missing-import]
            import google.generativeai as legacy_genai
            model = legacy_genai.GenerativeModel("gemini-1.5-flash")
            generation_config = {
                "response_mime_type": "application/json",
                "temperature": 0.2
            }
            response = model.generate_content(prompt, generation_config=generation_config)
            response_text = response.text
        else:
            raise RuntimeError("Kein Gemini SDK verfügbar.")
            
        return json.loads(response_text.strip())
    except Exception as e:
        logger.error(f"Fehler bei der KI-Portfolio-Analyse: {e}")
        raise HTTPException(status_code=500, detail=f"KI-Analyse fehlgeschlagen: {str(e)}")


@app.post("/api/refresh")
def trigger_refresh(background_tasks: BackgroundTasks):
    """Löst eine manuelle Aktualisierung der Marktdaten und KI-Analysen aus."""
    if scheduler.is_updating:
        return {"status": "updating", "message": "Aktualisierung läuft bereits."}
        
    # Führe Aktualisierung im Hintergrund aus
    background_tasks.add_task(scheduler.run_update_cycle)
    return {"status": "started", "message": "Aktualisierungszyklus gestartet."}

# Finde den Pfad zum Frontend-Ordner
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

# Statische Dateien für das Frontend ausliefern (MUSS als letztes gemountet werden)
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=False)
