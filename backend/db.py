import aiosqlite
import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent / "data" / "finance_bot.db"
DB_PATH.parent.mkdir(exist_ok=True)

async def get_db_connection():
    """Gibt eine Verbindung zur SQLite-Datenbank zurück."""
    conn = await aiosqlite.connect(str(DB_PATH))
    await conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = aiosqlite.Row
    return conn

async def init_db():
    """Initialisiert die Datenbank-Tabellen, falls sie nicht existieren."""
    logger.info("Initialisiere SQLite-Datenbank...")
    conn = await get_db_connection()
    try:
        cursor = await conn.cursor()
        
        # 1. Assets-Tabelle (Watchlist)
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS assets (
                symbol TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL
            )
        """)
        
        # 2. Predictions-Tabelle (Aktuelle Analysen)
        await cursor.execute("""
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
        await cursor.execute("""
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
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolios_list (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)
        
        # Standard-Portfolio einfügen falls leer
        await cursor.execute("SELECT COUNT(*) FROM portfolios_list")
        row = await cursor.fetchone()
        if row and row[0] == 0:
            await cursor.execute("INSERT INTO portfolios_list (id, name) VALUES (1, 'Standard-Portfolio')")

        # 5. Portfolio-Tabelle (Bestände des Nutzers)
        await cursor.execute("PRAGMA table_info(portfolio)")
        cols_rows = await cursor.fetchall()
        cols = [col[1] for col in cols_rows]
        if not cols:
            # Tabelle existiert nicht, erstellen
            await cursor.execute("""
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
            await cursor.execute("ALTER TABLE portfolio RENAME TO portfolio_old")
            # 2. Erstelle neue Tabelle
            await cursor.execute("""
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
                await cursor.execute("INSERT INTO portfolio (portfolio_id, symbol, quantity, buy_price) SELECT 1, symbol, quantity, buy_price FROM portfolio_old")
            except Exception as e:
                logger.error(f"Fehler beim Kopieren der alten Portfoliodaten: {e}")
            # 4. Lösche alte Tabelle
            await cursor.execute("DROP TABLE portfolio_old")
            
        # 6. Settings-Tabelle (Einstellungen für Prompts etc.)
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        # Standard-Einstellungen einfügen
        await cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('custom_prompt', '')")
        await cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('ai_tone', 'professionell')")
        
        # Benachrichtigungskanäle Standard-Einstellungen einfügen
        await cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('telegram_bot_token', '')")
        await cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('telegram_chat_id', '')")
        await cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('discord_webhook_url', '')")
        await cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('email_smtp_server', '')")
        await cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('email_smtp_port', '')")
        await cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('email_sender', '')")
        await cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('email_password', '')")
        await cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('email_recipient', '')")

        # 7. Transaktionen-Tabelle (für FIFO)
        await cursor.execute("""
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

        # 8. Chat-Verlauf Tabelle
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id INTEGER NOT NULL,
                sender TEXT NOT NULL, -- 'user' oder 'bot'
                message TEXT NOT NULL,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (portfolio_id) REFERENCES portfolios_list (id) ON DELETE CASCADE
            )
        """)

        # 9. Alerts-Tabelle (Alarme des Nutzers)
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                target_value REAL,
                is_triggered INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (symbol) REFERENCES assets (symbol) ON DELETE CASCADE
            );

            -- Users table for JWT auth
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'viewer'
            );

            -- Table for storing push subscription endpoints per user
            CREATE TABLE IF NOT EXISTS user_devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                endpoint TEXT NOT NULL,
                p256dh TEXT NOT NULL,
                auth TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # Migrations: Add dividend columns to predictions table if they do not exist
        try:
            await cursor.execute("ALTER TABLE predictions ADD COLUMN dividend_yield REAL")
        except aiosqlite.OperationalError:
            pass
        try:
            await cursor.execute("ALTER TABLE predictions ADD COLUMN dividend_rate REAL")
        except aiosqlite.OperationalError:
            pass
            
        # Standard-Assets einfügen, falls die assets-Tabelle leer ist
        await cursor.execute("SELECT COUNT(*) FROM assets")
        row = await cursor.fetchone()
        if row and row[0] == 0:
            logger.info("Füge Standard-Assets in die Datenbank ein...")
            from backend.config import DEFAULT_ASSETS
            for asset in DEFAULT_ASSETS:
                await cursor.execute(
                    "INSERT INTO assets (symbol, name, type) VALUES (?, ?, ?)",
                    (asset["symbol"], asset["name"], asset["type"])
                )
                
        await conn.commit()
    finally:
        await conn.close()
    logger.info("Datenbank erfolgreich initialisiert.")

async def get_all_assets():
    """Holt alle überwachten Assets."""
    conn = await get_db_connection()
    try:
        async with conn.execute("SELECT symbol, name, type FROM assets") as cursor:
            rows = await cursor.fetchall()
            return [{"symbol": row["symbol"], "name": row["name"], "type": row["type"]} for row in rows]
    finally:
        await conn.close()

async def asset_exists(symbol):
    """Prüft, ob ein Asset in der Watchlist existiert."""
    conn = await get_db_connection()
    try:
        async with conn.execute("SELECT 1 FROM assets WHERE symbol = ?", (symbol,)) as cursor:
            row = await cursor.fetchone()
            return row is not None
    finally:
        await conn.close()

async def add_asset(symbol, name, asset_type):
    """Fügt ein neues Asset hinzu."""
    conn = await get_db_connection()
    try:
        await conn.execute(
            "INSERT OR REPLACE INTO assets (symbol, name, type) VALUES (?, ?, ?)",
            (symbol, name, asset_type)
        )
        await conn.commit()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen des Assets {symbol}: {e}")
        return False
    finally:
        await conn.close()

async def delete_asset(symbol):
    """Entfernt ein Asset aus der Watchlist."""
    conn = await get_db_connection()
    try:
        await conn.execute("DELETE FROM assets WHERE symbol = ?", (symbol,))
        await conn.commit()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Assets {symbol}: {e}")
        return False
    finally:
        await conn.close()

async def save_prediction(pred):
    """Speichert eine aktuelle Prognose in predictions und archiviert in prediction_history."""
    conn = await get_db_connection()
    try:
        # In Haupt-Predictions-Tabelle speichern
        await conn.execute("""
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
        await conn.execute("""
            INSERT INTO prediction_history (symbol, price, recommendation, confidence, last_updated)
            VALUES (?, ?, ?, ?, ?)
        """, (
            pred["symbol"], pred["price"], pred["recommendation"],
            pred["confidence"], pred["last_updated"]
        ))
        
        await conn.commit()
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Prognose für {pred['symbol']}: {e}")
    finally:
        await conn.close()

async def get_predictions_from_db():
    """Holt alle aktuellen Prognosen."""
    conn = await get_db_connection()
    try:
        async with conn.execute("SELECT * FROM predictions") as cursor:
            rows = await cursor.fetchall()
            
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
                
            return {"last_updated": last_updated, "predictions": predictions}
    finally:
        await conn.close()

async def get_portfolio_from_db(portfolio_id: int = 1):
    """Holt das Portfolio des Nutzers für ein Profil."""
    conn = await get_db_connection()
    try:
        async with conn.execute("SELECT symbol, quantity, buy_price FROM portfolio WHERE portfolio_id = ?", (portfolio_id,)) as cursor:
            rows = await cursor.fetchall()
            return [{"symbol": row["symbol"], "quantity": row["quantity"], "buy_price": row["buy_price"]} for row in rows]
    finally:
        await conn.close()

async def save_portfolio_item(symbol, quantity, buy_price, portfolio_id: int = 1):
    """Speichert oder aktualisiert ein Portfolio-Asset."""
    conn = await get_db_connection()
    try:
        await conn.execute("""
            INSERT OR REPLACE INTO portfolio (portfolio_id, symbol, quantity, buy_price)
            VALUES (?, ?, ?, ?)
        """, (portfolio_id, symbol.upper(), quantity, buy_price))
        await conn.commit()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Speichern des Portfolio-Assets {symbol} für Portfolio {portfolio_id}: {e}")
        return False
    finally:
        await conn.close()

async def delete_portfolio_item(symbol, portfolio_id: int = 1):
    """Löscht ein Asset aus dem Portfolio."""
    conn = await get_db_connection()
    try:
        await conn.execute("DELETE FROM portfolio WHERE symbol = ? AND portfolio_id = ?", (symbol, portfolio_id))
        await conn.commit()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Portfolio-Assets {symbol} für Portfolio {portfolio_id}: {e}")
        return False
    finally:
        await conn.close()

async def get_all_alerts():
    """Holt alle eingerichteten Alarme."""
    conn = await get_db_connection()
    try:
        async with conn.execute("SELECT id, symbol, alert_type, target_value, is_triggered, created_at FROM alerts ORDER BY created_at DESC") as cursor:
            rows = await cursor.fetchall()
            return [{
                "id": row["id"],
                "symbol": row["symbol"],
                "alert_type": row["alert_type"],
                "target_value": row["target_value"],
                "is_triggered": row["is_triggered"],
                "created_at": row["created_at"]
            } for row in rows]
    finally:
        await conn.close()

async def add_alert(symbol, alert_type, target_value):
    """Erstellt einen neuen Alarm."""
    import datetime
    conn = await get_db_connection()
    created_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        await conn.execute("""
            INSERT INTO alerts (symbol, alert_type, target_value, is_triggered, created_at)
            VALUES (?, ?, ?, 0, ?)
        """, (symbol.upper(), alert_type, target_value, created_at))
        await conn.commit()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen des Alarms für {symbol}: {e}")
        return False
    finally:
        await conn.close()

async def delete_alert(alert_id):
    """Löscht einen Alarm."""
    conn = await get_db_connection()
    try:
        await conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
        await conn.commit()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Alarms {alert_id}: {e}")
        return False
    finally:
        await conn.close()

async def get_triggered_alerts():
    """Holt alle ausgelösten Alarme und setzt sie wieder zurück (bzw. markiert sie)."""
    conn = await get_db_connection()
    try:
        async with conn.execute("SELECT id, symbol, alert_type, target_value, created_at FROM alerts WHERE is_triggered = 1") as cursor:
            rows = await cursor.fetchall()
            
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
                await conn.execute(f"DELETE FROM alerts WHERE id IN ({placeholders})", ids)
                await conn.commit()
                
            return triggered
    finally:
        await conn.close()

async def mark_alert_triggered(alert_id):
    """Markiert einen Alarm als ausgelöst."""
    conn = await get_db_connection()
    try:
        await conn.execute("UPDATE alerts SET is_triggered = 1 WHERE id = ?", (alert_id,))
        await conn.commit()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Markieren des Alarms {alert_id} als ausgelöst: {e}")
        return False
    finally:
        await conn.close()

async def get_portfolios():
    """Holt alle Portfolio-Profile."""
    conn = await get_db_connection()
    try:
        async with conn.execute("SELECT id, name FROM portfolios_list ORDER BY id ASC") as cursor:
            rows = await cursor.fetchall()
            return [{"id": row["id"], "name": row["name"]} for row in rows]
    finally:
        await conn.close()

async def create_portfolio(name):
    """Erstellt ein neues Portfolio-Profil."""
    conn = await get_db_connection()
    try:
        await conn.execute("INSERT INTO portfolios_list (name) VALUES (?)", (name,))
        await conn.commit()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Portfolios {name}: {e}")
        return False
    finally:
        await conn.close()

async def delete_portfolio(portfolio_id):
    """Löscht ein Portfolio-Profil (und kaskadiert alle Bestände/Transaktionen)."""
    if portfolio_id == 1:
        return False # Standard-Portfolio darf nicht gelöscht werden
    conn = await get_db_connection()
    try:
        await conn.execute("DELETE FROM portfolios_list WHERE id = ?", (portfolio_id,))
        await conn.commit()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Portfolios {portfolio_id}: {e}")
        return False
    finally:
        await conn.close()

async def get_setting(key, default=""):
    """Liest eine Einstellung aus."""
    conn = await get_db_connection()
    try:
        async with conn.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else default
    finally:
        await conn.close()

async def save_setting(key, value):
    """Speichert eine Einstellung."""
    conn = await get_db_connection()
    try:
        await conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        await conn.commit()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Einstellung {key}: {e}")
        return False
    finally:
        await conn.close()

async def get_transactions(portfolio_id):
    """Holt den Transaktionsverlauf eines Portfolios."""
    conn = await get_db_connection()
    try:
        async with conn.execute("""
            SELECT t.id, t.symbol, t.type, t.quantity, t.price, t.date, a.name
            FROM transactions t
            JOIN assets a ON t.symbol = a.symbol
            WHERE t.portfolio_id = ?
            ORDER BY t.date DESC, t.id DESC
        """, (portfolio_id,)) as cursor:
            rows = await cursor.fetchall()
            return [{
                "id": row["id"],
                "symbol": row["symbol"],
                "name": row["name"],
                "type": row["type"],
                "quantity": row["quantity"],
                "price": row["price"],
                "date": row["date"]
            } for row in rows]
    finally:
        await conn.close()

async def add_transaction(portfolio_id, symbol, tx_type, quantity, price, date):
    """Fügt eine Transaktion hinzu und aktualisiert den Gesamtbestand im Portfolio."""
    conn = await get_db_connection()
    symbol = symbol.upper()
    try:
        # Transaktion einfügen
        await conn.execute("""
            INSERT INTO transactions (portfolio_id, symbol, type, quantity, price, date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (portfolio_id, symbol, tx_type.upper(), quantity, price, date))
        
        # Neuen Gesamtbestand für dieses Asset berechnen
        async with conn.execute("""
            SELECT type, quantity, price FROM transactions 
            WHERE portfolio_id = ? AND symbol = ?
        """, (portfolio_id, symbol)) as cursor:
            rows = await cursor.fetchall()
        
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
            await conn.execute("""
                INSERT OR REPLACE INTO portfolio (portfolio_id, symbol, quantity, buy_price)
                VALUES (?, ?, ?, ?)
            """, (portfolio_id, symbol, total_qty, round(avg_buy_price, 4)))
        else:
            await conn.execute("""
                DELETE FROM portfolio WHERE portfolio_id = ? AND symbol = ?
            """, (portfolio_id, symbol))
            
        await conn.commit()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen der Transaktion: {e}")
        return False
    finally:
        await conn.close()

async def delete_transaction(tx_id, portfolio_id):
    """Löscht eine Transaktion und berechnet den Bestand neu."""
    conn = await get_db_connection()
    try:
        async with conn.execute("SELECT symbol FROM transactions WHERE id = ?", (tx_id,)) as cursor:
            row = await cursor.fetchone()
        if not row:
            return False
        symbol = row["symbol"]
        
        await conn.execute("DELETE FROM transactions WHERE id = ? AND portfolio_id = ?", (tx_id, portfolio_id))
        
        async with conn.execute("""
            SELECT type, quantity, price FROM transactions 
            WHERE portfolio_id = ? AND symbol = ?
        """, (portfolio_id, symbol)) as cursor:
            rows = await cursor.fetchall()
        
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
            await conn.execute("""
                INSERT OR REPLACE INTO portfolio (portfolio_id, symbol, quantity, buy_price)
                VALUES (?, ?, ?, ?)
            """, (portfolio_id, symbol, total_qty, round(avg_buy_price, 4)))
        else:
            await conn.execute("""
                DELETE FROM portfolio WHERE portfolio_id = ? AND symbol = ?
            """, (portfolio_id, symbol))
            
        await conn.commit()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Löschen der Transaktion: {e}")
        return False
    finally:
        await conn.close()

async def calculate_fifo_tax(portfolio_id, symbol, sell_qty, sell_price):
    """
    Berechnet den Gewinn/Verlust nach FIFO und schätzt die Kapitalertragsteuer (26,375%).
    Gibt Details zu den gematchten Käufen zurück.
    """
    conn = await get_db_connection()
    symbol = symbol.upper()
    try:
        async with conn.execute("""
            SELECT type, quantity, price, date FROM transactions 
            WHERE portfolio_id = ? AND symbol = ?
            ORDER BY date ASC, id ASC
        """, (portfolio_id, symbol)) as cursor:
            rows = await cursor.fetchall()
    finally:
        await conn.close()
    
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

async def get_chat_history(portfolio_id: int):
    """Holt den Chatverlauf für ein bestimmtes Portfolio-Profil."""
    conn = await get_db_connection()
    try:
        async with conn.execute("""
            SELECT sender, message, timestamp 
            FROM chat_history 
            WHERE portfolio_id = ? 
            ORDER BY id ASC
        """, (portfolio_id,)) as cursor:
            rows = await cursor.fetchall()
            return [{"sender": row["sender"], "message": row["message"], "timestamp": row["timestamp"]} for row in rows]
    finally:
        await conn.close()

async def add_chat_message(portfolio_id: int, sender: str, message: str):
    """Fügt eine Chatnachricht zum Verlauf hinzu."""
    import datetime
    conn = await get_db_connection()
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        await conn.execute("""
            INSERT INTO chat_history (portfolio_id, sender, message, timestamp) 
            VALUES (?, ?, ?, ?)
        """, (portfolio_id, sender, message, timestamp))
        await conn.commit()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Chat-Nachricht: {e}")
        return False
    finally:
        await conn.close()

async def clear_chat_history(portfolio_id: int):
    """Löscht den Chatverlauf für ein bestimmtes Portfolio-Profil."""
    conn = await get_db_connection()
    try:
        await conn.execute("DELETE FROM chat_history WHERE portfolio_id = ?", (portfolio_id,))
        await conn.commit()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Chatverlaufs für Portfolio {portfolio_id}: {e}")
        return False
    finally:
        await conn.close()

async def get_target_allocation(portfolio_id: int):
    """Liest die Ziel-Allokation für ein Portfolio aus den Einstellungen."""
    key = f"portfolio_target_allocation_{portfolio_id}"
    conn = await get_db_connection()
    try:
        async with conn.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0]:
                return json.loads(row[0])
            # Standardwert, falls nicht gesetzt
            return {"stock": 50.0, "crypto": 30.0, "commodity": 20.0}
    except Exception as e:
        logger.error(f"Fehler beim Laden der Zielallokation für Portfolio {portfolio_id}: {e}")
        return {"stock": 50.0, "crypto": 30.0, "commodity": 20.0}
    finally:
        await conn.close()

async def save_target_allocation(portfolio_id: int, target_alloc: dict):
    """Speichert die Ziel-Allokation für ein Portfolio in den Einstellungen."""
    key = f"portfolio_target_allocation_{portfolio_id}"
    conn = await get_db_connection()
    try:
        val_str = json.dumps(target_alloc)
        await conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, val_str))
        await conn.commit()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Zielallokation für Portfolio {portfolio_id}: {e}")
        return False
    finally:
        await conn.close()

async def save_user_device(user_id: int, subscription_info: dict):
    """Speichert eine Push-Subscription in der SQLite-Datenbank."""
    conn = await get_db_connection()
    try:
        endpoint = subscription_info.get("endpoint", "")
        keys = subscription_info.get("keys", {})
        p256dh = keys.get("p256dh", "")
        auth = keys.get("auth", "")
        
        await conn.execute("""
            INSERT OR REPLACE INTO user_devices (user_id, endpoint, p256dh, auth)
            VALUES (?, ?, ?, ?)
        """, (user_id, endpoint, p256dh, auth))
        await conn.commit()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Speichern des User-Devices: {e}")
        return False
    finally:
        await conn.close()

async def get_user_device(user_id: int) -> dict | None:
    """Holt die Push-Subscription für einen Benutzer aus der SQLite-Datenbank."""
    conn = await get_db_connection()
    try:
        async with conn.execute("""
            SELECT endpoint, p256dh, auth FROM user_devices 
            WHERE user_id = ? ORDER BY id DESC LIMIT 1
        """, (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "endpoint": row["endpoint"],
                    "keys": {
                        "p256dh": row["p256dh"],
                        "auth": row["auth"]
                    }
                }
            return None
    except Exception as e:
        logger.error(f"Fehler beim Laden des User-Devices: {e}")
        return None
    finally:
        await conn.close()

async def get_user_by_username(username: str) -> dict | None:
    """Holt einen Benutzer anhand des Benutzernamens aus der Datenbank."""
    conn = await get_db_connection()
    try:
        async with conn.execute(
            "SELECT id, username, email, hashed_password, role FROM users WHERE username = ?",
            (username,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "username": row["username"],
                    "email": row["email"],
                    "hashed_password": row["hashed_password"],
                    "role": row["role"]
                }
            return None
    except Exception as e:
        logger.error(f"Fehler beim Laden des Benutzers {username}: {e}")
        return None
    finally:
        await conn.close()

async def create_user(username: str, email: str, hashed_password: str, role: str = "viewer") -> bool:
    """Erstellt einen neuen Benutzer in der Datenbank."""
    conn = await get_db_connection()
    try:
        await conn.execute(
            "INSERT INTO users (username, email, hashed_password, role) VALUES (?, ?, ?, ?)",
            (username, email, hashed_password, role)
        )
        await conn.commit()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Benutzers {username}: {e}")
        return False
    finally:
        await conn.close()



