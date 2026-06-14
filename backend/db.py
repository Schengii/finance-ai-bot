import sqlite3
import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent / "data" / "finance_bot.db"
DB_PATH.parent.mkdir(exist_ok=True)

def get_db_connection():
    """Gibt eine Verbindung zur SQLite-Datenbank zurück."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialisiert die Datenbank-Tabellen, falls sie nicht existieren."""
    logger.info("Initialisiere SQLite-Datenbank...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Assets-Tabelle (Watchlist)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assets (
            symbol TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL
        )
    """)
    
    # 2. Predictions-Tabelle (Aktuelle Analysen)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            symbol TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            price REAL,
            price_change_1d REAL,
            price_change_7d REAL,
            price_change_30d REAL,
            rsi REAL,
            technical_trend TEXT,
            recommendation TEXT,
            confidence INTEGER,
            sentiment_score REAL,
            risk_level TEXT,
            ai_explanation TEXT,
            key_drivers TEXT,
            key_risks TEXT,
            news TEXT,
            history TEXT,
            last_updated TEXT,
            FOREIGN KEY (symbol) REFERENCES assets (symbol) ON DELETE CASCADE
        )
    """)
    
    # 3. Prediction History (Historische Analysen für Backtesting)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prediction_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            price REAL,
            recommendation TEXT,
            confidence INTEGER,
            last_updated TEXT,
            FOREIGN KEY (symbol) REFERENCES assets (symbol) ON DELETE CASCADE
        )
    """)
    
    # 4. Portfolio-Tabelle (Bestände des Nutzers)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            symbol TEXT PRIMARY KEY,
            quantity REAL NOT NULL,
            buy_price REAL NOT NULL,
            FOREIGN KEY (symbol) REFERENCES assets (symbol) ON DELETE CASCADE
        )
    """)
    
    # 5. Alerts-Tabelle (Alarme des Nutzers)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            target_value REAL,
            is_triggered INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (symbol) REFERENCES assets (symbol) ON DELETE CASCADE
        )
    """)
    
    # Migrations: Add dividend columns to predictions table if they do not exist
    try:
        cursor.execute("ALTER TABLE predictions ADD COLUMN dividend_yield REAL")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE predictions ADD COLUMN dividend_rate REAL")
    except sqlite3.OperationalError:
        pass
        
    # Standard-Assets einfügen, falls die assets-Tabelle leer ist
    cursor.execute("SELECT COUNT(*) FROM assets")
    if cursor.fetchone()[0] == 0:
        logger.info("Füge Standard-Assets in die Datenbank ein...")
        from backend.config import DEFAULT_ASSETS
        for asset in DEFAULT_ASSETS:
            cursor.execute(
                "INSERT INTO assets (symbol, name, type) VALUES (?, ?, ?)",
                (asset["symbol"], asset["name"], asset["type"])
            )
            
    conn.commit()
    conn.close()
    logger.info("Datenbank erfolgreich initialisiert.")

# Hilfsfunktionen für DB-Zugriffe

def get_all_assets():
    """Holt alle überwachten Assets."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT symbol, name, type FROM assets")
    rows = cursor.fetchall()
    conn.close()
    return [{"symbol": row["symbol"], "name": row["name"], "type": row["type"]} for row in rows]

def asset_exists(symbol):
    """Prüft, ob ein Asset in der Watchlist existiert."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM assets WHERE symbol = ?", (symbol,))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def add_asset(symbol, name, asset_type):
    """Fügt ein neues Asset hinzu."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT OR REPLACE INTO assets (symbol, name, type) VALUES (?, ?, ?)",
            (symbol, name, asset_type)
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen des Assets {symbol}: {e}")
        return False
    finally:
        conn.close()

