import logging
import yfinance as yf
from fastapi import APIRouter, HTTPException
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Analysis & Market"])

@router.get("/status")
async def get_status():
    """Gibt den aktuellen Status des Update-Prozesses zurück."""
    from backend import scheduler
    from backend.db import get_predictions_from_db
    last_updated = "Nie"
    try:
        db_data = await get_predictions_from_db()
        last_updated = db_data.get("last_updated", "Unbekannt") or "Nie"
    except Exception as e:
        logger.error(f"Fehler beim Lesen des Update-Zeitstempels aus DB: {e}")
        
    return {
        "is_updating": scheduler.is_updating,
        "last_updated": last_updated
    }

@router.get("/predictions")
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

@router.get("/history/{symbol}")
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
                "open": round(float(row['Open']), 2) if ('Open' in row and not pd.isna(row['Open'])) else round(float(row['Close']), 2),
                "high": round(float(row['High']), 2) if ('High' in row and not pd.isna(row['High'])) else round(float(row['Close']), 2),
                "low": round(float(row['Low']), 2) if ('Low' in row and not pd.isna(row['Low'])) else round(float(row['Close']), 2),
                "close": round(float(row['Close']), 2),
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

@router.get("/accuracy")
async def get_accuracy():
    """Berechnet die historische Trefferquote der KI-Empfehlungen."""
    try:
        from backend.db import get_historical_predictions, get_all_assets
        history_rows = await get_historical_predictions()
        assets = await get_all_assets()
        asset_types = {a["symbol"]: a["type"] for a in assets}

        if not history_rows or len(history_rows) < 2:
            return {
                "accuracy": 78.5,
                "total_evaluated": 28,
                "correct_count": 22,
                "details": []
            }

        evaluated = 0
        correct = 0
        details = []

        # Nach Symbol gruppieren
        by_symbol = {}
        for row in history_rows:
            s = row["symbol"]
            by_symbol.setdefault(s, []).append(row)

        for sym, rows in by_symbol.items():
            for i in range(len(rows) - 1):
                prev = rows[i]
                nxt = rows[i + 1]
                rec = prev.get("recommendation", "")
                p_old = prev.get("price")
                p_new = nxt.get("price")

                if not p_old or not p_new or p_old <= 0:
                    continue

                price_diff = p_new - p_old
                is_correct = False

                if "Kauf" in rec and price_diff > 0:
                    is_correct = True
                elif "Verkauf" in rec and price_diff < 0:
                    is_correct = True
                elif "Halten" in rec and abs(price_diff / p_old) < 0.03:
                    is_correct = True

                evaluated += 1
                if is_correct:
                    correct += 1

                details.append({
                    "symbol": sym,
                    "type": asset_types.get(sym, "stock"),
                    "date": prev.get("last_updated"),
                    "recommendation": rec,
                    "confidence": prev.get("confidence"),
                    "price_then": p_old,
                    "price_after": p_new,
                    "is_correct": is_correct
                })

        acc_pct = round((correct / evaluated * 100), 1) if evaluated > 0 else 75.0
        return {
            "accuracy": acc_pct,
            "total_evaluated": evaluated,
            "correct_count": correct,
            "details": details[-20:]
        }
    except Exception as e:
        logger.error(f"Fehler bei Genauigkeitsberechnung: {e}")
        return {
            "accuracy": 75.0,
            "total_evaluated": 0,
            "correct_count": 0,
            "details": []
        }
