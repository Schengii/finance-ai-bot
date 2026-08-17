import json
import logging
import threading
import asyncio
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from backend.config import DEFAULT_ASSETS, UPDATE_INTERVAL_HOURS
from backend.data_fetcher import fetch_market_data, fetch_news
from backend.ai_analyzer import analyze_asset_with_ai
from backend.db import get_all_assets, save_prediction, get_predictions_from_db, init_db

logger = logging.getLogger(__name__)

# Status-Variable, um zu sehen, ob gerade eine Aktualisierung läuft
is_updating = False

async def _run_update_cycle_async():
    """Asynchroner Kern des Aktualisierungszyklus."""
    global is_updating
    if is_updating:
        logger.warning("Aktualisierungszyklus läuft bereits. Überspringe...")
        return
        
    is_updating = True
    logger.info("Starte Aktualisierungszyklus...")
    
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        # Assets aus der Datenbank laden (dynamische Watchlist)
        assets = await get_all_assets()
        
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
                prediction = await analyze_asset_with_ai(asset, market_data, news_items)
                
                # Ergänze die Nachrichten und den Chartverlauf in dem gespeicherten Objekt
                prediction["news"] = news_items
                prediction["history"] = market_data["history"]
                prediction["last_updated"] = timestamp
                
                # 4. In Datenbank speichern (aktuelle Prognose + Historie)
                await save_prediction(prediction)
                
                logger.info(f"Analyse für {symbol} erfolgreich abgeschlossen und in DB gespeichert.")
                
            except Exception as e:
                logger.error(f"Unerwarteter Fehler bei der Analyse von {symbol}: {e}")
                    
        # Alarme prüfen
        await _check_alerts_async()
        logger.info("Aktualisierungszyklus abgeschlossen. Daten in DB gespeichert.")
    finally:
        is_updating = False

def run_update_cycle():
    """Führt einen vollständigen Aktualisierungszyklus für alle Assets durch."""
    try:
        asyncio.run(_run_update_cycle_async())
    except Exception as e:
        logger.error(f"Fehler im run_update_cycle: {e}")

async def _check_alerts_async():
    """Prüft alle aktiven Alarme gegen die aktuellen Prognosedaten."""
    try:
        from backend.db import get_all_alerts, get_predictions_from_db, mark_alert_triggered
        alerts = await get_all_alerts()
        if not alerts:
            return
            
        predictions_data = (await get_predictions_from_db()).get("predictions", {})
        
        for alert in alerts:
            if alert["is_triggered"]:
                continue
                
            symbol = alert["symbol"]
            alert_type = alert["alert_type"]
            target_value = alert["target_value"]
            
            if symbol not in predictions_data:
                continue
                
            pred = predictions_data[symbol]
            current_price = pred.get("price")
            rsi = pred.get("rsi")
            rec = pred.get("recommendation")
            
            trigger = False
            try:
                if alert_type == "price_above" and current_price and current_price > float(target_value):
                    trigger = True
                elif alert_type == "price_below" and current_price and current_price < float(target_value):
                    trigger = True
                elif alert_type == "rsi_above" and rsi and rsi > float(target_value):
                    trigger = True
                elif alert_type == "rsi_below" and rsi and rsi < float(target_value):
                    trigger = True
                elif alert_type == "change_above" and pred.get("price_change_1d") is not None and pred.get("price_change_1d") > float(target_value):
                    trigger = True
                elif alert_type == "change_below" and pred.get("price_change_1d") is not None and pred.get("price_change_1d") < float(target_value):
                    trigger = True
                elif alert_type == "rec_change" and rec and rec.strip().lower() == str(target_value).strip().lower():
                    trigger = True
                elif alert_type == "multi_rsi_buy" and rsi and rsi < (float(target_value) if str(target_value).replace('.','',1).isdigit() else 35.0) and rec and "kauf" in rec.lower():
                    trigger = True
                elif alert_type == "multi_rsi_sell" and rsi and rsi > (float(target_value) if str(target_value).replace('.','',1).isdigit() else 70.0) and rec and "verkauf" in rec.lower():
                    trigger = True
            except Exception as e:
                logger.error(f"Fehler bei Alarm-Auswertung für {symbol}: {e}")
                
            if trigger:
                await mark_alert_triggered(alert["id"])
                logger.info(f"ALARM AUSGELÖST: {symbol} ({alert_type}) erreicht Zielwert {target_value}")
                
                try:
                    from backend.notifications import send_all_notifications
                    
                    type_labels = {
                        "price_above": "Preis übersteigt",
                        "price_below": "Preis fällt unter",
                        "rsi_above": "RSI übersteigt",
                        "rsi_below": "RSI fällt unter",
                        "change_above": "Tagesveränderung übersteigt %",
                        "change_below": "Tagesveränderung fällt unter %",
                        "rec_change": "KI-Empfehlung ändert sich auf",
                        "multi_rsi_buy": "Multi-Condition (RSI überverkauft + KI-Kauf)",
                        "multi_rsi_sell": "Multi-Condition (RSI überkauft + KI-Verkauf)"
                    }
                    label = type_labels.get(alert_type, alert_type)
                    
                    subj = f"🚨 AlphaPulse Alarm ausgelöst: {symbol}"
                    text_msg = (
                        f"🚨 Alarm ausgelöst!\n\n"
                        f"Asset: {symbol} ({pred.get('name', '')})\n"
                        f"Bedingung: {label} {target_value}\n\n"
                        f"Aktuelle Werte:\n"
                        f"- Preis: {current_price} $\n"
                        f"- 1D Veränderung: {pred.get('price_change_1d')}%\n"
                        f"- RSI: {rsi:.1f if rsi else 0.0}\n"
                        f"- Empfehlung: {rec}"
                    )
                    html_msg = (
                        f"<h3>🚨 Alarm ausgelöst!</h3>"
                        f"<p>Asset: <b>{symbol}</b> ({pred.get('name', '')})<br>"
                        f"Bedingung: {label} <b>{target_value}</b></p>"
                        f"<p><b>Aktuelle Werte:</b><br>"
                        f"• Preis: {current_price} $<br>"
                        f"• 1D Veränderung: {pred.get('price_change_1d')}%<br>"
                        f"• RSI: {rsi:.1f if rsi else 0.0}<br>"
                        f"• Empfehlung: <b>{rec}</b></p>"
                    )
                    await send_all_notifications(subj, html_msg, text_msg)
                except Exception as e_notif:
                    logger.error(f"Fehler beim Versenden der Alarm-Benachrichtigung: {e_notif}")
    except Exception as e:
        logger.error(f"Fehler in _check_alerts_async: {e}")

