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
    
    # 4. Portfolios-Liste (Profile)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolios_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)
    
    # Standard-Portfolio einfügen falls leer
    cursor.execute("SELECT COUNT(*) FROM portfolios_list")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO portfolios_list (id, name) VALUES (1, 'Standard-Portfolio')")

    # 5. Portfolio-Tabelle (Bestände des Nutzers)
    # Check if 'portfolio' table has composite primary key / portfolio_id
    cursor.execute("PRAGMA table_info(portfolio)")
    cols = [col[1] for col in cursor.fetchall()]
    if not cols:
        # Tabelle existiert nicht, erstellen
        cursor.execute("""
            CREATE TABLE portfolio (
                portfolio_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                quantity REAL NOT NULL,
                buy_price REAL NOT NULL,
                PRIMARY KEY (portfolio_id, symbol),
                FOREIGN KEY (portfolio_id) REFERENCES portfolios_list (id) ON DELETE CASCADE,
                FOREIGN KEY (symbol) REFERENCES assets (symbol) ON DELETE CASCADE
            )
        """)
    elif "portfolio_id" not in cols:
        logger.info("Migriere Portfolio-Tabelle zur Unterstützung von Multi-Portfolios...")
        # 1. Benenne alte Tabelle um
        cursor.execute("ALTER TABLE portfolio RENAME TO portfolio_old")
        # 2. Erstelle neue Tabelle
        cursor.execute("""
            CREATE TABLE portfolio (
                portfolio_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                quantity REAL NOT NULL,
                buy_price REAL NOT NULL,
                PRIMARY KEY (portfolio_id, symbol),
                FOREIGN KEY (portfolio_id) REFERENCES portfolios_list (id) ON DELETE CASCADE,
                FOREIGN KEY (symbol) REFERENCES assets (symbol) ON DELETE CASCADE
            )
        """)
        # 3. Kopiere alte Daten mit portfolio_id = 1
        try:
            cursor.execute("INSERT INTO portfolio (portfolio_id, symbol, quantity, buy_price) SELECT 1, symbol, quantity, buy_price FROM portfolio_old")
        except Exception as e:
            logger.error(f"Fehler beim Kopieren der alten Portfoliodaten: {e}")
        # 4. Lösche alte Tabelle
        cursor.execute("DROP TABLE portfolio_old")
        
    # 6. Settings-Tabelle (Einstellungen für Prompts etc.)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    # Standard-Einstellungen einfügen
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('custom_prompt', '')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('ai_tone', 'professionell')")

    # 7. Transaktionen-Tabelle (für FIFO)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            portfolio_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            type TEXT NOT NULL, -- 'BUY' oder 'SELL'
            quantity REAL NOT NULL,
            price REAL NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (portfolio_id) REFERENCES portfolios_list (id) ON DELETE CASCADE,
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

def get_portfolio_from_db(portfolio_id: int = 1):
    """Holt das Portfolio des Nutzers für ein Profil."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT symbol, quantity, buy_price FROM portfolio WHERE portfolio_id = ?", (portfolio_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"symbol": row["symbol"], "quantity": row["quantity"], "buy_price": row["buy_price"]} for row in rows]

def save_portfolio_item(symbol, quantity, buy_price, portfolio_id: int = 1):
    """Speichert oder aktualisiert ein Portfolio-Asset."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO portfolio (portfolio_id, symbol, quantity, buy_price)
            VALUES (?, ?, ?, ?)
        """, (portfolio_id, symbol.upper(), quantity, buy_price))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Speichern des Portfolio-Assets {symbol} für Portfolio {portfolio_id}: {e}")
        return False
    finally:
        conn.close()

def delete_portfolio_item(symbol, portfolio_id: int = 1):
    """Löscht ein Asset aus dem Portfolio."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM portfolio WHERE symbol = ? AND portfolio_id = ?", (symbol, portfolio_id))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Portfolio-Assets {symbol} für Portfolio {portfolio_id}: {e}")
        return False
    finally:
        conn.close()
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

