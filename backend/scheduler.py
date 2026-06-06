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
# pyrefly: ignore [missing-import]
from backend.db import get_all_assets, save_prediction, get_predictions_from_db, init_db

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
        
        # Assets aus der Datenbank laden (dynamische Watchlist)
        assets = get_all_assets()
        
        if not assets:
            logger.warning("Keine Assets in der Watchlist. Überspringe Aktualisierungszyklus.")
            return

        for asset in assets:
            symbol = asset["symbol"]
            try:
                # 1. Marktdaten abrufen
                market_data = fetch_market_data(symbol)
                if not market_data:
                    logger.error(f"Konnte Marktdaten für {symbol} nicht laden. Überspringe.")
                    continue
                    
                market_data["last_updated"] = timestamp
                
                # 2. Nachrichten abrufen
                news_items = fetch_news(symbol, asset["name"])
                
                # 3. KI-Prognose generieren
                prediction = analyze_asset_with_ai(asset, market_data, news_items)
                
                # Ergänze die Nachrichten und den Chartverlauf in dem gespeicherten Objekt
                prediction["news"] = news_items
                prediction["history"] = market_data["history"]
                prediction["last_updated"] = timestamp
                
                # 4. In Datenbank speichern (aktuelle Prognose + Historie)
                save_prediction(prediction)
                
                logger.info(f"Analyse für {symbol} erfolgreich abgeschlossen und in DB gespeichert.")
                
            except Exception as e:
                logger.error(f"Unerwarteter Fehler bei der Analyse von {symbol}: {e}")
                    
        # Kompatibilitäts-Fallback: JSON-Datei ebenfalls aktualisieren
        try:
            db_data = get_predictions_from_db()
            db_data["last_updated"] = timestamp
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(db_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Aktualisierungszyklus abgeschlossen. Daten in DB und {DATA_FILE} gespeichert.")
        except Exception as e:
            logger.error(f"Fehler beim Schreiben der JSON-Fallback-Datei: {e}")
    finally:
        is_updating = False


def analyze_single_asset_background(asset_info):
    """Führt eine sofortige Analyse für ein einzelnes Asset im Hintergrund aus."""
    symbol = asset_info["symbol"]
    name = asset_info["name"]
    logger.info(f"Starte sofortige Hintergrundanalyse für das neue Asset: {symbol}...")
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        # 1. Marktdaten abrufen
        market_data = fetch_market_data(symbol)
        if not market_data:
            logger.error(f"Konnte Marktdaten für das neue Asset {symbol} nicht laden.")
            return
            
        market_data["last_updated"] = timestamp
        
        # 2. Nachrichten abrufen
        news_items = fetch_news(symbol, name)
        
        # 3. KI-Prognose generieren
        prediction = analyze_asset_with_ai(asset_info, market_data, news_items)
        
        # Ergänze die Nachrichten und den Chartverlauf in dem gespeicherten Objekt
        prediction["news"] = news_items
        prediction["history"] = market_data["history"]
        prediction["last_updated"] = timestamp
        
        # 4. In Datenbank speichern (aktuelle Prognose + Historie)
        save_prediction(prediction)
        
        logger.info(f"Sofortige Analyse für {symbol} erfolgreich abgeschlossen und in DB gespeichert.")
        
        # Kompatibilitäts-Fallback: JSON-Datei ebenfalls aktualisieren
        try:
            db_data = get_predictions_from_db()
            db_data["last_updated"] = timestamp
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(db_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Fallback JSON-Datei aktualisiert nach Analyse von {symbol}.")
        except Exception as e:
            logger.error(f"Fehler beim Schreiben der JSON-Fallback-Datei: {e}")
            
    except Exception as e:
        logger.error(f"Unerwarteter Fehler bei der sofortigen Analyse von {symbol}: {e}")


def start_scheduler():
    """Initialisiert und startet den Hintergrund-Scheduler."""
    # Datenbank initialisieren
    init_db()
    
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_update_cycle, 
        'interval', 
        hours=UPDATE_INTERVAL_HOURS, 
        id='market_analysis_job'
    )
    scheduler.start()
    logger.info(f"Hintergrund-Scheduler gestartet (Intervall: {UPDATE_INTERVAL_HOURS} Stunden).")
    
    # Führe einen ersten Lauf asynchron aus, falls die DB noch keine Prognosen enthält
    db_data = get_predictions_from_db()
    should_update = not db_data["predictions"]
            
    if should_update:
        logger.info("Keine bestehenden Prognosen in der DB gefunden. Starte initialen Update-Zyklus...")
        threading.Thread(target=run_update_cycle).start()