def delete_asset(symbol):
    """Entfernt ein Asset aus der Watchlist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM assets WHERE symbol = ?", (symbol,))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Assets {symbol}: {e}")
        return False
    finally:
        conn.close()

def save_prediction(pred):
    """Speichert eine aktuelle Prognose in predictions und archiviert in prediction_history."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # In Haupt-Predictions-Tabelle speichern
        cursor.execute("""
            INSERT OR REPLACE INTO predictions (
                symbol, name, type, price, price_change_1d, price_change_7d, price_change_30d,
                rsi, technical_trend, recommendation, confidence, sentiment_score, risk_level,
                ai_explanation, key_drivers, key_risks, news, history, last_updated,
                dividend_yield, dividend_rate
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pred["symbol"], pred["name"], pred["type"], pred["price"],
            pred["price_change_1d"], pred["price_change_7d"], pred["price_change_30d"],
            pred["rsi"], pred["technical_trend"], pred["recommendation"], pred["confidence"],
            pred["sentiment_score"], pred["risk_level"], pred["ai_explanation"],
            json.dumps(pred.get("key_drivers", [])),
            json.dumps(pred.get("key_risks", [])),
            json.dumps(pred.get("news", [])),
            json.dumps(pred.get("history", [])),
            pred["last_updated"],
            pred.get("dividend_yield", 0.0),
            pred.get("dividend_rate", 0.0)
        ))
        
        # In History-Tabelle archivieren (für Backtesting)
        cursor.execute("""
            INSERT INTO prediction_history (symbol, price, recommendation, confidence, last_updated)
            VALUES (?, ?, ?, ?, ?)
        """, (
            pred["symbol"], pred["price"], pred["recommendation"],
            pred["confidence"], pred["last_updated"]
        ))
        
        conn.commit()
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Prognose für {pred['symbol']}: {e}")
    finally:
        conn.close()

def get_predictions_from_db():
    """Holt alle aktuellen Prognosen."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM predictions")
    rows = cursor.fetchall()
    
    predictions = {}
    last_updated = "Nie"
    
    for row in rows:
        last_updated = row["last_updated"]
        
        # Check if dividend columns exist in query result (safeguard)
        dividend_yield = 0.0
        dividend_rate = 0.0
        try:
            dividend_yield = row["dividend_yield"]
            dividend_rate = row["dividend_rate"]
        except Exception:
            pass
            
        predictions[row["symbol"]] = {
            "symbol": row["symbol"],
            "name": row["name"],
            "type": row["type"],
            "price": row["price"],
            "price_change_1d": row["price_change_1d"],
            "price_change_7d": row["price_change_7d"],
            "price_change_30d": row["price_change_30d"],
            "rsi": row["rsi"],
            "technical_trend": row["technical_trend"],
            "recommendation": row["recommendation"],
            "confidence": row["confidence"],
            "sentiment_score": row["sentiment_score"],
            "risk_level": row["risk_level"],
            "ai_explanation": row["ai_explanation"],
            "key_drivers": json.loads(row["key_drivers"] or "[]"),
            "key_risks": json.loads(row["key_risks"] or "[]"),
            "news": json.loads(row["news"] or "[]"),
            "history": json.loads(row["history"] or "[]"),
            "last_updated": row["last_updated"],
            "dividend_yield": dividend_yield,
            "dividend_rate": dividend_rate
        }
        
    conn.close()
    return {"last_updated": last_updated, "predictions": predictions}

def get_portfolio_from_db():
    """Holt das Portfolio des Nutzers."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT symbol, quantity, buy_price FROM portfolio")
    rows = cursor.fetchall()
    conn.close()
    return [{"symbol": row["symbol"], "quantity": row["quantity"], "buy_price": row["buy_price"]} for row in rows]

def save_portfolio_item(symbol, quantity, buy_price):
    """Speichert oder aktualisiert ein Portfolio-Asset."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO portfolio (symbol, quantity, buy_price)
            VALUES (?, ?, ?)
        """, (symbol, quantity, buy_price))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Speichern des Portfolio-Assets {symbol}: {e}")
        return False
    finally:
        conn.close()

def delete_portfolio_item(symbol):
    """Löscht ein Asset aus dem Portfolio."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM portfolio WHERE symbol = ?", (symbol,))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Portfolio-Assets {symbol}: {e}")
        return False
    finally:
        conn.close()

# Alarme CRUD Hilfsfunktionen

def get_all_alerts():
    """Holt alle eingerichteten Alarme."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, symbol, alert_type, target_value, is_triggered, created_at FROM alerts ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [{
        "id": row["id"],
        "symbol": row["symbol"],
        "alert_type": row["alert_type"],
        "target_value": row["target_value"],
        "is_triggered": row["is_triggered"],
        "created_at": row["created_at"]
    } for row in rows]

def add_alert(symbol, alert_type, target_value):
    """Erstellt einen neuen Alarm."""
    import datetime
    conn = get_db_connection()
    cursor = conn.cursor()
    created_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        cursor.execute("""
            INSERT INTO alerts (symbol, alert_type, target_value, is_triggered, created_at)
            VALUES (?, ?, ?, 0, ?)
        """, (symbol.upper(), alert_type, target_value, created_at))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen des Alarms für {symbol}: {e}")
        return False
    finally:
        conn.close()

def delete_alert(alert_id):
    """Löscht einen Alarm."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Alarms {alert_id}: {e}")
        return False
    finally:
        conn.close()

def get_triggered_alerts():
    """Holt alle ausgelösten Alarme und setzt sie wieder zurück (bzw. markiert sie)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, symbol, alert_type, target_value, created_at FROM alerts WHERE is_triggered = 1")
    rows = cursor.fetchall()
    
    triggered = []
    for row in rows:
        triggered.append({
            "id": row["id"],
            "symbol": row["symbol"],
            "alert_type": row["alert_type"],
            "target_value": row["target_value"],
            "created_at": row["created_at"]
        })
        
    if triggered:
        # Löschen oder als gelesen markieren. Löschen wir sie, damit sie nur einmal gemeldet werden
        ids = [row["id"] for row in rows]
        placeholders = ",".join("?" for _ in ids)
        cursor.execute(f"DELETE FROM alerts WHERE id IN ({placeholders})", ids)
        conn.commit()
        
    conn.close()
    return triggered

def mark_alert_triggered(alert_id):
    """Markiert einen Alarm als ausgelöst."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE alerts SET is_triggered = 1 WHERE id = ?", (alert_id,))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Markieren des Alarms {alert_id} als ausgelöst: {e}")
        return False
    finally:
        conn.close()

