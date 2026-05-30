import os
import sys
import json
import logging

# Übergeordnetes Verzeichnis zum Python-Pfad hinzufügen
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# pyrefly: ignore [missing-import]
from fastapi import FastAPI, BackgroundTasks, HTTPException
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
# pyrefly: ignore [missing-import]
from fastapi.staticfiles import StaticFiles
from backend.config import DATA_FILE
from backend.scheduler import start_scheduler, run_update_cycle, is_updating

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
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
    start_scheduler()

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
        "is_updating": is_updating,
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

@app.post("/api/refresh")
def trigger_refresh(background_tasks: BackgroundTasks):
    """Löst eine manuelle Aktualisierung der Marktdaten und KI-Analysen aus."""
    global is_updating
    if is_updating:
        return {"status": "updating", "message": "Aktualisierung läuft bereits."}
        
    # Führe Aktualisierung im Hintergrund aus
    background_tasks.add_task(run_update_cycle)
    return {"status": "started", "message": "Aktualisierungszyklus gestartet."}

# Finde den Pfad zum Frontend-Ordner
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

# Statische Dateien für das Frontend ausliefern (MUSS als letztes gemountet werden)
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