# --------------------------------------------------------------------------
# Hilfsfunktionen für Multi-Portfolio, Settings & FIFO Transaktionen
# --------------------------------------------------------------------------

def get_portfolios():
    """Holt alle Portfolio-Profile."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM portfolios_list ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": row["id"], "name": row["name"]} for row in rows]

def create_portfolio(name):
    """Erstellt ein neues Portfolio-Profil."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO portfolios_list (name) VALUES (?)", (name,))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Portfolios {name}: {e}")
        return False
    finally:
        conn.close()

def delete_portfolio(portfolio_id):
    """Löscht ein Portfolio-Profil (und kaskadiert alle Bestände/Transaktionen)."""
    if portfolio_id == 1:
        return False # Standard-Portfolio darf nicht gelöscht werden
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM portfolios_list WHERE id = ?", (portfolio_id,))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Portfolios {portfolio_id}: {e}")
        return False
    finally:
        conn.close()

def get_setting(key, default=""):
    """Liest eine Einstellung aus."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default

def save_setting(key, value):
    """Speichert eine Einstellung."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Einstellung {key}: {e}")
        return False
    finally:
        conn.close()

def get_transactions(portfolio_id):
    """Holt den Transaktionsverlauf eines Portfolios."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.id, t.symbol, t.type, t.quantity, t.price, t.date, a.name
        FROM transactions t
        JOIN assets a ON t.symbol = a.symbol
        WHERE t.portfolio_id = ?
        ORDER BY t.date DESC, t.id DESC
    """, (portfolio_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{
        "id": row["id"],
        "symbol": row["symbol"],
        "name": row["name"],
        "type": row["type"],
        "quantity": row["quantity"],
        "price": row["price"],
        "date": row["date"]
    } for row in rows]

def add_transaction(portfolio_id, symbol, tx_type, quantity, price, date):
    """Fügt eine Transaktion hinzu und aktualisiert den Gesamtbestand im Portfolio."""
    conn = get_db_connection()
    cursor = conn.cursor()
    symbol = symbol.upper()
    try:
        # Transaktion einfügen
        cursor.execute("""
            INSERT INTO transactions (portfolio_id, symbol, type, quantity, price, date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (portfolio_id, symbol, tx_type.upper(), quantity, price, date))
        
        # Neuen Gesamtbestand für dieses Asset berechnen
        cursor.execute("""
            SELECT type, quantity, price FROM transactions 
            WHERE portfolio_id = ? AND symbol = ?
        """, (portfolio_id, symbol))
        rows = cursor.fetchall()
        
        total_qty = 0.0
        total_cost = 0.0
        
        for row in rows:
            qty = row["quantity"]
            p = row["price"]
            if row["type"] == "BUY":
                total_qty += qty
                total_cost += qty * p
            elif row["type"] == "SELL":
                if total_qty > 0:
                    avg_price = total_cost / total_qty
                    total_qty = max(0.0, total_qty - qty)
                    total_cost = total_qty * avg_price
                else:
                    total_qty = 0.0
                    total_cost = 0.0
                    
        avg_buy_price = (total_cost / total_qty) if total_qty > 0 else 0.0
        
        if total_qty > 0:
            cursor.execute("""
                INSERT OR REPLACE INTO portfolio (portfolio_id, symbol, quantity, buy_price)
                VALUES (?, ?, ?, ?)
            """, (portfolio_id, symbol, total_qty, round(avg_buy_price, 4)))
        else:
            cursor.execute("""
                DELETE FROM portfolio WHERE portfolio_id = ? AND symbol = ?
            """, (portfolio_id, symbol))
            
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen der Transaktion: {e}")
        return False
    finally:
        conn.close()

def delete_transaction(tx_id, portfolio_id):
    """Löscht eine Transaktion und berechnet den Bestand neu."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT symbol FROM transactions WHERE id = ?", (tx_id,))
        row = cursor.fetchone()
        if not row:
            return False
        symbol = row["symbol"]
        
        cursor.execute("DELETE FROM transactions WHERE id = ? AND portfolio_id = ?", (tx_id, portfolio_id))
        
        cursor.execute("""
            SELECT type, quantity, price FROM transactions 
            WHERE portfolio_id = ? AND symbol = ?
        """, (portfolio_id, symbol))
        rows = cursor.fetchall()
        
        total_qty = 0.0
        total_cost = 0.0
        
        for row in rows:
            qty = row["quantity"]
            p = row["price"]
            if row["type"] == "BUY":
                total_qty += qty
                total_cost += qty * p
            elif row["type"] == "SELL":
                if total_qty > 0:
                    avg_price = total_cost / total_qty
                    total_qty = max(0.0, total_qty - qty)
                    total_cost = total_qty * avg_price
                else:
                    total_qty = 0.0
                    total_cost = 0.0
                    
        avg_buy_price = (total_cost / total_qty) if total_qty > 0 else 0.0
        
        if total_qty > 0:
            cursor.execute("""
                INSERT OR REPLACE INTO portfolio (portfolio_id, symbol, quantity, buy_price)
                VALUES (?, ?, ?, ?)
            """, (portfolio_id, symbol, total_qty, round(avg_buy_price, 4)))
        else:
            cursor.execute("""
                DELETE FROM portfolio WHERE portfolio_id = ? AND symbol = ?
            """, (portfolio_id, symbol))
            
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Löschen der Transaktion: {e}")
        return False
    finally:
        conn.close()

