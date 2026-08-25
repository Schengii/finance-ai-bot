import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from backend.db import get_db_connection, save_portfolio_item, delete_portfolio_item, add_notification

logger = logging.getLogger(__name__)

async def create_advanced_order(
    portfolio_id: int,
    symbol: str,
    side: str, # "BUY" oder "SELL"
    order_type: str, # "LIMIT", "STOP_LIMIT", "TRAILING_STOP", "OCO", "BRACKET"
    quantity: float,
    limit_price: Optional[float] = None,
    stop_price: Optional[float] = None,
    take_profit_price: Optional[float] = None,
    stop_loss_price: Optional[float] = None,
    trail_percent: Optional[float] = None
) -> dict:
    """
    Erstellt eine fortschrittliche Order (inkl. OCO und Bracket-Orders) in der SQLite-Datenbank.
    """
    db = await get_db_connection()
    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sym = symbol.upper()
        
        # 1. Haupt-Order anlegen
        cursor = await db.execute(
            """
            INSERT INTO advanced_orders (
                portfolio_id, symbol, side, order_type, quantity,
                limit_price, stop_price, take_profit_price, stop_loss_price,
                trail_percent, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?)
            """,
            (
                portfolio_id, sym, side.upper(), order_type.upper(), quantity,
                limit_price, stop_price, take_profit_price, stop_loss_price,
                trail_percent, now_str
            )
        )
        order_id = cursor.lastrowid
        await db.commit()
        
        logger.info(f"Advanced Order #{order_id} ({order_type} {side} {quantity} {sym}) erfolgreich erstellt.")
        return {
            "status": "success",
            "order_id": order_id,
            "message": f"Order #{order_id} ({order_type} {side} {quantity} Stk. {sym}) platziert."
        }
    finally:
        await db.close()


async def get_advanced_orders(portfolio_id: int = 1, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Holt alle offenen oder historischen Orders für das Portfolio."""
    db = await get_db_connection()
    try:
        if status:
            cursor = await db.execute(
                "SELECT * FROM advanced_orders WHERE portfolio_id = ? AND status = ? ORDER BY id DESC",
                (portfolio_id, status)
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM advanced_orders WHERE portfolio_id = ? ORDER BY id DESC LIMIT 50",
                (portfolio_id,)
            )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def cancel_advanced_order(order_id: int) -> bool:
    """Storniert eine offene Order."""
    db = await get_db_connection()
    try:
        cursor = await db.execute(
            "UPDATE advanced_orders SET status = 'CANCELLED' WHERE id = ? AND status = 'PENDING'",
            (order_id,)
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def evaluate_advanced_orders(portfolio_id: int, market_prices: Dict[str, float]) -> List[Dict[str, Any]]:
    """
    Wertet alle offenen PENDING Orders gegen die aktuellen Marktpreise aus.
    Führt automatische Bracket-Aktivierungen, OCO-Stornierungen und Slippage-Berechnungen durch.
    """
    executed_trades = []
    db = await get_db_connection()
    try:
        cursor = await db.execute(
            "SELECT * FROM advanced_orders WHERE portfolio_id = ? AND status = 'PENDING'",
            (portfolio_id,)
        )
        orders = [dict(r) for r in await cursor.fetchall()]

        for o in orders:
            oid = o["id"]
            sym = o["symbol"]
            side = o["side"]
            otype = o["order_type"]
            qty = float(o["quantity"])
            curr_p = market_prices.get(sym)

            if not curr_p or curr_p <= 0:
                continue

            executed = False
            exec_price = curr_p
            slippage = 0.0005 # 0.05% Slippage Simulation

            # 1. LIMIT ORDER
            if otype == "LIMIT":
                limit_p = float(o.get("limit_price") or 0)
                if side == "BUY" and curr_p <= limit_p:
                    exec_price = curr_p * (1.0 + slippage)
                    executed = True
                elif side == "SELL" and curr_p >= limit_p:
                    exec_price = curr_p * (1.0 - slippage)
                    executed = True

            # 2. STOP LOSS ORDER
            elif otype in ["STOP", "STOP_LOSS"]:
                stop_p = float(o.get("stop_price") or 0)
                if side == "SELL" and curr_p <= stop_p:
                    exec_price = curr_p * (1.0 - slippage)
                    executed = True

            # 3. OCO (One-Cancels-Other)
            elif otype == "OCO":
                tp = float(o.get("take_profit_price") or 999999)
                sl = float(o.get("stop_loss_price") or 0)
                if curr_p >= tp:
                    exec_price = curr_p * (1.0 - slippage)
                    executed = True
                    logger.info(f"OCO #{oid} TP getriggert bei {curr_p:.2f} €")
                elif curr_p <= sl:
                    exec_price = curr_p * (1.0 - slippage)
                    executed = True
                    logger.info(f"OCO #{oid} SL getriggert bei {curr_p:.2f} €")

            # 4. BRACKET ORDER (Entry + Take Profit + Stop Loss)
            elif otype == "BRACKET":
                limit_p = float(o.get("limit_price") or curr_p)
                tp = float(o.get("take_profit_price") or (curr_p * 1.10))
                sl = float(o.get("stop_loss_price") or (curr_p * 0.93))

                if side == "BUY" and curr_p <= limit_p:
                    exec_price = curr_p * (1.0 + slippage)
                    executed = True
                    # Nach Ausführung des Entry-Kaufs -> Automatisches OCO für Exit anlegen!
                    await db.execute(
                        """
                        INSERT INTO advanced_orders (
                            portfolio_id, symbol, side, order_type, quantity,
                            take_profit_price, stop_loss_price, status, created_at
                        ) VALUES (?, ?, 'SELL', 'OCO', ?, ?, ?, 'PENDING', datetime('now'))
                        """,
                        (portfolio_id, sym, qty, tp, sl)
                    )
                    logger.info(f"Bracket #{oid} Entry ausgeführt -> Folge-OCO (TP: {tp}, SL: {sl}) platziert.")

            # AUSFÜHRUNG DURCHFÜHREN
            if executed:
                fee = 1.0 # 1 € pauschale Broker-Gebühr
                exec_price = round(exec_price, 2)
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # Update Order-Status
                await db.execute(
                    "UPDATE advanced_orders SET status = 'FILLED', executed_at = ?, execution_price = ? WHERE id = ?",
                    (now_str, exec_price, oid)
                )

                # Portfolio anpassen
                if side == "BUY":
                    await save_portfolio_item(sym, qty, exec_price, portfolio_id)
                elif side == "SELL":
                    await delete_portfolio_item(sym, portfolio_id)

                # Notification auslösen
                await add_notification(
                    title=f"🎯 Order #{oid} Ausgeführt: {side} {sym}",
                    message=f"{qty} Stk. {sym} zu {exec_price:.2f} € ({otype}) ausgeführt (Gebühr: {fee:.2f} €).",
                    notif_type="success",
                    symbol=sym
                )

                executed_trades.append({
                    "order_id": oid,
                    "symbol": sym,
                    "side": side,
                    "type": otype,
                    "quantity": qty,
                    "execution_price": exec_price,
                    "fee": fee
                })

        await db.commit()
    finally:
        await db.close()

    return executed_trades
