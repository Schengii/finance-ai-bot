import json
import logging
import threading
from datetime import datetime
# pyrefly: ignore [missing-import]
from apscheduler.schedulers.background import BackgroundScheduler
# pyrefly: ignore [missing-import]
from backend.config import DEFAULT_ASSETS, DATA_FILE, UPDATE_INTERVAL_HOURS
# pyrefly: ignore [missing-import]
from backend.data_fetcher import fetch_market_data, fetch_news
# pyrefly: ignore [missing-import]
from backend.ai_analyzer import analyze_asset_with_ai

logger = logging.getLogger(__name__)

# Status-Variable, um zu sehen, ob gerade eine Aktualisierung läuft
is_updating = False

def run_update_cycle():
    """Führt einen vollständigen Aktualisierungszyklus für alle Assets durch."""
    global is_updating
    if is_updating:
        logger.warning("Aktualisierungszyklus läuft bereits. Überspringe...")
        return
        
    is_updating = True
    logger.info("Starte Aktualisierungszyklus...")
    
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        # Vorhandene Daten laden, um sie bei Fehlern beizubehalten
        existing_data = {}
        if DATA_FILE.exists():
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f).get("predictions", {})
            except Exception as e:
                logger.error(f"Fehler beim Laden bestehender Daten: {e}")

        predictions = {}
        
        for asset in DEFAULT_ASSETS:
            symbol = asset["symbol"]
            try:
                # 1. Marktdaten abrufen
                market_data = fetch_market_data(symbol)
                if not market_data:
                    logger.error(f"Konnte Marktdaten für {symbol} nicht laden. Verwende alte Daten falls vorhanden.")
                    if symbol in existing_data:
                        predictions[symbol] = existing_data[symbol]
                    continue
                    
                market_data["last_updated"] = timestamp
                
                # 2. Nachrichten abrufen
                news_items = fetch_news(symbol, asset["name"])
                
                # 3. KI-Prognose generieren
                prediction = analyze_asset_with_ai(asset, market_data, news_items)
                
                # Ergänze die Nachrichten und den Chartverlauf in dem gespeicherten Objekt
                prediction["news"] = news_items
                prediction["history"] = market_data["history"]
                
                predictions[symbol] = prediction
                logger.info(f"Analyse für {symbol} erfolgreich abgeschlossen.")
                
            except Exception as e:
                logger.error(f"Unerwarteter Fehler bei der Analyse von {symbol}: {e}")
                if symbol in existing_data:
                    predictions[symbol] = existing_data[symbol]
                    
        # Speichern der Daten
        output_data = {
            "last_updated": timestamp,
            "predictions": predictions
        }
        
        try:
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Aktualisierungszyklus abgeschlossen. Daten in {DATA_FILE} gespeichert.")
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Prognosedaten: {e}")
    finally:
        is_updating = False


def start_scheduler():
    """Initialisiert und startet den Hintergrund-Scheduler."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_update_cycle, 
        'interval', 
        hours=UPDATE_INTERVAL_HOURS, 
        id='market_analysis_job'
    )
    scheduler.start()
    logger.info(f"Hintergrund-Scheduler gestartet (Intervall: {UPDATE_INTERVAL_HOURS} Stunden).")
    
    # Führe einen ersten Lauf asynchron aus, falls die Datei noch nicht existiert
    # ODER falls die Datei existiert, aber leer/ungültig ist.
    should_update = not DATA_FILE.exists()
    if not should_update:
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not data.get("predictions"):
                    should_update = True
        except Exception:
            should_update = True
            
    if should_update:
        logger.info("Keine oder leere/ungültige bestehende Daten gefunden. Starte initialen Update-Zyklus...")
        threading.Thread(target=run_update_cycle).start()
