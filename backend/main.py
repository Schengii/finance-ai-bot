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
from backend.config import DATA_DIR
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
    """Holt historische Kursdaten für ein bestimmtes Intervall und berechnet SMA 20/50."""
    yf_period = "3mo"
    yf_interval = "1d"
    
    if period == "24h":
        yf_period = "5d"
        yf_interval = "15m"
    elif period == "7d":
        yf_period = "15d"
        yf_interval = "1h"
    elif period == "30d":
        yf_period = "3mo"
        yf_interval = "1d"
    elif period == "1y":
        yf_period = "2y"
        yf_interval = "1d"
    elif period == "5y":
        yf_period = "7y"
        yf_interval = "1wk"
    elif period == "10y":
        yf_period = "12y"
        yf_interval = "1mo"
        
    try:
        import pandas as pd
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=yf_period, interval=yf_interval)
        if df.empty:
            raise HTTPException(status_code=404, detail="Keine historischen Daten gefunden.")
            
        # Berechne SMA 20 und SMA 50
        df['sma_20'] = df['Close'].rolling(window=20).mean()
        df['sma_50'] = df['Close'].rolling(window=50).mean()
        
        # Filter auf den tatsächlich angeforderten Zeitraum
        from datetime import datetime, timedelta
        now = datetime.now(df.index.tz) if df.index.tz else datetime.now()
        
        if period == "24h":
            cutoff = now - timedelta(hours=24)
        elif period == "7d":
            cutoff = now - timedelta(days=7)
        elif period == "30d":
            cutoff = now - timedelta(days=30)
        elif period == "1y":
            cutoff = now - timedelta(days=365)
        elif period == "5y":
            cutoff = now - timedelta(days=5*365)
        elif period == "10y":
            cutoff = now - timedelta(days=10*365)
        else:
            cutoff = None
            
        if cutoff:
            df_filtered = df[df.index >= cutoff]
            if df_filtered.empty:
                df_filtered = df.tail(30 if period == "30d" else (100 if period == "1y" else 24))
        else:
            df_filtered = df
            
        history = []
        for index, row in df_filtered.iterrows():
            if period in ["24h", "7d"]:
                date_str = index.strftime('%Y-%m-%d %H:%M')
            else:
                date_str = index.strftime('%Y-%m-%d')
                
            sma_20_val = round(float(row['sma_20']), 2) if 'sma_20' in row and not pd.isna(row['sma_20']) else None
            sma_50_val = round(float(row['sma_50']), 2) if 'sma_50' in row and not pd.isna(row['sma_50']) else None
            
            history.append({
                "date": date_str,
                "price": round(float(row['Close']), 2),
                "volume": int(row['Volume']) if 'Volume' in row else 0,
                "sma_20": sma_20_val,
                "sma_50": sma_50_val
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

class ChatRequest(BaseModel):
    message: str
    portfolio_id: int = 1

class AlertRequest(BaseModel):
    symbol: str
    alert_type: str
    target_value: str

class SettingsRequest(BaseModel):
    custom_prompt: str
    ai_tone: str
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    discord_webhook_url: str = ""
    email_smtp_server: str = ""
    email_smtp_port: str = ""
    email_sender: str = ""
    email_password: str = ""
    email_recipient: str = ""

class PortfolioCreateRequest(BaseModel):
    name: str

class TransactionRequest(BaseModel):
    symbol: str
    type: str  # 'BUY' oder 'SELL'
    quantity: float
    price: float
    date: str

class TaxSimulateRequest(BaseModel):
    symbol: str
    sell_quantity: float
    sell_price: float



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
        from backend.db import add_asset, asset_exists
        symbol = item.symbol.strip().upper()
        name = item.name.strip()
        asset_type = item.type.strip().lower()
        
        if not symbol or not name or asset_type not in ["stock", "crypto", "commodity"]:
            raise HTTPException(status_code=400, detail="Ungültige Asset-Daten.")
            
        if asset_exists(symbol):
            raise HTTPException(status_code=400, detail=f"Asset {symbol} existiert bereits in der Watchlist.")
            
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
    except HTTPException:
        raise
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
            

        return {"status": "success", "message": f"Asset {symbol_upper} gelöscht."}
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Assets {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/portfolio")
def get_portfolio(portfolio_id: int = 1):
    """Holt das Portfolio des Nutzers aus der Datenbank."""
    try:
        from backend.db import get_portfolio_from_db
        return get_portfolio_from_db(portfolio_id)
    except Exception as e:
        logger.error(f"Fehler beim Laden des Portfolios: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Laden des Portfolios.")


@app.post("/api/portfolio")
def add_portfolio_item_route(item: PortfolioItem, portfolio_id: int = 1):
    """Speichert oder aktualisiert ein Asset im Portfolio."""
    try:
        from backend.db import save_portfolio_item
        success = save_portfolio_item(item.symbol, item.quantity, item.buy_price, portfolio_id)
        if not success:
            raise HTTPException(status_code=500, detail="Fehler beim Speichern in der Datenbank.")
        return {"status": "success", "message": f"Asset {item.symbol} im Portfolio gespeichert."}
    except Exception as e:
        logger.error(f"Fehler beim Speichern des Portfolio-Items {item.symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/portfolio/{symbol}")
def delete_portfolio_item_route(symbol: str, portfolio_id: int = 1):
    """Löscht ein Asset aus dem Portfolio."""
    try:
        from backend.db import delete_portfolio_item
        success = delete_portfolio_item(symbol, portfolio_id)
        if not success:
            raise HTTPException(status_code=500, detail="Fehler beim Löschen in der Datenbank.")
        return {"status": "success", "message": f"Asset {symbol} aus dem Portfolio gelöscht."}
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Portfolio-Items {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Neue Routen für Settings, Multi-Portfolio & FIFO ---

@app.get("/api/portfolios")
def get_portfolios_route():
    """Holt alle Portfolio-Profile."""
    try:
        from backend.db import get_portfolios
        return get_portfolios()
    except Exception as e:
        logger.error(f"Fehler beim Laden der Portfolios: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Laden der Portfolio-Profile.")


@app.post("/api/portfolios")
def create_portfolio_route(req: PortfolioCreateRequest):
    """Erstellt ein neues Portfolio-Profil."""
    try:
        from backend.db import create_portfolio
        success = create_portfolio(req.name)
        if not success:
            raise HTTPException(status_code=400, detail="Portfolio-Profil konnte nicht erstellt werden (Name evtl. bereits vergeben).")
        return {"status": "success", "message": f"Portfolio '{req.name}' erfolgreich erstellt."}
    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Portfolios: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/portfolios/{portfolio_id}")
def delete_portfolio_route(portfolio_id: int):
    """Löscht ein Portfolio-Profil."""
    try:
        from backend.db import delete_portfolio
        if portfolio_id == 1:
            raise HTTPException(status_code=400, detail="Das Standard-Portfolio darf nicht gelöscht werden.")
        success = delete_portfolio(portfolio_id)
        if not success:
            raise HTTPException(status_code=500, detail="Fehler beim Löschen des Portfolios.")
        return {"status": "success", "message": "Portfolio erfolgreich gelöscht."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Portfolios: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/settings")
def get_settings_route():
    """Holt alle KI- und System-Einstellungen."""
    try:
        from backend.db import get_setting
        return {
            "custom_prompt": get_setting("custom_prompt", ""),
            "ai_tone": get_setting("ai_tone", "professionell"),
            "telegram_bot_token": get_setting("telegram_bot_token", ""),
            "telegram_chat_id": get_setting("telegram_chat_id", ""),
            "discord_webhook_url": get_setting("discord_webhook_url", ""),
            "email_smtp_server": get_setting("email_smtp_server", ""),
            "email_smtp_port": get_setting("email_smtp_port", ""),
            "email_sender": get_setting("email_sender", ""),
            "email_password": get_setting("email_password", ""),
            "email_recipient": get_setting("email_recipient", "")
        }
    except Exception as e:
        logger.error(f"Fehler beim Laden der Einstellungen: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Laden der Einstellungen.")


@app.post("/api/settings")
def save_settings_route(settings: SettingsRequest):
    """Speichert die KI- und System-Einstellungen."""
    try:
        from backend.db import save_setting
        success_prompt = save_setting("custom_prompt", settings.custom_prompt)
        success_tone = save_setting("ai_tone", settings.ai_tone)
        
        # Save notification settings
        save_setting("telegram_bot_token", settings.telegram_bot_token)
        save_setting("telegram_chat_id", settings.telegram_chat_id)
        save_setting("discord_webhook_url", settings.discord_webhook_url)
        save_setting("email_smtp_server", settings.email_smtp_server)
        save_setting("email_smtp_port", settings.email_smtp_port)
        save_setting("email_sender", settings.email_sender)
        save_setting("email_password", settings.email_password)
        save_setting("email_recipient", settings.email_recipient)
        
        if not success_prompt or not success_tone:
            raise HTTPException(status_code=500, detail="Fehler beim Speichern der Haupteinstellungen.")
        return {"status": "success", "message": "Einstellungen erfolgreich gespeichert."}
    except Exception as e:
        logger.error(f"Fehler beim Speichern des Settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/portfolio/{portfolio_id}/transactions")
def get_transactions_route(portfolio_id: int):
    """Holt alle Transaktionen eines Portfolios."""
    try:
        from backend.db import get_transactions
        return get_transactions(portfolio_id)
    except Exception as e:
        logger.error(f"Fehler beim Laden der Transaktionen: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Laden der Transaktionen.")


@app.post("/api/portfolio/{portfolio_id}/transactions")
def add_transaction_route(portfolio_id: int, tx: TransactionRequest):
    """Fügt eine Transaktion hinzu und passt den Portfolio-Bestand an."""
    try:
        from backend.db import add_transaction
        success = add_transaction(
            portfolio_id=portfolio_id,
            symbol=tx.symbol,
            tx_type=tx.type,
            quantity=tx.quantity,
            price=tx.price,
            date=tx.date
        )
        if not success:
            raise HTTPException(status_code=500, detail="Fehler beim Hinzufügen der Transaktion.")
        return {"status": "success", "message": "Transaktion hinzugefügt und Portfolio aktualisiert."}
    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen der Transaktion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/portfolio/{portfolio_id}/transactions/{tx_id}")
def delete_transaction_route(portfolio_id: int, tx_id: int):
    """Löscht eine Transaktion und berechnet den Portfolio-Bestand neu."""
    try:
        from backend.db import delete_transaction
        success = delete_transaction(tx_id, portfolio_id)
        if not success:
            raise HTTPException(status_code=500, detail="Fehler beim Löschen der Transaktion.")
        return {"status": "success", "message": "Transaktion gelöscht und Portfolio-Bestand neu berechnet."}
    except Exception as e:
        logger.error(f"Fehler beim Löschen der Transaktion: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/api/portfolio/{portfolio_id}/tax-simulate")
def tax_simulate_route(portfolio_id: int, req: TaxSimulateRequest):
    """Führt eine FIFO-Steuersimulation für einen Verkauf durch."""
    try:
        from backend.db import calculate_fifo_tax
        result = calculate_fifo_tax(
            portfolio_id=portfolio_id,
            symbol=req.symbol,
            sell_qty=req.sell_quantity,
            sell_price=req.sell_price
        )
        return result
    except Exception as e:
        logger.error(f"Fehler bei der FIFO-Steuersimulation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/portfolio/{portfolio_id}/export/csv")
def export_portfolio_csv(portfolio_id: int):
    """Exportiert das Portfolio als CSV."""
    from backend.db import get_portfolio_from_db
    import io
    import csv
    from fastapi.responses import StreamingResponse
    try:
        holdings = get_portfolio_from_db(portfolio_id)
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        writer.writerow(["Symbol", "Menge", "Durchschnittlicher Kaufpreis"])
        for h in holdings:
            writer.writerow([h["symbol"], h["quantity"], h["buy_price"]])
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=portfolio_{portfolio_id}_export.csv"}
        )
    except Exception as e:
        logger.error(f"Fehler beim CSV-Export: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/portfolio/{portfolio_id}/export/print")
def export_portfolio_print(portfolio_id: int):
    """Liefert einen druckfreundlichen Report für das Portfolio."""
    from backend.db import get_portfolio_from_db, get_predictions_from_db, get_portfolios
    from fastapi.responses import HTMLResponse
    import datetime
    try:
        portfolios = get_portfolios()
        portfolio_name = "Unbekanntes Portfolio"
        for p in portfolios:
            if p["id"] == portfolio_id:
                portfolio_name = p["name"]
                break

        holdings = get_portfolio_from_db(portfolio_id)
        predictions_data = get_predictions_from_db().get("predictions", {})

        rows_html = ""
        total_val = 0.0
        now_str = datetime.datetime.now().strftime('%d.%m.%Y %H:%M')

        for h in holdings:
            symbol = h["symbol"]
            qty = h["quantity"]
            bp = h["buy_price"]
            pred = predictions_data.get(symbol, {})
            cp = pred.get("price", bp)
            val = qty * cp
            total_val += val
            rec = pred.get("recommendation", "N/A")
            rows_html += f"""
            <tr>
                <td>{symbol}</td>
                <td>{qty}</td>
                <td>{bp:.2f} €</td>
                <td>{cp:.2f} €</td>
                <td>{val:.2f} €</td>
                <td>{rec}</td>
            </tr>
            """

        html_content = f"""
        <!DOCTYPE html>
        <html lang="de">
        <head>
            <meta charset="UTF-8">
            <title>Portfolio-Report: {portfolio_name}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    color: #333;
                    margin: 40px;
                    line-height: 1.6;
                }}
                h1 {{
                    color: #1a365d;
                    border-bottom: 2px solid #3182ce;
                    padding-bottom: 10px;
                }}
                .meta {{
                    font-size: 0.9em;
                    color: #718096;
                    margin-bottom: 30px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 30px;
                }}
                th, td {{
                    border: 1px solid #e2e8f0;
                    padding: 12px;
                    text-align: left;
                }}
                th {{
                    background-color: #ebf8ff;
                    color: #2b6cb0;
                }}
                .total {{
                    font-size: 1.2em;
                    font-weight: bold;
                    text-align: right;
                    color: #2b6cb0;
                }}
                @media print {{
                    body {{ margin: 0; }}
                    button {{ display: none; }}
                }}
            </style>
        </head>
        <body>
            <h1>AlphaPulse AI Portfolio-Zusammenfassung</h1>
            <div class="meta">
                <strong>Portfolio:</strong> {portfolio_name}<br>
                <strong>Erstellt am:</strong> {now_str}
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Menge</th>
                        <th>Durchschnittlicher Kaufpreis</th>
                        <th>Aktueller Preis</th>
                        <th>Gesamtwert</th>
                        <th>KI-Empfehlung</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
            <div class="total">Gesamtwert: {total_val:.2f} €</div>
            <script>
                window.onload = function() {{
                    window.print();
                }}
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
    except Exception as e:
        logger.error(f"Fehler beim Druckexport: {e}")
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


@app.get("/api/search/{symbol}")
def search_ticker(symbol: str):
    """Sucht nach einem Ticker-Symbol über Yahoo Finance und liefert Name und Typ zurück."""
    try:
        symbol_upper = symbol.strip().upper()
        ticker = yf.Ticker(symbol_upper)
        info = ticker.info
        
        if not info or not info.get('quoteType'):
            raise HTTPException(status_code=404, detail="Symbol nicht gefunden.")
            
        name = info.get('longName') or info.get('shortName') or symbol_upper
        quote_type = info.get('quoteType').upper()
        
        if quote_type == "EQUITY":
            asset_type = "stock"
        elif quote_type == "CRYPTOCURRENCY":
            asset_type = "crypto"
            if name.endswith(" USD"):
                name = name[:-4]
        elif quote_type in ["FUTURE", "COMMODITY"]:
            asset_type = "commodity"
            if name == symbol_upper or not name or name == "None":
                comm_names = {
                    "GC=F": "Gold",
                    "SI=F": "Silber",
                    "CL=F": "Rohöl",
                    "PL=F": "Platin",
                    "HG=F": "Kupfer"
                }
                name = comm_names.get(symbol_upper, symbol_upper)
        else:
            asset_type = "stock"
            
        return {
            "symbol": symbol_upper,
            "name": name,
            "type": asset_type
        }
    except Exception as e:
        logger.error(f"Fehler bei Ticker-Suche für {symbol}: {e}")
        from backend.config import DEFAULT_ASSETS
        for asset in DEFAULT_ASSETS:
            if asset["symbol"].upper() == symbol.strip().upper():
                return asset
        raise HTTPException(status_code=404, detail="Ticker konnte nicht gefunden werden.")


@app.get("/api/accuracy")
def get_prediction_accuracy():
    """Berechnet die Genauigkeit der bisherigen KI-Prognosen (Trefferquote)."""
    try:
        from backend.db import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT h.symbol, h.price AS pred_price, h.recommendation, h.last_updated, p.price AS current_price
            FROM prediction_history h
            JOIN predictions p ON h.symbol = p.symbol
        """)
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return {
                "accuracy": 0.0,
                "total_evaluated": 0,
                "correct_count": 0,
                "message": "Nicht genügend historische Daten vorhanden für eine Auswertung."
            }
            
        correct_count = 0
        total_evaluated = 0
        
        for row in rows:
            pred_price = row["pred_price"]
            current_price = row["current_price"]
            rec = row["recommendation"]
            
            if not pred_price or not current_price or not rec:
                continue
                
            total_evaluated += 1
            is_correct = False
            
            if rec in ["Kauf", "Starker Kauf"]:
                if current_price > pred_price:
                    is_correct = True
            elif rec in ["Verkauf", "Starker Verkauf"]:
                if current_price < pred_price:
                    is_correct = True
            elif rec == "Halten":
                pct_diff = abs(current_price - pred_price) / pred_price
                if pct_diff <= 0.03:
                    is_correct = True
                    
            if is_correct:
                correct_count += 1
                
        accuracy = round((correct_count / total_evaluated) * 100, 1) if total_evaluated > 0 else 0.0
        
        return {
            "accuracy": accuracy,
            "total_evaluated": total_evaluated,
            "correct_count": correct_count
        }
    except Exception as e:
        logger.error(f"Fehler beim Berechnen der KI-Genauigkeit: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@app.post("/api/chat")
def handle_chat_query(req: ChatRequest, background_tasks: BackgroundTasks):
    """Beantwortet Fragen des Nutzers basierend auf Portfolio und Watchlist-Daten."""
    try:
        from backend.db import get_predictions_from_db, get_portfolio_from_db, add_asset, delete_asset, add_chat_message, add_transaction
        from backend.ai_analyzer import generate_chat_response
        import datetime
        
        msg = req.message.strip()
        portfolio_id = req.portfolio_id
        current_date = datetime.date.today().strftime('%Y-%m-%d')
        
        # Save user message to chat history
        add_chat_message(portfolio_id, "user", msg)
        
        # 1. Befehlserkennung
        if msg.startswith("/"):
            parts = msg.split()
            cmd = parts[0].lower()
            
            if cmd == "/add" and len(parts) >= 4:
                # /add SYMBOL MENGE KAUFPREIS
                symbol = parts[1].upper()
                try:
                    qty = float(parts[2])
                    price = float(parts[3])
                    
                    # Watchlist prüfen (yfinance validieren)
                    try:
                        ticker_info = search_ticker(symbol)
                        # Als Asset in Watchlist hinzufügen falls nicht vorhanden
                        add_asset(symbol, ticker_info["name"], ticker_info["type"])
                    except Exception:
                        pass
                        
                    # Buchen einer Transaktion (dadurch wird das Portfolio automatisch aktualisiert)
                    add_transaction(portfolio_id, symbol, 'BUY', qty, price, current_date)
                    
                    response_text = f"✅ **Erfolgreich hinzugefügt!** {qty}x **{symbol}** für je {price}$ wurde als Kauf in dein Portfolio (Profil: {portfolio_id}) eingetragen."
                    add_chat_message(portfolio_id, "bot", response_text)
                    return {
                        "response": response_text,
                        "trigger_refresh": True
                    }
                except Exception as e:
                    response_text = f"❌ Fehler beim Hinzufügen: {str(e)}. Syntax: `/add SYMBOL MENGE KAUFPREIS`"
                    add_chat_message(portfolio_id, "bot", response_text)
                    return {
                        "response": response_text,
                        "trigger_refresh": False
                    }
                    
            elif (cmd == "/remove" or cmd == "/delete") and len(parts) >= 2:
                # /remove SYMBOL
                symbol = parts[1].upper()
                try:
                    # Finde den aktuellen Bestand im Portfolio, um ihn zu nullen
                    holdings = get_portfolio_from_db(portfolio_id)
                    item = next((h for h in holdings if h["symbol"] == symbol), None)
                    
                    if item and item["quantity"] > 0:
                        predictions_data = get_predictions_from_db().get("predictions", {})
                        pred = predictions_data.get(symbol, {})
                        sell_price = pred.get("price") or item["buy_price"]
                        
                        # Transaktion buchen, die den Bestand eliminiert
                        add_transaction(portfolio_id, symbol, 'SELL', item["quantity"], sell_price, current_date)
                        response_text = f"🗑️ **Erfolgreich gelöscht!** Asset **{symbol}** wurde über einen Komplettverkauf aus deinem Portfolio entfernt."
                    else:
                        response_text = f"ℹ️ Asset **{symbol}** befindet sich nicht in diesem Portfolio."
                    
                    add_chat_message(portfolio_id, "bot", response_text)
                    return {
                        "response": response_text,
                        "trigger_refresh": True
                    }
                except Exception as e:
                    response_text = f"❌ Fehler beim Entfernen: {str(e)}"
                    add_chat_message(portfolio_id, "bot", response_text)
                    return {
                        "response": response_text,
                        "trigger_refresh": False
                    }
                    
            elif cmd == "/watch" and len(parts) >= 2:
                # /watch SYMBOL
                symbol = parts[1].upper()
                try:
                    ticker_info = search_ticker(symbol)
                    add_asset(symbol, ticker_info["name"], ticker_info["type"])
                    
                    # Asynchrone Analyse starten
                    from backend.scheduler import analyze_single_asset_background
                    background_tasks.add_task(analyze_single_asset_background, {
                        "symbol": symbol,
                        "name": ticker_info["name"],
                        "type": ticker_info["type"]
                    })
                    response_text = f"👀 **Erfolgreich!** Asset **{symbol}** ({ticker_info['name']}) wird jetzt beobachtet. Die KI-Analyse läuft im Hintergrund."
                    add_chat_message(portfolio_id, "bot", response_text)
                    return {
                        "response": response_text,
                        "trigger_refresh": True
                    }
                except Exception as e:
                    response_text = f"❌ Asset konnte nicht gefunden werden: {str(e)}"
                    add_chat_message(portfolio_id, "bot", response_text)
                    return {
                        "response": response_text,
                        "trigger_refresh": False
                    }
                    
            elif cmd == "/unwatch" and len(parts) >= 2:
                # /unwatch SYMBOL
                symbol = parts[1].upper()
                delete_asset(symbol)
                response_text = f"❌ **Beobachtung beendet!** Asset **{symbol}** wurde aus der Watchlist entfernt."
                add_chat_message(portfolio_id, "bot", response_text)
                return {
                    "response": response_text,
                    "trigger_refresh": True
                }
                
            else:
                response_text = (
                    "ℹ️ **Verfügbare Chat-Befehle:**\n"
                    "- `/watch SYMBOL` - Fügt Asset zur Watchlist hinzu\n"
                    "- `/unwatch SYMBOL` - Entfernt Asset aus Watchlist\n"
                    "- `/add SYMBOL MENGE KAUFPREIS` - Fügt Asset zum Portfolio hinzu\n"
                    "- `/remove SYMBOL` - Entfernt Asset aus Portfolio"
                )
                add_chat_message(portfolio_id, "bot", response_text)
                return {
                    "response": response_text,
                    "trigger_refresh": False
                }
        
        # Reguläre AI Chat-Antwort
        predictions_data = get_predictions_from_db().get("predictions", {})
        portfolio_data = get_portfolio_from_db(portfolio_id)
        ai_response = generate_chat_response(msg, portfolio_data, predictions_data, portfolio_id=portfolio_id)
        
        add_chat_message(portfolio_id, "bot", ai_response)
        return {"response": ai_response, "trigger_refresh": False}
    except Exception as e:
        logger.error(f"Fehler bei Chat-Anfrage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/backtest")
def get_backtest_history():
    """Holt die vollständige Historie der Prognosen für detailliertes Backtesting."""
    try:
        from backend.db import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT h.symbol, h.price AS pred_price, h.recommendation, h.confidence, h.last_updated, p.name, p.price AS current_price
            FROM prediction_history h
            JOIN predictions p ON h.symbol = p.symbol
            ORDER BY h.last_updated DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        
        history_list = []
        for row in rows:
            pred_price = row["pred_price"]
            current_price = row["current_price"]
            rec = row["recommendation"]
            
            is_correct = False
            if rec in ["Kauf", "Starker Kauf"]:
                if current_price > pred_price:
                    is_correct = True
            elif rec in ["Verkauf", "Starker Verkauf"]:
                if current_price < pred_price:
                    is_correct = True
            elif rec == "Halten":
                pct_diff = abs(current_price - pred_price) / pred_price
                if pct_diff <= 0.03:
                    is_correct = True
                    
            history_list.append({
                "symbol": row["symbol"],
                "name": row["name"],
                "pred_price": pred_price,
                "current_price": current_price,
                "recommendation": rec,
                "confidence": row["confidence"],
                "last_updated": row["last_updated"],
                "is_correct": is_correct
            })
            
        return history_list
    except Exception as e:
        logger.error(f"Fehler beim Laden der Backtest-Historie: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/exchange-rate")
def get_exchange_rate():
    """Liefert den aktuellen USD/EUR-Wechselkurs."""
    try:
        from backend.data_fetcher import fetch_exchange_rate
        return {"rate": fetch_exchange_rate()}
    except Exception as e:
        logger.error(f"Fehler beim Laden des Wechselkurses: {e}")
        return {"rate": 0.92}


@app.get("/api/alerts")
def get_alerts():
    """Liefert alle aktiven Alarme."""
    try:
        from backend.db import get_all_alerts
        return get_all_alerts()
    except Exception as e:
        logger.error(f"Fehler beim Laden der Alarme: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Laden der Alarme.")


@app.post("/api/alerts")
def create_new_alert(alert: AlertRequest):
    """Erstellt einen neuen Alarm."""
    try:
        from backend.db import add_alert
        success = add_alert(alert.symbol, alert.alert_type, alert.target_value)
        if not success:
            raise HTTPException(status_code=500, detail="Fehler beim Speichern des Alarms.")
        return {"status": "success", "message": f"Alarm für {alert.symbol} erstellt."}
    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Alarms: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/alerts/{alert_id}")
def delete_alert_route(alert_id: int):
    """Löscht einen bestehenden Alarm."""
    try:
        from backend.db import delete_alert
        success = delete_alert(alert_id)
        if not success:
            raise HTTPException(status_code=500, detail="Fehler beim Löschen des Alarms.")
        return {"status": "success", "message": f"Alarm {alert_id} gelöscht."}
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Alarms: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/alerts/triggered")
def get_triggered_alerts_route():
    """Liefert alle ausgelösten Alarme."""
    try:
        from backend.db import get_triggered_alerts
        return get_triggered_alerts()
    except Exception as e:
        logger.error(f"Fehler beim Laden der ausgelösten Alarme: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/backtest/simulate")
def simulate_strategy(symbol: str, strategy: str, years: int = 1):
    """Simuliert eine Handelsstrategie (rsi, sma, macd) über einen Zeitraum."""
    try:
        import pandas as pd
        import numpy as np
        symbol_upper = symbol.strip().upper()
        ticker = yf.Ticker(symbol_upper)
        
        # Etwas mehr Daten abrufen für gleitende Durchschnitte
        period = f"{years}y"
        df = ticker.history(period=period)
        if df.empty:
            raise HTTPException(status_code=404, detail="Keine historischen Daten gefunden.")
            
        close_prices = df['Close']
        
        # Indikatoren berechnen
        # RSI
        delta = close_prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        loss = loss.replace(0, 0.00001)
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # SMA
        sma_20 = close_prices.rolling(window=20).mean()
        sma_50 = close_prices.rolling(window=50).mean()
        
        # MACD
        exp1 = close_prices.ewm(span=12, adjust=False).mean()
        exp2 = close_prices.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        macd_signal = macd.ewm(span=9, adjust=False).mean()
        
        # Simulation
        cash = 10000.0
        shares = 0.0
        trade_count = 0
        
        sim_history = []
        buy_hold_shares = 10000.0 / float(close_prices.iloc[0])
        
        start_idx = 50 if len(close_prices) > 50 else 0
        
        for i in range(start_idx, len(df)):
            date_str = df.index[i].strftime('%Y-%m-%d')
            price = float(close_prices.iloc[i])
            
            buy_signal = False
            sell_signal = False
            
            if strategy == "rsi":
                curr_rsi = rsi.iloc[i]
                if not pd.isna(curr_rsi):
                    if curr_rsi < 30:
                        buy_signal = True
                    elif curr_rsi > 70:
                        sell_signal = True
            elif strategy == "sma":
                curr_sma20 = sma_20.iloc[i]
                curr_sma50 = sma_50.iloc[i]
                prev_sma20 = sma_20.iloc[i-1] if i > 0 else curr_sma20
                prev_sma50 = sma_50.iloc[i-1] if i > 0 else curr_sma50
                if not pd.isna(curr_sma20) and not pd.isna(curr_sma50):
                    if prev_sma20 <= prev_sma50 and curr_sma20 > curr_sma50:
                        buy_signal = True
                    elif prev_sma20 >= prev_sma50 and curr_sma20 < curr_sma50:
                        sell_signal = True
            elif strategy == "macd":
                curr_macd = macd.iloc[i]
                curr_sig = macd_signal.iloc[i]
                prev_macd = macd.iloc[i-1] if i > 0 else curr_macd
                prev_sig = macd_signal.iloc[i-1] if i > 0 else curr_sig
                if not pd.isna(curr_macd) and not pd.isna(curr_sig):
                    if prev_macd <= prev_sig and curr_macd > curr_sig:
                        buy_signal = True
                    elif prev_macd >= prev_sig and curr_macd < curr_sig:
                        sell_signal = True
                        
            if buy_signal and cash > 0:
                shares = cash / price
                cash = 0.0
                trade_count += 1
            elif sell_signal and shares > 0:
                cash = shares * price
                shares = 0.0
                trade_count += 1
                
            strat_val = cash + (shares * price)
            bh_val = buy_hold_shares * price
            
            sim_history.append({
                "date": date_str,
                "strategy_val": round(strat_val, 2),
                "buy_hold_val": round(bh_val, 2),
                "price": round(price, 2)
            })
            
        final_strat_val = cash + (shares * float(close_prices.iloc[-1]))
        final_bh_val = buy_hold_shares * float(close_prices.iloc[-1])
        
        strat_return = ((final_strat_val - 10000.0) / 10000.0) * 100
        bh_return = ((final_bh_val - 10000.0) / 10000.0) * 100
        
        return {
            "symbol": symbol_upper,
            "strategy": strategy,
            "years": years,
            "total_trades": trade_count,
            "final_value": round(final_strat_val, 2),
            "strategy_return": round(strat_return, 2),
            "buy_hold_return": round(bh_return, 2),
            "history": sim_history
        }
    except Exception as e:
        logger.error(f"Fehler bei Strategie-Simulation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/portfolio/dividends")
def get_portfolio_dividends(portfolio_id: int = 1):
    """Berechnet die geschätzten monatlichen Dividenden-Zahlungen des Portfolios."""
    try:
        from backend.db import get_portfolio_from_db, get_predictions_from_db
        from backend.data_fetcher import fetch_dividend_history
        
        holdings = get_portfolio_from_db(portfolio_id)
        predictions = get_predictions_from_db().get("predictions", {})

        
        monthly_dividends = {m: 0.0 for m in range(1, 13)}
        annual_total = 0.0
        
        for item in holdings:
            symbol = item["symbol"]
            qty = item["quantity"]
            
            pred = predictions.get(symbol)
            if not pred:
                continue
                
            price = pred.get("price") or item["buy_price"]
            div_yield = pred.get("dividend_yield") or 0.0
            div_rate = pred.get("dividend_rate") or 0.0
            
            if div_rate > 0:
                holding_annual = qty * div_rate
            else:
                holding_annual = qty * price * div_yield
                
            if holding_annual <= 0:
                continue
                
            annual_total += holding_annual
            
            months = fetch_dividend_history(symbol)
            if not months:
                months = [3, 6, 9, 12]
                
            div_per_month = holding_annual / len(months)
            for m in months:
                monthly_dividends[m] += div_per_month
                
        for m in monthly_dividends:
            monthly_dividends[m] = round(monthly_dividends[m], 2)
            
        return {
            "monthly_dividends": monthly_dividends,
            "annual_total": round(annual_total, 2)
        }
    except Exception as e:
        logger.error(f"Fehler bei Dividendenberechnung: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/portfolio/{portfolio_id}/chat")
def get_portfolio_chat_route(portfolio_id: int):
    """Holt die Chat-Historie für das Portfolio."""
    try:
        from backend.db import get_chat_history
        return get_chat_history(portfolio_id)
    except Exception as e:
        logger.error(f"Fehler beim Laden des Chatverlaufs: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Laden des Chatverlaufs.")


@app.delete("/api/portfolio/{portfolio_id}/chat")
def delete_portfolio_chat_route(portfolio_id: int):
    """Löscht die Chat-Historie für das Portfolio."""
    try:
        from backend.db import clear_chat_history
        success = clear_chat_history(portfolio_id)
        if not success:
            raise HTTPException(status_code=500, detail="Fehler beim Löschen des Chatverlaufs.")
        return {"status": "success", "message": "Chatverlauf gelöscht."}
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Chatverlaufs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class TestNotificationRequest(BaseModel):
    message: str = "Test-Nachricht von AlphaPulse AI!"


@app.post("/api/settings/test-telegram")
def test_telegram_route(req: TestNotificationRequest):
    """Sendet eine Test-Benachrichtigung an Telegram."""
    from backend.notifications import send_telegram_notification
    success = send_telegram_notification(req.message)
    if not success:
        raise HTTPException(status_code=400, detail="Telegram Test fehlgeschlagen. Bitte Einstellungen prüfen.")
    return {"status": "success", "message": "Testnachricht an Telegram gesendet."}


@app.post("/api/settings/test-discord")
def test_discord_route(req: TestNotificationRequest):
    """Sendet eine Test-Benachrichtigung an Discord."""
    from backend.notifications import send_discord_notification
    success = send_discord_notification(req.message)
    if not success:
        raise HTTPException(status_code=400, detail="Discord Test fehlgeschlagen. Bitte Einstellungen prüfen.")
    return {"status": "success", "message": "Testnachricht an Discord gesendet."}


@app.post("/api/settings/test-email")
def test_email_route(req: TestNotificationRequest):
    """Sendet eine Test-E-Mail."""
    from backend.notifications import send_email_notification
    success = send_email_notification("AlphaPulse AI Test E-Mail", f"<h3>Test</h3><p>{req.message}</p>")
    if not success:
        raise HTTPException(status_code=400, detail="E-Mail Test fehlgeschlagen. Bitte Einstellungen prüfen.")
    return {"status": "success", "message": "Test E-Mail gesendet."}


# Finde den Pfad zum Frontend-Ordner
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

# Statische Dateien für das Frontend ausliefern (MUSS als letztes gemountet werden)
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=False)
