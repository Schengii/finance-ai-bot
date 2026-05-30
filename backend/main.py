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
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                last_updated = data.get("last_updated", "Unbekannt")
        except Exception as e:
            logger.error(f"Fehler beim Lesen des Update-Zeitstempels: {e}")
            
    return {
        "is_updating": scheduler.is_updating,
        "last_updated": last_updated
    }

@app.get("/api/predictions")
def get_predictions():
    """Gibt alle aktuellen Krypto- und Aktienprognosen zurück."""
    if not DATA_FILE.exists():
        return {
            "last_updated": "Nie",
            "predictions": {},
            "message": "Es wurden noch keine Daten generiert. Das erste Update läuft im Hintergrund."
        }
        
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"Fehler beim Laden der Prognosen: {e}")
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
