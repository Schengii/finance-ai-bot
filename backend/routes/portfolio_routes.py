import logging
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Portfolio & Trading"])

class PortfolioItem(BaseModel):
    symbol: str
    quantity: float
    buy_price: float

class PortfolioAnalysisRequest(BaseModel):
    holdings: List[PortfolioItem]
    strategy: str

class CashUpdateRequest(BaseModel):
    cash_balance: float

class PortfolioCreateRequest(BaseModel):
    name: str

class TransactionRequest(BaseModel):
    symbol: str
    type: str
    quantity: float
    price: float
    date: str

class TaxSimulateRequest(BaseModel):
    symbol: str
    sell_quantity: float
    sell_price: float

class TargetAllocationRequest(BaseModel):
    stock: float
    crypto: float
    commodity: float

class PaperTradingRequest(BaseModel):
    portfolio_id: int = 1
    trades: List[dict]

class DailySummaryRequest(BaseModel):
    portfolio_id: int = 1
    strategy: str = "Ausgewogen"

@router.get("/portfolio")
async def get_portfolio_route(portfolio_id: int = 1):
    """Gibt das aktuelle Portfolio des Nutzers aus der Datenbank zurück."""
    try:
        from backend.db import get_portfolio_from_db
        return await get_portfolio_from_db(portfolio_id)
    except Exception as e:
        logger.error(f"Fehler beim Laden des Portfolios {portfolio_id}: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Laden des Portfolios.")

@router.post("/portfolio")
async def add_portfolio_item_route(item: PortfolioItem, portfolio_id: int = 1):
    """Speichert oder aktualisiert ein Asset im Portfolio."""
    try:
        from backend.db import save_portfolio_item
        success = await save_portfolio_item(item.symbol, item.quantity, item.buy_price, portfolio_id)
        if not success:
            raise HTTPException(status_code=500, detail="Fehler beim Speichern in der Datenbank.")
        return {"status": "success", "message": f"Asset {item.symbol} im Portfolio gespeichert."}
    except Exception as e:
        logger.error(f"Fehler beim Speichern des Portfolio-Items {item.symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/portfolio/{symbol}")
async def delete_portfolio_item_route(symbol: str, portfolio_id: int = 1):
    """Löscht ein Asset aus dem Portfolio."""
    try:
        from backend.db import delete_portfolio_item
        success = await delete_portfolio_item(symbol, portfolio_id)
        if not success:
            raise HTTPException(status_code=500, detail="Fehler beim Löschen in der Datenbank.")
        return {"status": "success", "message": f"Asset {symbol} aus dem Portfolio gelöscht."}
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Portfolio-Items {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/portfolios")
async def get_portfolios_route():
    """Holt alle Portfolio-Profile."""
    try:
        from backend.db import get_portfolios
        return await get_portfolios()
    except Exception as e:
        logger.error(f"Fehler beim Laden der Portfolios: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Laden der Portfolio-Profile.")

@router.post("/portfolios")
async def create_portfolio_route(req: PortfolioCreateRequest):
    """Erstellt ein neues Portfolio-Profil."""
    try:
        from backend.db import create_portfolio
        success = await create_portfolio(req.name)
        if not success:
            raise HTTPException(status_code=400, detail="Portfolio-Profil konnte nicht erstellt werden (Name evtl. bereits vergeben).")
        return {"status": "success", "message": f"Portfolio '{req.name}' erfolgreich erstellt."}
    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Portfolios: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/portfolios/{portfolio_id}")
async def delete_portfolio_profile_route(portfolio_id: int):
    """Löscht ein Portfolio-Profil."""
    try:
        from backend.db import delete_portfolio
        if portfolio_id == 1:
            raise HTTPException(status_code=400, detail="Das Standard-Portfolio kann nicht gelöscht werden.")
        success = await delete_portfolio(portfolio_id)
        if not success:
            raise HTTPException(status_code=500, detail="Fehler beim Löschen des Portfolios.")
        return {"status": "success", "message": f"Portfolio {portfolio_id} gelöscht."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Portfolios {portfolio_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