def calculate_fifo_tax(portfolio_id, symbol, sell_qty, sell_price):
    """
    Berechnet den Gewinn/Verlust nach FIFO und schätzt die Kapitalertragsteuer (26,375%).
    Gibt Details zu den gematchten Käufen zurück.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    symbol = symbol.upper()
    
    cursor.execute("""
        SELECT type, quantity, price, date FROM transactions 
        WHERE portfolio_id = ? AND symbol = ?
        ORDER BY date ASC, id ASC
    """, (portfolio_id, symbol))
    rows = cursor.fetchall()
    conn.close()
    
    buy_queue = []
    
    for row in rows:
        qty = row["quantity"]
        p = row["price"]
        t_type = row["type"]
        
        if t_type == "BUY":
            buy_queue.append({"qty": qty, "price": p, "date": row["date"]})
        elif t_type == "SELL":
            to_remove = qty
            while to_remove > 0 and buy_queue:
                first = buy_queue[0]
                if first["qty"] <= to_remove:
                    to_remove -= first["qty"]
                    buy_queue.pop(0)
                else:
                    first["qty"] -= to_remove
                    to_remove = 0
                    
    matched_buys = []
    total_cost = 0.0
    remaining_to_sell = sell_qty
    
    temp_queue = [dict(b) for b in buy_queue]
    
    while remaining_to_sell > 0 and temp_queue:
        first = temp_queue[0]
        match_qty = min(remaining_to_sell, first["qty"])
        
        matched_buys.append({
            "buy_date": first["date"],
            "buy_price": first["price"],
            "quantity": match_qty,
            "cost": round(match_qty * first["price"], 2)
        })
        
        total_cost += match_qty * first["price"]
        remaining_to_sell -= match_qty
        
        first["qty"] -= match_qty
        if first["qty"] <= 0:
            temp_queue.pop(0)
            
    revenue = sell_qty * sell_price
    profit = revenue - total_cost
    tax = max(0.0, profit * 0.26375)
    
    return {
        "symbol": symbol,
        "sell_quantity": sell_qty,
        "sell_price": sell_price,
        "revenue": round(revenue, 2),
        "total_cost": round(total_cost, 2),
        "profit": round(profit, 2),
        "tax": round(tax, 2),
        "matched_buys": matched_buys,
        "unmatched_quantity": remaining_to_sell
    }