async def send_daily_digest_async():
    """Erzeugt und versendet den täglichen Markt- & Portfolio-Report."""
    try:
        from backend.db import get_portfolio_from_db, get_predictions_from_db, get_setting
        from backend.ai_analyzer import generate_daily_summary
        from backend.notifications import send_all_notifications
        
        enabled = await get_setting("daily_digest_enabled", "0")
        if enabled != "1":
            return
            
        portfolio = await get_portfolio_from_db(1)
        db_data = await get_predictions_from_db()
        predictions = db_data.get("predictions", {})
        
        digest = generate_daily_summary(portfolio, predictions, "Ausgewogen")
        
        subj = f"📈 AlphaPulse AI - Daily Digest ({datetime.now().strftime('%d.%m.%Y')})"
        text_msg = f"📊 Daily Market & Portfolio Report\n\n{digest['headline']}\n\n{digest['summary']}\n\nEmpfehlungen:\n"
        for rec in digest.get('recommendations', []):
            text_msg += f"- {rec}\n"
            
        html_msg = f"<h2>📈 AlphaPulse AI - Daily Digest</h2><h4>{digest['headline']}</h4><p>{digest['summary']}</p><h5>Empfehlungen:</h5><ul>"
        for rec in digest.get('recommendations', []):
            html_msg += f"<li>{rec}</li>"
        html_msg += "</ul>"
        
        await send_all_notifications(subj, html_msg, text_msg)
        logger.info("Daily Digest erfolgreich versendet.")
    except Exception as e:
        logger.error(f"Fehler beim Versenden des Daily Digest: {e}")

def check_alerts():
    """Wrapper für die synchrone Ausführung des Alarm-Checks."""
    try:
        asyncio.run(_check_alerts_async())
    except Exception as e:
        logger.error(f"Fehler im check_alerts Wrapper: {e}")

async def analyze_single_asset_background(asset_info):
    """Führe eine sofortige Analyse für ein einzelnes Asset im Hintergrund aus (FastAPI BackgroundTask)."""
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
        prediction = await analyze_asset_with_ai(asset_info, market_data, news_items)
        
        # Ergänze die Nachrichten und den Chartverlauf in dem gespeicherten Objekt
        prediction["news"] = news_items
        prediction["history"] = market_data["history"]
        prediction["last_updated"] = timestamp
        
        # 4. In Datenbank speichern (aktuelle Prognose + Historie)
        await save_prediction(prediction)
        
        # Alarme prüfen
        await _check_alerts_async()
        logger.info(f"Sofortige Analyse für {symbol} erfolgreich abgeschlossen und in DB gespeichert.")
    except Exception as e:
        logger.error(f"Unerwarteter Fehler bei der sofortigen Analyse von {symbol}: {e}")

def start_scheduler():
    """Initialisiert und startet den Hintergrund-Scheduler."""
    # Datenbank initialisieren
    asyncio.run(init_db())
    
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
    db_data = asyncio.run(get_predictions_from_db())
    should_update = not db_data["predictions"]
            
    if should_update:
        logger.info("Keine bestehenden Prognosen in der DB gefunden. Starte initialen Update-Zyklus...")
        threading.Thread(target=run_update_cycle).start()
