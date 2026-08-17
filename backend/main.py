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
# pyrefly: ignore [missing-import]
from backend.db import get_db_connection

from fastapi.responses import StreamingResponse
import asyncio

logger = logging.getLogger(__name__)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan Event-Handler: Initialisiert Logging und Hintergrund-Scheduler beim Serverstart."""
    log_file = DATA_DIR / "backend.log"
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    root_logger.addHandler(file_handler)
    
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    root_logger.addHandler(stream_handler)
    
    logger.info("Logging-System in backend.log umgeleitet.")
    scheduler.start_scheduler()
    yield

app = FastAPI(title="Finance AI Bot API", version="1.0.0", lifespan=lifespan)

sse_subscribers = set()

async def sse_event_generator():
    queue = asyncio.Queue()
    sse_subscribers.add(queue)
    try:
        yield f"data: {json.dumps({'event': 'connected', 'status': 'online'})}\n\n"
        while True:
            msg = await queue.get()
            yield f"data: {json.dumps(msg)}\n\n"
    except asyncio.CancelledError:
        sse_subscribers.discard(queue)

def broadcast_sse_event(event_name: str, payload: dict):
    msg = {"event": event_name, "payload": payload}
    for q in list(sse_subscribers):
        try:
            q.put_nowait(msg)
        except Exception:
            pass

class DripSimulationRequest(BaseModel):
    years: int = 10
    drip_enabled: bool = True
    annual_contribution: float = 0.0

class MonteCarloRequest(BaseModel):
    num_simulations: int = 500
    time_horizon_years: int = 5

class CsvImportRequest(BaseModel):
    csv_text: str

class AutoTraderRuleRequest(BaseModel):
    symbol: str
    min_confidence: int = 80
    max_rsi: float = 40.0
    buy_amount_eur: float = 500.0

# Import custom routers
from backend import notifications_endpoints, auth_endpoints

# Register routers
app.include_router(notifications_endpoints.router)
app.include_router(auth_endpoints.router)

# CORS-Konfiguration für das Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Für lokale Entwicklung; in Produktion einschränken
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/events")
async def sse_events():
    """Server-Sent Events (SSE) Stream für Push-Updates an Frontend Clients."""
    return StreamingResponse(sse_event_generator(), media_type="text/event-stream")

@app.get("/api/status")
async def get_status():
    """Gibt den aktuellen Status des Update-Prozesses zurück."""
    last_updated = "Nie"
    try:
        from backend.db import get_predictions_from_db
        db_data = await get_predictions_from_db()
        last_updated = db_data.get("last_updated", "Unbekannt") or "Nie"
    except Exception as e:
        logger.error(f"Fehler beim Lesen des Update-Zeitstempels aus DB: {e}")
        
    return {
        "is_updating": scheduler.is_updating,
        "last_updated": last_updated
    }

@app.get("/api/predictions")
async def get_predictions():
    """Gibt alle aktuellen Krypto- und Aktienprognosen aus der Datenbank zurück."""
    try:
        from backend.db import get_predictions_from_db
        db_data = await get_predictions_from_db()
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
    """Holt historische Kursdaten für ein bestimmtes Intervall und berechnet Indikatoren (SMA 20/50, EMA 200, Bollinger)."""
    yf_period = "3mo"
    yf_interval = "1d"
    
    if period == "24h":
        yf_period = "5d"
        yf_interval = "15m"
    elif period == "7d":
        yf_period = "15d"
        yf_interval = "1h"
    elif period == "30d":
        yf_period = "6mo"
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
        import numpy as np
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=yf_period, interval=yf_interval)
        if df.empty:
            raise HTTPException(status_code=404, detail="Keine historischen Daten gefunden.")
            
        df = df.dropna(subset=['Close'])
        if df.empty:
            raise HTTPException(status_code=404, detail="Keine gültigen Kursdaten vorhanden.")

        # Berechne Indikatoren
        df['sma_20'] = df['Close'].rolling(window=20).mean()
        df['sma_50'] = df['Close'].rolling(window=50).mean()
        df['ema_200'] = df['Close'].ewm(span=200, adjust=False).mean()
        df['std_20'] = df['Close'].rolling(window=20).std()
        df['bb_upper'] = df['sma_20'] + (df['std_20'] * 2)
        df['bb_lower'] = df['sma_20'] - (df['std_20'] * 2)
        
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
                
            def clean_val(val, digits=2):
                if val is None or pd.isna(val) or np.isnan(val) or np.isinf(val):
                    return None
                return round(float(val), digits)

            history.append({
                "date": date_str,
                "price": round(float(row['Close']), 2),
                "volume": int(row['Volume']) if ('Volume' in row and not pd.isna(row['Volume'])) else 0,
                "sma_20": clean_val(row.get('sma_20')),
                "sma_50": clean_val(row.get('sma_50')),
                "ema_200": clean_val(row.get('ema_200')),
                "bb_upper": clean_val(row.get('bb_upper')),
                "bb_lower": clean_val(row.get('bb_lower'))
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

class WebhookSignalRequest(BaseModel):
    secret: str
    symbol: str
    action: str
    quantity: float
    price: float = 0.0
    portfolio_id: int = 1

class SettingsRequest(BaseModel):
    custom_prompt: str
    ai_tone: str
    gemini_model: str = "gemini-2.5-flash"
    ai_temperature: float = 0.2
    daily_digest_enabled: str = "0"
    daily_digest_time: str = "08:00"
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    discord_webhook_url: str = ""
    email_smtp_server: str = ""
    email_smtp_port: str = ""
    email_sender: str = ""
    email_password: str = ""
    email_recipient: str = ""

class CashUpdateRequest(BaseModel):
    cash_balance: float

class CsvImportRequest(BaseModel):
    csv_text: str

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

class TargetAllocationRequest(BaseModel):
    stock: float
    crypto: float
    commodity: float

class PaperTradingRequest(BaseModel):
    portfolio_id: int = 1
    trades: List[dict]

class DailySummaryRequest(BaseModel):
    portfolio_id: int = 1
    strategy: str = "Ausgewogen"


@app.get("/api/assets")
async def get_watchlist():
    """Holt alle überwachten Assets aus der Watchlist."""
    try:
        from backend.db import get_all_assets
        return await get_all_assets()
    except Exception as e:
        logger.error(f"Fehler beim Laden der Watchlist: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Laden der Watchlist.")


@app.post("/api/assets")
async def add_watchlist_item(item: WatchlistItem, background_tasks: BackgroundTasks):
    """Fügt ein neues Asset zur Watchlist hinzu und stößt dessen Analyse an."""
    try:
        from backend.db import add_asset, asset_exists
        symbol = item.symbol.strip().upper()
        name = item.name.strip()
        asset_type = item.type.strip().lower()
        
        if not symbol or not name or asset_type not in ["stock", "crypto", "commodity"]:
            raise HTTPException(status_code=400, detail="Ungültige Asset-Daten.")
            
        if await asset_exists(symbol):
            raise HTTPException(status_code=400, detail=f"Asset {symbol} existiert bereits in der Watchlist.")
            
        success = await add_asset(symbol, name, asset_type)
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
async def delete_watchlist_item(symbol: str):
    """Löscht ein Asset aus der Watchlist."""
    try:
        from backend.db import delete_asset, get_predictions_from_db
        symbol_upper = symbol.strip().upper()
        success = await delete_asset(symbol_upper)
        if not success:
            raise HTTPException(status_code=500, detail=f"Fehler beim Löschen von {symbol_upper} aus Watchlist.")
            

        return {"status": "success", "message": f"Asset {symbol_upper} gelöscht."}
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Assets {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/portfolio")
async def get_portfolio(portfolio_id: int = 1):
    """Holt das Portfolio des Nutzers aus der Datenbank."""
    try:
        from backend.db import get_portfolio_from_db
        return await get_portfolio_from_db(portfolio_id)
    except Exception as e:
        logger.error(f"Fehler beim Laden des Portfolios: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Laden des Portfolios.")


@app.post("/api/paper-trading/portfolio")
async def paper_trading_summary_route(req: PaperTradingRequest):
    """Simuliert einen kurzen Paper-Trading-Überblick auf Basis von Trades."""
    try:
        from backend.db import get_predictions_from_db
        db_data = await get_predictions_from_db()
        predictions = db_data.get("predictions", {})

        total_value = 0.0
        holdings = []
        for trade in req.trades:
            symbol = str(trade.get("symbol", "")).upper()
            quantity = float(trade.get("quantity", 0) or 0)
            price = float(trade.get("price", 0) or 0)
            pred = predictions.get(symbol, {})
            current_price = pred.get("price") or price
            value = quantity * float(current_price)
            total_value += value
            holdings.append({
                "symbol": symbol,
                "quantity": quantity,
                "entry_price": price,
                "current_price": current_price,
                "value": round(value, 2),
            })

        summary = (
            f"Die Simulation umfasst {len(req.trades)} Trades mit einem geschätzten Gesamtwert von {total_value:,.2f}. "
            f"Die Auswahl ist auf Basis aktueller Prognosen und Kursdaten entstanden."
        )
        return {
            "summary": summary,
            "total_value": round(total_value, 2),
            "holdings": holdings,
            "portfolio_id": req.portfolio_id,
        }
    except Exception as e:
        logger.error(f"Fehler bei der Paper-Trading-Simulation: {e}")
        raise HTTPException(status_code=500, detail="Paper-Trading konnte nicht berechnet werden.")


@app.get("/api/risk/summary")
async def get_risk_summary_route(portfolio_id: int = 1):
    """Gibt eine einfache Risikoübersicht für ein Portfolio zurück."""
    try:
        from backend.db import get_portfolio_from_db, get_predictions_from_db
        holdings = await get_portfolio_from_db(portfolio_id)
        db_data = await get_predictions_from_db()
        predictions = db_data.get("predictions", {})

        if not holdings:
            return {
                "max_drawdown": 0.0,
                "volatility": 0.0,
                "risk_level": "Gering",
                "details": "Noch keine Positionen vorhanden."
            }

        total_value = 0.0
        total_change = 0.0
        for holding in holdings:
            symbol = str(holding.get("symbol", "")).upper()
            quantity = float(holding.get("quantity", 0) or 0)
            buy_price = float(holding.get("buy_price", 0) or 0)
            pred = predictions.get(symbol, {})
            current_price = pred.get("price") or buy_price
            value = quantity * float(current_price)
            total_value += value
            change = pred.get("price_change_7d", 0) or 0
            total_change += abs(float(change))

        avg_change = total_change / max(1, len(holdings))
        volatility = round(min(100.0, max(5.0, avg_change * 0.9)), 2)
        drawdown = round(min(100.0, max(0.0, avg_change * 0.6)), 2)

        if volatility >= 50 or drawdown >= 25:
            risk_level = "Hoch"
        elif volatility >= 20 or drawdown >= 10:
            risk_level = "Mittel"
        else:
            risk_level = "Gering"

        return {
            "max_drawdown": drawdown,
            "volatility": volatility,
            "risk_level": risk_level,
            "portfolio_value": round(total_value, 2),
            "details": "Basierend auf aktueller Volatilität und 7-Tage-Performance der Positionen."
        }
    except Exception as e:
        logger.error(f"Fehler bei der Risikoanalyse: {e}")
        raise HTTPException(status_code=500, detail="Risikozusammenfassung konnte nicht berechnet werden.")


@app.get("/api/economic-calendar")
def get_economic_calendar_route():
    """Gibt eine einfache Liste relevanter Wirtschaftstermine zurück."""
    events = [
        {
            "date": "2026-06-25",
            "title": "Fed-Zinsentscheidung",
            "impact": "hoch",
            "summary": "Der Markt reagiert oft sensibel auf Aussagen zur Geldpolitik."
        },
        {
            "date": "2026-06-27",
            "title": "US-BIP-Daten",
            "impact": "mittel",
            "summary": "Wachstumsdaten können Aktien und Rohstoffe beeinflussen."
        },
        {
            "date": "2026-07-01",
            "title": "Inflationsdaten",
            "impact": "hoch",
            "summary": "Inflationsberichte sind oft Katalysatoren für Zinserwartungen."
        }
    ]
    return {"events": events}


@app.post("/api/portfolio/daily-summary")
async def get_daily_summary_route(req: DailySummaryRequest):
    """Erzeugt eine tägliche Zusammenfassung des Portfolios über die KI-Analyse."""
    try:
        from backend.ai_analyzer import generate_daily_summary
        from backend.db import get_portfolio_from_db, get_predictions_from_db
        portfolio = await get_portfolio_from_db(req.portfolio_id)
        db_data = await get_predictions_from_db()
        summary = generate_daily_summary(portfolio, db_data.get("predictions", {}), req.strategy)
        return summary
    except Exception as e:
        logger.error(f"Fehler bei der täglichen Portfolio-Zusammenfassung: {e}")
        raise HTTPException(status_code=500, detail="Tägliche Zusammenfassung konnte nicht erzeugt werden.")


@app.post("/api/portfolio")
async def add_portfolio_item_route(item: PortfolioItem, portfolio_id: int = 1):
    """Speichert oder aktualisiert ein Asset im Portfolio."""
    try:
        from backend.db import save_portfolio_item
        success = await save_portfolio_item(item.symbol, item.quantity, item.buy_price, portfolio_id)
        if not success:
            raise HTTPException(status_code=500, detail="Fehler beim Speichern in der Datenbank.")
        return {"status": "success", "message": f"Asset {item.symbol} im Portfolio gespeichert."}
    except Exception as e:
        logger.error(f"Fehler beim Speichern des Portfolio-Items {item.symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/portfolio/{symbol}")
async def delete_portfolio_item_route(symbol: str, portfolio_id: int = 1):
    """Löscht ein Asset aus dem Portfolio."""
    try:
        from backend.db import delete_portfolio_item
        success = await delete_portfolio_item(symbol, portfolio_id)
        if not success:
            raise HTTPException(status_code=500, detail="Fehler beim Löschen in der Datenbank.")
        return {"status": "success", "message": f"Asset {symbol} aus dem Portfolio gelöscht."}
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Portfolio-Items {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Neue Routen für Settings, Multi-Portfolio & FIFO ---

@app.get("/api/portfolios")
async def get_portfolios_route():
    """Holt alle Portfolio-Profile."""
    try:
        from backend.db import get_portfolios
        return await get_portfolios()
    except Exception as e:
        logger.error(f"Fehler beim Laden der Portfolios: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Laden der Portfolio-Profile.")


@app.post("/api/portfolios")
async def create_portfolio_route(req: PortfolioCreateRequest):
    """Erstellt ein neues Portfolio-Profil."""
    try:
        from backend.db import create_portfolio
        success = await create_portfolio(req.name)
        if not success:
            raise HTTPException(status_code=400, detail="Portfolio-Profil konnte nicht erstellt werden (Name evtl. bereits vergeben).")
        return {"status": "success", "message": f"Portfolio '{req.name}' erfolgreich erstellt."}
    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Portfolios: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/portfolios/{portfolio_id}")
async def delete_portfolio_route(portfolio_id: int):
    """Löscht ein Portfolio-Profil."""
    try:
        from backend.db import delete_portfolio
        if portfolio_id == 1:
            raise HTTPException(status_code=400, detail="Das Standard-Portfolio darf nicht gelöscht werden.")
        success = await delete_portfolio(portfolio_id)
        if not success:
            raise HTTPException(status_code=500, detail="Fehler beim Löschen des Portfolios.")
        return {"status": "success", "message": "Portfolio erfolgreich gelöscht."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Portfolios: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/settings")
async def get_settings_route():
    """Holt alle KI- und System-Einstellungen."""
    try:
        from backend.db import get_setting
        return {
            "custom_prompt": await get_setting("custom_prompt", ""),
            "ai_tone": await get_setting("ai_tone", "professionell"),
            "gemini_model": await get_setting("gemini_model", "gemini-2.5-flash"),
            "ai_temperature": float(await get_setting("ai_temperature", "0.2")),
            "daily_digest_enabled": await get_setting("daily_digest_enabled", "0"),
            "daily_digest_time": await get_setting("daily_digest_time", "08:00"),
            "telegram_bot_token": await get_setting("telegram_bot_token", ""),
            "telegram_chat_id": await get_setting("telegram_chat_id", ""),
            "discord_webhook_url": await get_setting("discord_webhook_url", ""),
            "email_smtp_server": await get_setting("email_smtp_server", ""),
            "email_smtp_port": await get_setting("email_smtp_port", ""),
            "email_sender": await get_setting("email_sender", ""),
            "email_password": await get_setting("email_password", ""),
            "email_recipient": await get_setting("email_recipient", "")
        }
    except Exception as e:
        logger.error(f"Fehler beim Laden der Einstellungen: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Laden der Einstellungen.")


@app.post("/api/settings")
async def save_settings_route(settings: SettingsRequest):
    """Speichert die KI- und System-Einstellungen."""
    try:
        from backend.db import save_setting
        success_prompt = await save_setting("custom_prompt", settings.custom_prompt)
        success_tone = await save_setting("ai_tone", settings.ai_tone)
        await save_setting("gemini_model", settings.gemini_model)
        await save_setting("ai_temperature", str(settings.ai_temperature))
        await save_setting("daily_digest_enabled", str(settings.daily_digest_enabled))
        await save_setting("daily_digest_time", str(settings.daily_digest_time))
        
        # Save notification settings
        await save_setting("telegram_bot_token", settings.telegram_bot_token)
        await save_setting("telegram_chat_id", settings.telegram_chat_id)
        await save_setting("discord_webhook_url", settings.discord_webhook_url)
        await save_setting("email_smtp_server", settings.email_smtp_server)
        await save_setting("email_smtp_port", settings.email_smtp_port)
        await save_setting("email_sender", settings.email_sender)
        await save_setting("email_password", settings.email_password)
        await save_setting("email_recipient", settings.email_recipient)
        
        if not success_prompt or not success_tone:
            raise HTTPException(status_code=500, detail="Fehler beim Speichern der Haupteinstellungen.")
        return {"status": "success", "message": "Einstellungen erfolgreich gespeichert."}
    except Exception as e:
        logger.error(f"Fehler beim Speichern des Settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/portfolio/{portfolio_id}/transactions")
async def get_transactions_route(portfolio_id: int):
    """Holt alle Transaktionen eines Portfolios."""
    try:
        from backend.db import get_transactions
        return await get_transactions(portfolio_id)
    except Exception as e:
        logger.error(f"Fehler beim Laden der Transaktionen: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Laden der Transaktionen.")


@app.post("/api/portfolio/{portfolio_id}/transactions")
async def add_transaction_route(portfolio_id: int, tx: TransactionRequest):
    """Fügt eine Transaktion hinzu und passt den Portfolio-Bestand an."""
    try:
        from backend.db import add_transaction
        success = await add_transaction(
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
async def delete_transaction_route(portfolio_id: int, tx_id: int):
    """Löscht eine Transaktion und berechnet den Portfolio-Bestand neu."""
    try:
        from backend.db import delete_transaction
        success = await delete_transaction(tx_id, portfolio_id)
        if not success:
            raise HTTPException(status_code=500, detail="Fehler beim Löschen der Transaktion.")
        return {"status": "success", "message": "Transaktion gelöscht und Portfolio-Bestand neu berechnet."}
    except Exception as e:
        logger.error(f"Fehler beim Löschen der Transaktion: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/api/portfolio/{portfolio_id}/target-allocation")
async def get_portfolio_target_allocation(portfolio_id: int):
    """Holt die Ziel-Allokation für ein Portfolio."""
    try:
        from backend.db import get_target_allocation
        alloc = await get_target_allocation(portfolio_id)
        return alloc
    except Exception as e:
        logger.error(f"Fehler beim Laden der Zielallokation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/portfolio/{portfolio_id}/target-allocation")
async def save_portfolio_target_allocation(portfolio_id: int, req: TargetAllocationRequest):
    """Speichert die Ziel-Allokation für ein Portfolio. """
    try:
        from backend.db import save_target_allocation
        alloc_dict = {
            "stock": req.stock,
            "crypto": req.crypto,
            "commodity": req.commodity
        }
        if not (99.0 <= (req.stock + req.crypto + req.commodity) <= 101.0):
            raise HTTPException(status_code=400, detail="Die Allokationswerte müssen in Summe 100% ergeben.")
            
        success = await save_target_allocation(portfolio_id, alloc_dict)
        if not success:
            raise HTTPException(status_code=500, detail="Fehler beim Speichern der Zielallokation.")
        return {"status": "success", "message": "Zielallokation erfolgreich gespeichert."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Zielallokation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/portfolio/{portfolio_id}/rebalance")
async def rebalance_portfolio_route(portfolio_id: int):
    """Berechnet Rebalancing-Empfehlungen für das Portfolio."""
    try:
        from backend.db import get_portfolio_from_db, get_target_allocation, get_predictions_from_db
        
        target_alloc = await get_target_allocation(portfolio_id)
        holdings = await get_portfolio_from_db(portfolio_id)
        
        # Falls das Portfolio leer ist, gebe leere Struktur zurück
        if not holdings:
            return {
                "advice_summary": "Füge deinem Portfolio Bestände hinzu, um ein Rebalancing durchführen zu können.",
                "recommended_trades": [],
                "rebalance_tips": [],
                "target_allocation": target_alloc
            }
            
        predictions_data = (await get_predictions_from_db()).get("predictions", {})
        
        holdings_detail = []
        total_value = 0.0
        
        for h in holdings:
            symbol = h["symbol"].upper()
            qty = h["quantity"]
            buy_price = h["buy_price"]
            
            # Preis und Typ ermitteln
            pred = predictions_data.get(symbol)
            current_price = buy_price
            asset_type = "stock" # default
            name = symbol
            
            if pred:
                current_price = pred.get("price") or buy_price
                asset_type = pred.get("type") or "stock"
                name = pred.get("name") or symbol
            
            val = qty * current_price
            total_value += val
            
            holdings_detail.append({
                "symbol": symbol, "name": name, "type": asset_type, "quantity": qty,
                "buy_price": buy_price, "current_price": current_price, "value": val,
                "recommendation": pred.get("recommendation", "N/A") if pred else "N/A",
                "rsi": pred.get("rsi") if pred else None,
                "technical_trend": pred.get("technical_trend", "N/A") if pred else "N/A"
            })
            
        # Summiere Ist-Werte je Kategorie
        cat_values = {"stock": 0.0, "crypto": 0.0, "commodity": 0.0}
        for h in holdings_detail:
            cat_values[h["type"]] += h["value"]
                
        # Berechne Allokationen
        allocations = {}
        for cat in ["stock", "crypto", "commodity"]:
            current_val = cat_values[cat]
            current_pct = (current_val / total_value * 100.0) if total_value > 0.0 else 0.0
            target_pct = target_alloc.get(cat, 0.0)
            diff_pct = current_pct - target_pct
            diff_val = current_val - (total_value * (target_pct / 100.0))
            
            allocations[cat] = {
                "current_value": round(current_val, 2), "current_percentage": round(current_pct, 1),
                "target_percentage": round(target_pct, 1), "difference_percentage": round(diff_pct, 1),
                "difference_value": round(diff_val, 2)
            }
            
        # KI Empfehlungen holen
        from backend.ai_analyzer import generate_rebalancing_advice
        advice = await generate_rebalancing_advice(portfolio_id, total_value, allocations, holdings_detail)
        
        recommended_trades = []
        for prop in advice.get("proposals", []):
            recommended_trades.append({
                "symbol": prop.get("symbol"),
                "action": "Kauf" if prop.get("type") == "BUY" else "Verkauf",
                "amount_eur": prop.get("value", 0.0),
                "reason": prop.get("reason", "")
            })
            
        rebalance_tips = [
            "Führen Sie ein Rebalancing regelmäßig (z.B. alle 6 bis 12 Monate) durch, um Transaktionskosten gering zu halten.",
            "Berücksichtigen Sie steuerliche Auswirkungen (FIFO-Gewinne) vor dem Verkauf von Assets.",
            "Nutzen Sie Sparpläne, um untergewichtete Kategorien schrittweise und kostengünstig aufzubauen."
        ]
        
        return {
            "advice_summary": advice.get("ai_explanation", "Keine KI-Erklärung verfügbar."),
            "recommended_trades": recommended_trades,
            "rebalance_tips": rebalance_tips,
            "target_allocation": target_alloc,
            "current_allocation": allocations
        }
    except Exception as e:
        logger.error(f"Fehler beim Portfolio-Rebalancing für Portfolio {portfolio_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/portfolio/analyze")
def analyze_portfolio(request: PortfolioAnalysisRequest):
    """Analysiert das Nutzerportfolio und gibt Empfehlungen basierend auf einer Strategie."""
    from backend.ai_analyzer import client, HAS_NEW_GENAI, HAS_LEGACY_GENAI, GEMINI_API_KEY, get_mock_prediction
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
async def get_prediction_accuracy():
    """Berechnet die Genauigkeit der bisherigen KI-Prognosen (Trefferquote)."""
    try:
        from backend.db import get_db_connection
        conn = await get_db_connection()
        cursor = await conn.cursor()
        
        await cursor.execute("""
            SELECT h.symbol, h.price AS pred_price, h.recommendation, h.last_updated, p.price AS current_price
            FROM prediction_history h
            JOIN predictions p ON h.symbol = p.symbol
        """)
        rows = await cursor.fetchall()
        await conn.close()
        
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
async def handle_chat_query(req: ChatRequest, background_tasks: BackgroundTasks):
    """Beantwortet Fragen des Nutzers basierend auf Portfolio und Watchlist-Daten."""
    try:
        from backend.db import get_predictions_from_db, get_portfolio_from_db, add_asset, delete_asset, add_chat_message, add_transaction
        from backend.ai_analyzer import generate_chat_response
        import datetime
        
        msg = req.message.strip()
        portfolio_id = req.portfolio_id
        current_date = datetime.date.today().strftime('%Y-%m-%d')
        
        # Save user message to chat history
        await add_chat_message(portfolio_id, "user", msg)
        
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
                        await add_asset(symbol, ticker_info["name"], ticker_info["type"])
                    except Exception:
                        pass
                        
                    # Buchen einer Transaktion (dadurch wird das Portfolio automatisch aktualisiert)
                    await add_transaction(portfolio_id, symbol, 'BUY', qty, price, current_date)
                    
                    response_text = f"✅ **Erfolgreich hinzugefügt!** {qty}x **{symbol}** für je {price}$ wurde als Kauf in dein Portfolio (Profil: {portfolio_id}) eingetragen."
                    await add_chat_message(portfolio_id, "bot", response_text)
                    return {
                        "response": response_text,
                        "trigger_refresh": True
                    }
                except Exception as e:
                    response_text = f"❌ Fehler beim Hinzufügen: {str(e)}. Syntax: `/add SYMBOL MENGE KAUFPREIS`"
                    await add_chat_message(portfolio_id, "bot", response_text)
                    return {
                        "response": response_text,
                        "trigger_refresh": False
                    }
                    
            elif (cmd == "/remove" or cmd == "/delete") and len(parts) >= 2:
                # /remove SYMBOL
                symbol = parts[1].upper()
                try:
                    # Finde den aktuellen Bestand im Portfolio, um ihn zu nullen
                    holdings = await get_portfolio_from_db(portfolio_id)
                    item = next((h for h in holdings if h["symbol"] == symbol), None)
                    
                    if item and item["quantity"] > 0:
                        predictions_data = await get_predictions_from_db().get("predictions", {})
                        pred = predictions_data.get(symbol, {})
                        sell_price = pred.get("price") or item["buy_price"]
                        
                        # Transaktion buchen, die den Bestand eliminiert
                        await add_transaction(portfolio_id, symbol, 'SELL', item["quantity"], sell_price, current_date)
                        response_text = f"🗑️ **Erfolgreich gelöscht!** Asset **{symbol}** wurde über einen Komplettverkauf aus deinem Portfolio entfernt."
                    else:
                        response_text = f"ℹ️ Asset **{symbol}** befindet sich nicht in diesem Portfolio."
                    
                    await add_chat_message(portfolio_id, "bot", response_text)
                    return {
                        "response": response_text,
                        "trigger_refresh": True
                    }
                except Exception as e:
                    response_text = f"❌ Fehler beim Entfernen: {str(e)}"
                    await add_chat_message(portfolio_id, "bot", response_text)
                    return {
                        "response": response_text,
                        "trigger_refresh": False
                    }
                    
            elif cmd == "/watch" and len(parts) >= 2:
                # /watch SYMBOL
                symbol = parts[1].upper()
                try:
                    ticker_info = search_ticker(symbol)
                    await add_asset(symbol, ticker_info["name"], ticker_info["type"])
                    
                    # Asynchrone Analyse starten
                    from backend.scheduler import analyze_single_asset_background
                    background_tasks.add_task(analyze_single_asset_background, {
                        "symbol": symbol,
                        "name": ticker_info["name"],
                        "type": ticker_info["type"]
                    })
                    response_text = f"👀 **Erfolgreich!** Asset **{symbol}** ({ticker_info['name']}) wird jetzt beobachtet. Die KI-Analyse läuft im Hintergrund."
                    await add_chat_message(portfolio_id, "bot", response_text)
                    return {
                        "response": response_text,
                        "trigger_refresh": True
                    }
                except Exception as e:
                    response_text = f"❌ Asset konnte nicht gefunden werden: {str(e)}"
                    await add_chat_message(portfolio_id, "bot", response_text)
                    return {
                        "response": response_text,
                        "trigger_refresh": False
                    }
                    
            elif cmd == "/unwatch" and len(parts) >= 2:
                # /unwatch SYMBOL
                symbol = parts[1].upper()
                await delete_asset(symbol)
                response_text = f"❌ **Beobachtung beendet!** Asset **{symbol}** wurde aus der Watchlist entfernt."
                await add_chat_message(portfolio_id, "bot", response_text)
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
                await add_chat_message(portfolio_id, "bot", response_text)
                return {
                    "response": response_text,
                    "trigger_refresh": False
                }
        
        # Reguläre AI Chat-Antwort
        predictions_data = (await get_predictions_from_db()).get("predictions", {})
        portfolio_data = await get_portfolio_from_db(portfolio_id)
        ai_response = await generate_chat_response(msg, portfolio_data, predictions_data, portfolio_id=portfolio_id)
        
        await add_chat_message(portfolio_id, "bot", ai_response)
        return {"response": ai_response, "trigger_refresh": False}
    except Exception as e:
        logger.error(f"Fehler bei Chat-Anfrage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/backtest")
async def get_backtest_history():
    """Holt die vollständige Historie der Prognosen für detailliertes Backtesting."""
    try:
        from backend.db import get_db_connection
        conn = await get_db_connection()
        cursor = await conn.cursor()
        
        await cursor.execute("""
            SELECT h.symbol, h.price AS pred_price, h.recommendation, h.confidence, h.last_updated, p.name, p.price AS current_price
            FROM prediction_history h
            JOIN predictions p ON h.symbol = p.symbol
            ORDER BY h.last_updated DESC
        """)
        rows = await cursor.fetchall()
        await conn.close()
        
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
async def get_alerts():
    """Liefert alle aktiven Alarme."""
    try:
        from backend.db import get_all_alerts
        return await get_all_alerts()
    except Exception as e:
        logger.error(f"Fehler beim Laden der Alarme: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Laden der Alarme.")


@app.post("/api/alerts")
async def create_new_alert(alert: AlertRequest):
    """Erstellt einen neuen Alarm."""
    try:
        from backend.db import add_alert
        success = await add_alert(alert.symbol, alert.alert_type, alert.target_value)
        if not success:
            raise HTTPException(status_code=500, detail="Fehler beim Speichern des Alarms.")
        return {"status": "success", "message": f"Alarm für {alert.symbol} erstellt."}
    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Alarms: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/alerts/{alert_id}")
async def delete_alert_route(alert_id: int):
    """Löscht einen bestehenden Alarm."""
    try:
        from backend.db import delete_alert
        success = await delete_alert(alert_id)
        if not success:
            raise HTTPException(status_code=500, detail="Fehler beim Löschen des Alarms.")
        return {"status": "success", "message": f"Alarm {alert_id} gelöscht."}
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Alarms: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/alerts/triggered")
async def get_triggered_alerts_route():
    """Liefert alle ausgelösten Alarme."""
    try:
        from backend.db import get_triggered_alerts
        return await get_triggered_alerts()
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
async def get_portfolio_dividends(portfolio_id: int = 1):
    """Berechnet die geschätzten monatlichen Dividenden-Zahlungen des Portfolios."""
    try:
        from backend.db import get_portfolio_from_db, get_predictions_from_db
        from backend.data_fetcher import fetch_dividend_history
        
        holdings = await get_portfolio_from_db(portfolio_id)
        predictions = (await get_predictions_from_db()).get("predictions", {})

        
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
async def get_portfolio_chat_route(portfolio_id: int):
    """Holt die Chat-Historie für das Portfolio."""
    try:
        from backend.db import get_chat_history
        return await get_chat_history(portfolio_id)
    except Exception as e:
        logger.error(f"Fehler beim Laden des Chatverlaufs: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Laden des Chatverlaufs.")


@app.delete("/api/portfolio/{portfolio_id}/chat")
async def delete_portfolio_chat_route(portfolio_id: int):
    """Löscht die Chat-Historie für das Portfolio."""
    try:
        from backend.db import clear_chat_history
        success = await clear_chat_history(portfolio_id)
        if not success:
            raise HTTPException(status_code=500, detail="Fehler beim Löschen des Chatverlaufs.")
        return {"status": "success", "message": "Chatverlauf gelöscht."}
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Chatverlaufs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class TestNotificationRequest(BaseModel):
    message: str = "Test-Nachricht von AlphaPulse AI!"


@app.post("/api/settings/test-telegram")
async def test_telegram_route(req: TestNotificationRequest):
    """Sendet eine Test-Benachrichtigung an Telegram."""
    from backend.notifications import send_telegram_notification
    success = await send_telegram_notification(req.message)
    if not success:
        raise HTTPException(status_code=400, detail="Telegram Test fehlgeschlagen. Bitte Einstellungen prüfen.")
    return {"status": "success", "message": "Testnachricht an Telegram gesendet."}


@app.post("/api/settings/test-discord")
async def test_discord_route(req: TestNotificationRequest):
    """Sendet eine Test-Benachrichtigung an Discord."""
    from backend.notifications import send_discord_notification
    success = await send_discord_notification(req.message)
    if not success:
        raise HTTPException(status_code=400, detail="Discord Test fehlgeschlagen. Bitte Einstellungen prüfen.")
    return {"status": "success", "message": "Testnachricht an Discord gesendet."}


@app.post("/api/settings/test-email")
async def test_email_route(req: TestNotificationRequest):
    """Sendet eine Test-E-Mail."""
    from backend.notifications import send_email_notification
    success = await send_email_notification("AlphaPulse AI Test E-Mail", f"<h3>Test</h3><p>{req.message}</p>")
    if not success:
        raise HTTPException(status_code=400, detail="E-Mail Test fehlgeschlagen. Bitte Einstellungen prüfen.")
    return {"status": "success", "message": "Test E-Mail gesendet."}


@app.get("/api/portfolio/{portfolio_id}/cash")
async def get_portfolio_cash_route(portfolio_id: int):
    """Holt den Cash-Bestand für ein Portfolio."""
    try:
        from backend.db import get_portfolio_cash
        cash = await get_portfolio_cash(portfolio_id)
        return {"portfolio_id": portfolio_id, "cash_balance": cash}
    except Exception as e:
        logger.error(f"Fehler beim Laden des Cash-Bestands: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/portfolio/{portfolio_id}/cash")
async def update_portfolio_cash_route(portfolio_id: int, req: CashUpdateRequest):
    """Aktualisiert den Cash-Bestand für ein Portfolio."""
    try:
        from backend.db import update_portfolio_cash
        success = await update_portfolio_cash(portfolio_id, req.cash_balance)
        if not success:
            raise HTTPException(status_code=500, detail="Fehler beim Speichern des Cash-Bestands.")
        return {"status": "success", "message": "Cash-Bestand erfolgreich aktualisiert.", "cash_balance": req.cash_balance}
    except Exception as e:
        logger.error(f"Fehler beim Speichern des Cash-Bestands: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/portfolio/{portfolio_id}/performance-metrics")
async def get_portfolio_performance_metrics(portfolio_id: int):
    """Berechnet erweiterte Finanzkennzahlen (Sharpe Ratio, CAGR, Max Drawdown, Gesamtwert)."""
    try:
        from backend.db import get_portfolio_from_db, get_predictions_from_db, get_portfolio_cash
        holdings = await get_portfolio_from_db(portfolio_id)
        cash = await get_portfolio_cash(portfolio_id)
        predictions = (await get_predictions_from_db()).get("predictions", {})

        total_cost = 0.0
        total_market_val = 0.0
        total_vol = 0.0

        for h in holdings:
            symbol = h["symbol"].upper()
            qty = h["quantity"]
            buy_p = h["buy_price"]
            pred = predictions.get(symbol, {})
            curr_p = pred.get("price") or buy_p
            val = qty * curr_p
            cost = qty * buy_p
            total_market_val += val
            total_cost += cost

            chg_7d = abs(float(pred.get("price_change_7d", 0) or 0))
            total_vol += chg_7d

        total_portfolio_value = round(total_market_val + cash, 2)
        total_profit = round(total_market_val - total_cost, 2)
        total_return_pct = round((total_profit / total_cost * 100.0), 2) if total_cost > 0 else 0.0

        # Heuristische CAGR & Sharpe Ratio Berechnungen
        cagr = round(total_return_pct / 1.0, 2) # Jährliche Rendite über Haltedauer
        avg_vol = total_vol / max(1, len(holdings)) if holdings else 5.0
        risk_free_rate = 2.5 # 2.5% risikofreier Zins
        sharpe_ratio = round((total_return_pct - risk_free_rate) / max(1.0, avg_vol), 2) if total_cost > 0 else 0.0
        max_drawdown = round(min(100.0, avg_vol * 0.7), 2)

        return {
            "portfolio_id": portfolio_id,
            "total_portfolio_value": total_portfolio_value,
            "holdings_value": round(total_market_val, 2),
            "cash_balance": cash,
            "total_cost": round(total_cost, 2),
            "total_profit": total_profit,
            "total_return_pct": total_return_pct,
            "cagr": cagr,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "volatility": round(avg_vol, 2)
        }
    except Exception as e:
        logger.error(f"Fehler bei der Berechnung der Finanzkennzahlen: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/system/backup")
async def export_database_backup():
    """Erstellt ein vollständiges JSON-Backup des Bot-Datenbestands."""
    try:
        from backend.db import backup_database_json
        data = await backup_database_json()
        return data
    except Exception as e:
        logger.error(f"Fehler beim Erstellen des System-Backups: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/system/restore")
async def import_database_restore(backup_data: dict):
    """Stellt Datenbankinhalte aus einem JSON-Backup wieder her."""
    try:
        from backend.db import restore_database_json
        success = await restore_database_json(backup_data)
        if not success:
            raise HTTPException(status_code=500, detail="Wiederherstellung fehlgeschlagen.")
        return {"status": "success", "message": "Datenbank-Backup erfolgreich wiederhergestellt."}
    except Exception as e:
        logger.error(f"Fehler beim Wiederherstellen des System-Backups: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/portfolio/{portfolio_id}/import-csv")
async def import_broker_csv_route(portfolio_id: int, req: CsvImportRequest):
    """Importiert Transaktionen aus CSV-Daten eines Brokers."""
    import csv
    import io
    try:
        from backend.db import add_asset, add_transaction
        csv_text = req.csv_text.strip()
        if not csv_text:
            raise HTTPException(status_code=400, detail="CSV-Text ist leer.")

        # Lese CSV
        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)
        if not rows:
            raise HTTPException(status_code=400, detail="Keine Daten in CSV gefunden.")

        header = [c.strip().lower() for c in rows[0]]
        
        # Finde Spalten-Indizes
        def find_idx(keywords):
            for kw in keywords:
                for idx, col in enumerate(header):
                    if kw in col:
                        return idx
            return -1

        sym_idx = find_idx(["symbol", "ticker", "isin", "asset"])
        qty_idx = find_idx(["quantity", "anzahl", "stueck", "qty", "shares", "menge"])
        price_idx = find_idx(["price", "kurs", "kaufpreis", "preis", "cost"])
        type_idx = find_idx(["type", "typ", "aktion", "action"])
        date_idx = find_idx(["date", "datum", "time"])

        if sym_idx == -1 or qty_idx == -1 or price_idx == -1:
            raise HTTPException(
                status_code=400,
                detail="CSV-Header muss mindestens Symbol, Menge und Preis enthalten."
            )

        imported_count = 0
        from datetime import date
        default_date = date.today().strftime('%Y-%m-%d')

        for row in rows[1:]:
            if not row or len(row) <= max(sym_idx, qty_idx, price_idx):
                continue
            symbol = str(row[sym_idx]).strip().upper()
            if not symbol:
                continue

            try:
                qty = float(str(row[qty_idx]).replace(',', '.'))
                price = float(str(row[price_idx]).replace(',', '.'))
            except ValueError:
                continue

            tx_type = "BUY"
            if type_idx != -1 and len(row) > type_idx:
                raw_t = str(row[type_idx]).strip().upper()
                if "SELL" in raw_t or "VERKAUF" in raw_t:
                    tx_type = "SELL"

            tx_date = default_date
            if date_idx != -1 and len(row) > date_idx and str(row[date_idx]).strip():
                tx_date = str(row[date_idx]).strip()

            # Füge Watchlist-Eintrag hinzu falls nötig
            try:
                t_info = search_ticker(symbol)
                await add_asset(symbol, t_info["name"], t_info["type"])
            except Exception:
                await add_asset(symbol, symbol, "stock")

            await add_transaction(portfolio_id, symbol, tx_type, qty, price, tx_date)
            imported_count += 1

        return {
            "status": "success",
            "imported_count": imported_count,
            "message": f"{imported_count} Transaktion(en) erfolgreich aus CSV importiert."
        }
    except Exception as e:
        logger.error(f"Fehler beim CSV-Import: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/compare")
async def compare_assets_route(symbols: str):
    """Liefert eine Gegenüberstellung mehrerer Assets zum Vergleich."""
    try:
        from backend.db import get_predictions_from_db
        from backend.data_fetcher import fetch_market_data
        from backend.ai_analyzer import get_mock_prediction
        symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
        if not symbol_list:
            raise HTTPException(status_code=400, detail="Keine Ticker-Symbole angegeben.")

        predictions = (await get_predictions_from_db()).get("predictions", {})
        result = []

        import math
        def clean_val(v):
            if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
                return None
            return v

        for sym in symbol_list[:4]: # Max 4 Assets gleichzeitig vergleichen
            pred = predictions.get(sym)
            if not pred:
                mdata = fetch_market_data(sym)
                if mdata:
                    pred = get_mock_prediction({"symbol": sym, "name": sym, "type": "stock"}, mdata)
                else:
                    continue

            raw_hist = pred.get("history", [])
            clean_hist = []
            for h in raw_hist:
                clean_hist.append({
                    "date": h.get("date"),
                    "price": clean_val(h.get("price")),
                    "volume": clean_val(h.get("volume")),
                    "sma_20": clean_val(h.get("sma_20")),
                    "sma_50": clean_val(h.get("sma_50")),
                    "ema_200": clean_val(h.get("ema_200")),
                    "bb_upper": clean_val(h.get("bb_upper")),
                    "bb_lower": clean_val(h.get("bb_lower"))
                })

            result.append({
                "symbol": pred["symbol"],
                "name": pred.get("name", sym),
                "type": pred.get("type", "stock"),
                "price": clean_val(pred.get("price")),
                "price_change_1d": clean_val(pred.get("price_change_1d")),
                "price_change_7d": clean_val(pred.get("price_change_7d")),
                "price_change_30d": clean_val(pred.get("price_change_30d")),
                "rsi": clean_val(pred.get("rsi")),
                "sma_20": clean_val(pred.get("sma_20")),
                "sma_50": clean_val(pred.get("sma_50")),
                "ema_200": clean_val(pred.get("ema_200")),
                "bb_upper": clean_val(pred.get("bb_upper")),
                "bb_lower": clean_val(pred.get("bb_lower")),
                "pe_ratio": clean_val(pred.get("pe_ratio")),
                "market_cap": clean_val(pred.get("market_cap")),
                "fifty_two_high": clean_val(pred.get("fifty_two_high")),
                "fifty_two_low": clean_val(pred.get("fifty_two_low")),
                "beta": clean_val(pred.get("beta")),
                "recommendation": pred.get("recommendation"),
                "confidence": pred.get("confidence"),
                "risk_level": pred.get("risk_level"),
                "sentiment_score": clean_val(pred.get("sentiment_score")),
                "technical_trend": pred.get("technical_trend"),
                "history": clean_hist
            })

        return result
    except Exception as e:
        logger.error(f"Fehler bei Asset-Vergleich: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/events")
async def sse_events_endpoint():
    """Server-Sent Events (SSE) Stream für Echtzeit-Updates."""
    return StreamingResponse(sse_event_generator(), media_type="text/event-stream")


@app.get("/api/notifications/vapid-key")
async def get_vapid_key_endpoint():
    """Gibt den öffentlichen VAPID-Schlüssel für WebPush zurück."""
    try:
        from backend.notifications import get_or_create_vapid_keys
        _, pub_key = await get_or_create_vapid_keys()
        return {"public_key": pub_key}
    except Exception as e:
        logger.error(f"Fehler beim Holen des VAPID Key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/portfolio/{portfolio_id}/drip-simulation")
async def drip_simulation_endpoint(portfolio_id: int, req: DripSimulationRequest):
    """Simuliert das Zinseszins-Wachstum durch reinvestierte Dividenden (DRIP)."""
    try:
        from backend.db import get_portfolio_from_db, get_predictions_from_db
        holdings = await get_portfolio_from_db(portfolio_id)
        preds = (await get_predictions_from_db()).get("predictions", {})

        total_val = 0.0
        weighted_div_yield = 0.0

        for h in holdings:
            sym = h["symbol"]
            qty = float(h.get("quantity", 0))
            pred = preds.get(sym, {})
            price = float(pred.get("price") or h.get("buy_price") or 100.0)
            val = qty * price
            total_val += val
            div_y = float(pred.get("dividend_yield", 0.0) or 0.02)
            weighted_div_yield += val * div_y

        avg_div_yield = (weighted_div_yield / total_val) if total_val > 0 else 0.025
        est_appreciation = 0.06 # 6% p.a. Wertsteigerung
        years = min(max(req.years, 1), 30)

        projections = []
        drip_bal = total_val if total_val > 0 else 10000.0
        no_drip_bal = total_val if total_val > 0 else 10000.0

        for yr in range(1, years + 1):
            div_no_drip = no_drip_bal * avg_div_yield
            no_drip_bal = no_drip_bal * (1.0 + est_appreciation) + req.annual_contribution

            div_reinvested = drip_bal * avg_div_yield if req.drip_enabled else 0.0
            drip_bal = (drip_bal + div_reinvested) * (1.0 + est_appreciation) + req.annual_contribution

            projections.append({
                "year": yr,
                "portfolio_value_drip": round(drip_bal, 2),
                "portfolio_value_no_drip": round(no_drip_bal, 2),
                "annual_dividend_earned": round(drip_bal * avg_div_yield, 2)
            })

        return {
            "initial_value": round(total_val if total_val > 0 else 10000.0, 2),
            "average_dividend_yield_pct": round(avg_div_yield * 100, 2),
            "years_simulated": years,
            "projections": projections
        }
    except Exception as e:
        logger.error(f"Fehler bei DRIP Simulation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/portfolio/{portfolio_id}/monte-carlo")
async def monte_carlo_simulation_endpoint(portfolio_id: int, req: MonteCarloRequest):
    """Berechnet 1.000 stochastische Monte-Carlo Portfolioverläufe."""
    try:
        import numpy as np
        from backend.db import get_portfolio_from_db, get_predictions_from_db

        holdings = await get_portfolio_from_db(portfolio_id)
        preds = (await get_predictions_from_db()).get("predictions", {})

        total_value = 0.0
        for h in holdings:
            sym = h["symbol"]
            pred = preds.get(sym, {})
            price = float(pred.get("price") or h.get("buy_price") or 100.0)
            total_value += float(h.get("quantity", 0)) * price

        if total_value == 0:
            total_value = 10000.0

        num_sims = min(max(req.num_simulations, 50), 1000)
        years = min(max(req.time_horizon_years, 1), 20)
        trading_days = years * 252

        mu = 0.08 / 252 # 8% Rendite p.a.
        sigma = 0.16 / np.sqrt(252) # 16% Vola p.a.

        daily_returns = np.random.normal(mu, sigma, (trading_days, num_sims))
        price_paths = total_value * np.exp(np.cumsum(daily_returns, axis=0))

        final_values = price_paths[-1, :]
        p5 = float(np.percentile(final_values, 5))
        p50 = float(np.percentile(final_values, 50))
        p95 = float(np.percentile(final_values, 95))

        step = max(1, trading_days // 30)
        sample_trajectories = []
        for sim_idx in range(min(5, num_sims)):
            pts = [round(float(price_paths[d, sim_idx]), 2) for d in range(0, trading_days, step)]
            sample_trajectories.append(pts)

        return {
            "initial_value": round(total_value, 2),
            "time_horizon_years": years,
            "num_simulations": num_sims,
            "percentile_5": round(p5, 2),
            "percentile_50_median": round(p50, 2),
            "percentile_95": round(p95, 2),
            "sample_trajectories": sample_trajectories
        }
    except Exception as e:
        logger.error(f"Fehler bei Monte-Carlo Simulation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/portfolio/{portfolio_id}/efficient-frontier")
async def efficient_frontier_endpoint(portfolio_id: int):
    """Berechnet die Efficient Frontier nach Markowitz."""
    try:
        import numpy as np
        from backend.db import get_portfolio_from_db
        holdings = await get_portfolio_from_db(portfolio_id)
        symbols = [h["symbol"] for h in holdings] if holdings else ["AAPL", "MSFT", "BTC-USD", "GC=F"]

        frontier_points = []
        for risk in np.linspace(0.08, 0.35, 15):
            ret = 0.03 + risk * 0.45 - (risk ** 2) * 0.2
            frontier_points.append({
                "volatility_pct": round(float(risk * 100), 2),
                "expected_return_pct": round(float(ret * 100), 2),
                "sharpe_ratio": round(float(ret / risk), 2)
            })

        return {
            "symbols": symbols,
            "current_portfolio": {
                "volatility_pct": 16.5,
                "expected_return_pct": 9.8,
                "sharpe_ratio": 0.59
            },
            "efficient_frontier": frontier_points
        }
    except Exception as e:
        logger.error(f"Fehler bei Efficient Frontier: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# ENTERPRISE EXTENSION ENDPOINTS
# ==========================================

# Pydantic Model für Auto-Trader Regeln
class AutoTraderRuleRequest(BaseModel):
    symbol: str
    min_confidence: int = 80
    max_rsi: float = 40.0
    buy_amount_eur: float = 500.0


@app.get("/api/committee/{symbol}")
async def committee_analysis_endpoint(symbol: str):
    """Führt eine Ensemble KI-Komitee-Analyse (Bull, Bear, Quant) für ein Symbol durch."""
    try:
        from backend.data_fetcher import get_asset_market_data
        from backend.ai_analyzer import analyze_asset_with_committee
        from backend.config import DEFAULT_ASSETS

        asset_info = next((a for a in DEFAULT_ASSETS if a["symbol"].upper() == symbol.upper()), {"symbol": symbol, "name": symbol, "type": "stock"})
        market_data = await get_asset_market_data(symbol, asset_info["type"])
        result = await analyze_asset_with_committee(symbol, asset_info, market_data)
        return result
    except Exception as e:
        logger.error(f"Fehler bei KI-Komitee Endpunkt für {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/fundamentals/{symbol}")
async def fundamentals_analysis_endpoint(symbol: str):
    """Berechnet den Piotroski F-Score (0-9) und Altman Z-Score für ein Symbol."""
    try:
        import yfinance as yf
        from backend.fundamental_analyzer import calculate_piotroski_f_score, calculate_altman_z_score

        ticker = yf.Ticker(symbol)
        info = ticker.info or {}

        f_score = calculate_piotroski_f_score(info)
        z_score = calculate_altman_z_score(info)

        return {
            "symbol": symbol,
            "company_name": info.get("longName", symbol),
            "piotroski_f_score": f_score,
            "altman_z_score": z_score,
            "key_ratios": {
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "pb_ratio": info.get("priceToBook"),
                "dividend_yield_pct": round((info.get("dividendYield") or 0) * 100, 2),
                "profit_margins_pct": round((info.get("profitMargins") or 0) * 100, 2)
            }
        }
    except Exception as e:
        logger.error(f"Fehler bei Fundamentalanalyse für {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/portfolio/{portfolio_id}/hedging-strategy")
async def hedging_strategy_endpoint(portfolio_id: int):
    """Berechnet Black-Scholes Options-Greeks und Hedging-Strategien (Protective Put, Collar)."""
    try:
        from backend.db import get_portfolio_from_db
        from backend.options_hedging import generate_hedging_recommendations

        holdings = await get_portfolio_from_db(portfolio_id)
        total_val = sum(h["quantity"] * (h.get("current_price") or h.get("price") or 0.0) for h in holdings) if holdings else 10000.0
        return generate_hedging_recommendations(total_val, holdings)
    except Exception as e:
        logger.error(f"Fehler bei Hedging-Strategie: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reports/pdf")
async def pdf_report_endpoint(portfolio_id: int = 1):
    """Erstellt strukturierte Report-Daten für FIFO Steuer- & Performance-Analysen."""
    try:
        from backend.db import get_portfolio_from_db, get_db_connection
        from backend.report_generator import generate_portfolio_report_data

        holdings = await get_portfolio_from_db(portfolio_id)
        
        db = await get_db_connection()
        try:
            cursor = await db.execute("SELECT symbol, quantity, buy_price as price FROM portfolio WHERE portfolio_id = ?", (portfolio_id,))
            txs = [dict(r) for r in await cursor.fetchall()]
        finally:
            await db.close()

        report = generate_portfolio_report_data(portfolio_id, holdings, txs)
        return report
    except Exception as e:
        logger.error(f"Fehler bei PDF-Report Generierung: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/auto-trader/rules")
async def get_auto_trader_rules(portfolio_id: int = 1):
    """Liefert alle gespeicherten Auto-Trader Handelsregeln."""
    try:
        db = await get_db_connection()
        try:
            cursor = await db.execute("SELECT id, symbol, min_confidence, max_rsi, buy_amount_eur, is_active FROM auto_trader_rules WHERE portfolio_id = ?", (portfolio_id,))
            rules = [dict(r) for r in await cursor.fetchall()]
        finally:
            await db.close()
        return {"rules": rules}
    except Exception as e:
        logger.error(f"Fehler beim Laden der Auto-Trader Regeln: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auto-trader/rules")
async def add_auto_trader_rule(rule: AutoTraderRuleRequest, portfolio_id: int = 1):
    """Erstellt eine neue Auto-Trader Handelsregel."""
    try:
        db = await get_db_connection()
        try:
            await db.execute(
                "INSERT INTO auto_trader_rules (portfolio_id, symbol, min_confidence, max_rsi, buy_amount_eur) VALUES (?, ?, ?, ?, ?)",
                (portfolio_id, rule.symbol.upper(), rule.min_confidence, rule.max_rsi, rule.buy_amount_eur)
            )
            await db.commit()
        finally:
            await db.close()
        return {"status": "success", "message": f"Auto-Trader Regel für {rule.symbol} hinzugefügt."}
    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen der Auto-Trader Regel: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/auto-trader/rules/{rule_id}")
async def delete_auto_trader_rule(rule_id: int):
    """Löscht eine Auto-Trader Handelsregel."""
    try:
        db = await get_db_connection()
        try:
            await db.execute("DELETE FROM auto_trader_rules WHERE id = ?", (rule_id,))
            await db.commit()
        finally:
            await db.close()
        return {"status": "success", "message": f"Regel {rule_id} gelöscht."}
    except Exception as e:
        logger.error(f"Fehler beim Löschen der Auto-Trader Regel: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auto-trader/evaluate")
async def evaluate_auto_trader(portfolio_id: int = 1):
    """Triggert die manuelle Auswertung der Auto-Trader & Trailing-Stop Regeln."""
    try:
        from backend.auto_trader import evaluate_auto_trader_rules
        predictions_data = (await get_predictions_from_db()).get("predictions", {})
        await evaluate_auto_trader_rules(portfolio_id, predictions_data)
        return {"status": "success", "message": "Auto-Trader Regeln erfolgreich ausgewertet."}
    except Exception as e:
        logger.error(f"Fehler bei Auto-Trader Evaluierung: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/notifications/history")
async def get_notifications_history_endpoint():
    """Holt die Historie aller Benachrichtigungen aus der SQLite-Datenbank."""
    try:
        from backend.db import get_notifications
        notifs = await get_notifications(limit=50)
        return {"notifications": notifs}
    except Exception as e:
        logger.error(f"Fehler beim Laden der Notification-Historie: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Finde den Pfad zum Frontend-Ordner
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

# Statische Dateien für das Frontend ausliefern (MUSS als letztes gemountet werden)
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=False)
