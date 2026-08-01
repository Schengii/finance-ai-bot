import logging
import asyncio
from datetime import datetime
from backend.db import (
    get_db_connection,
    add_portfolio_investment,
    remove_portfolio_investment,
    get_portfolio_from_db,
    add_notification
)

logger = logging.getLogger(__name__)

async def evaluate_auto_trader_rules(portfolio_id: int, predictions: dict):
    """
    Kreditiert und führt automatische Handelsregeln und Trailing-Stop-Loss-Orders aus.
    - Regel-Beispiel: "WENN confidence >= 80 UND rsi <= 35 DANN KAUFE 5 STÜCK"
    - Trailing Stop-Loss: Folgt dem Höchstkurs nach oben und löst bei Rücksetzern aus.
    """
    try:
        db = await get_db_connection()
        try:
            # 1. Trailing-Stop-Loss Auswertung
            cursor = await db.execute(
                "SELECT id, symbol, quantity, highest_price, trail_percent FROM trailing_stops WHERE portfolio_id = ?",
                (portfolio_id,)
            )
            stops = await cursor.fetchall()

            for stop in stops:
                stop_id, symbol, qty, highest_p, trail_pct = stop
                pred = predictions.get(symbol)
                if not pred:
                    continue

                curr_p = pred["price"]

                # Falls neuer Höchstkurs -> Trailing Stop nachziehen
                if curr_p > highest_p:
                    await db.execute(
                        "UPDATE trailing_stops SET highest_price = ? WHERE id = ?",
                        (curr_p, stop_id)
                    )
                    await db.commit()
                    logger.info(f"Trailing Stop für {symbol} nachgezogen auf Höchstkurs {curr_p:.2f} €")
                else:
                    # Stopp-Schwelle berechnen
                    stop_threshold = highest_p * (1.0 - (trail_pct / 100.0))
                    if curr_p <= stop_threshold:
                        # TRAILING STOP GETRIGGERT -> VERKAUF
                        logger.warning(f"Trailing Stop für {symbol} bei {curr_p:.2f} € getriggert! Verkaufe {qty} Stück.")
                        await remove_portfolio_investment(portfolio_id, symbol)
                        await db.execute("DELETE FROM trailing_stops WHERE id = ?", (stop_id,))
                        await db.commit()

                        await add_notification(
                            title=f"🛑 Trailing-Stop-Loss getriggert: {symbol}",
                            message=f"Position {symbol} ({qty} Stk.) wurde bei {curr_p:.2f} € automatisch verkauft.",
                            type="warning",
                            symbol=symbol
                        )

            # 2. Auto-Trader Regeln ausführen
            cursor = await db.execute(
                "SELECT id, symbol, min_confidence, max_rsi, buy_amount_eur, is_active FROM auto_trader_rules WHERE portfolio_id = ? AND is_active = 1",
                (portfolio_id,)
            )
            rules = await cursor.fetchall()

            for rule in rules:
                rule_id, symbol, min_conf, max_rsi, buy_eur, is_active = rule
                pred = predictions.get(symbol)
                if not pred:
                    continue

                conf = pred.get("confidence", 0)
                rsi = pred.get("rsi", 50)
                price = pred.get("price", 0)

                if conf >= min_conf and rsi <= max_rsi and price > 0:
                    qty = round(buy_eur / price, 4)
                    if qty > 0:
                        logger.info(f"Auto-Trader regel getriggert für {symbol}! Kaufe {qty} Stk. für {buy_eur} €.")
                        await add_portfolio_investment(portfolio_id, symbol, qty, price)
                        await add_notification(
                            title=f"🤖 Auto-Trader Kauf: {symbol}",
                            message=f"Bedingung erfüllt (Konfidenz: {conf}%, RSI: {rsi:.1f}). {qty} Stk. für {buy_eur} € gekauft.",
                            type="success",
                            symbol=symbol
                        )
        finally:
            await db.close()

    except Exception as e:
        logger.error(f"Fehler bei Auto-Trader Regel-Auswertung: {e}")
