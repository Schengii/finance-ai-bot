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
                ai_explanation, key_drivers, key_risks, news, history, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pred["symbol"], pred["name"], pred["type"], pred["price"],
            pred["price_change_1d"], pred["price_change_7d"], pred["price_change_30d"],
            pred["rsi"], pred["technical_trend"], pred["recommendation"], pred["confidence"],
            pred["sentiment_score"], pred["risk_level"], pred["ai_explanation"],
            json.dumps(pred.get("key_drivers", [])),
            json.dumps(pred.get("key_risks", [])),
            json.dumps(pred.get("news", [])),
            json.dumps(pred.get("history", [])),
            pred["last_updated"]
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
            "last_updated": row["last_updated"]
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
