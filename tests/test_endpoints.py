import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from backend.main import app

async def run_tests():
    print("==================================================")
    print("        STARTE NEUE API-ENDPUNKTE TESTLAUF        ")
    print("==================================================")
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. Test /api/search/{symbol}
        print("\n[1/3] Teste Ticker-Such-Endpunkt (/api/search/AAPL)...")
        response = await client.get("/api/search/AAPL")
        assert response.status_code == 200, "Suche für AAPL fehlgeschlagen"
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert "Apple" in data["name"]
        assert data["type"] == "stock"
        print("[OK] Ticker-Such-Endpunkt erfolgreich!")
        print(f"      Gefunden: {data['symbol']} -> {data['name']} ({data['type']})")
        
        # Test crypto search
        print("\n      Teste Krypto-Such-Endpunkt (/api/search/BTC-USD)...")
        response_crypto = await client.get("/api/search/BTC-USD")
        assert response_crypto.status_code == 200, "Suche für BTC-USD fehlgeschlagen"
        data_crypto = response_crypto.json()
        assert data_crypto["symbol"] == "BTC-USD"
        assert "Bitcoin" in data_crypto["name"]
        assert data_crypto["type"] == "crypto"
        print("[OK] Krypto-Such-Endpunkt erfolgreich!")
        print(f"      Gefunden: {data_crypto['symbol']} -> {data_crypto['name']} ({data_crypto['type']})")
        
        # 2. Test /api/history/{symbol} for SMAs
        print("\n[2/3] Teste Historie-Endpunkt mit SMA-Werten (/api/history/AAPL?period=30d)...")
        response_hist = await client.get("/api/history/AAPL?period=30d")
        assert response_hist.status_code == 200, "Historie für AAPL fehlgeschlagen"
        data_hist = response_hist.json()
        assert "history" in data_hist
        assert len(data_hist["history"]) > 0
        
        first_item = data_hist["history"][0]
        assert "sma_20" in first_item, "sma_20 fehlt im Verlauf"
        assert "sma_50" in first_item, "sma_50 fehlt im Verlauf"
        print("[OK] Historie mit SMA-Werten erfolgreich!")
        print(f"      Erster Verlaufspunkt: Date={first_item['date']}, Price={first_item['price']}, SMA 20={first_item['sma_20']}, SMA 50={first_item['sma_50']}")

        # 3. Test /api/accuracy
        print("\n[3/3] Teste KI-Erfolgsquote-Endpunkt (/api/accuracy)...")
        response_acc = await client.get("/api/accuracy")
        assert response_acc.status_code == 200, "Erfolgsquote fehlgeschlagen"
        data_acc = response_acc.json()
        assert "accuracy" in data_acc
        assert "total_evaluated" in data_acc
        assert "correct_count" in data_acc
        print("[OK] KI-Erfolgsquote-Endpunkt erfolgreich!")
        print(f"      KI-Trefferquote: {data_acc['accuracy']}% ({data_acc['correct_count']}/{data_acc['total_evaluated']} korrekte Empfehlungen)")
        
        # 4. Test Target Allocation and Rebalancing Endpoints
        print("\n[4/4] Teste Zielallokation- & Rebalancing-Endpunkte...")
        
        # Target Allocation POST
        target_data = {"stock": 45.0, "crypto": 35.0, "commodity": 20.0}
        response_post_alloc = await client.post("/api/portfolio/1/target-allocation", json=target_data)
        assert response_post_alloc.status_code == 200, "Speichern der Zielallokation fehlgeschlagen"
        
        # Target Allocation GET
        response_get_alloc = await client.get("/api/portfolio/1/target-allocation")
        assert response_get_alloc.status_code == 200, "Laden der Zielallokation fehlgeschlagen"
        alloc_res = response_get_alloc.json()
        assert alloc_res["stock"] == 45.0
        assert alloc_res["crypto"] == 35.0
        assert alloc_res["commodity"] == 20.0
        print("[OK] Zielallokation Speichern/Laden erfolgreich!")
        
        # Rebalance GET
        response_rebalance = await client.get("/api/portfolio/1/rebalance")
        assert response_rebalance.status_code == 200, "Rebalancing-Berechnung fehlgeschlagen"
        rebalance_res = response_rebalance.json()
        assert "current_allocation" in rebalance_res
        assert "target_allocation" in rebalance_res
        assert "advice_summary" in rebalance_res
        assert "recommended_trades" in rebalance_res
        print("[OK] Rebalancing-Berechnung erfolgreich!")
        
        # Paper Trading
        print("\n[5/5] Teste Paper-Trading...")
        response_paper = await client.post("/api/paper-trading/portfolio", json={
            "portfolio_id": 1,
            "trades": [
                {"symbol": "AAPL", "type": "BUY", "quantity": 2, "price": 180.0},
                {"symbol": "BTC-USD", "type": "BUY", "quantity": 0.05, "price": 60000.0}
            ]
        })
        assert response_paper.status_code == 200
        paper_data = response_paper.json()
        assert "summary" in paper_data
        assert "total_value" in paper_data
        print("[OK] Paper-Trading erfolgreich!")

        # Risk Summary
        print("\n[6/6] Teste Risikozusammenfassung...")
        response_risk = await client.get("/api/risk/summary?portfolio_id=1")
        assert response_risk.status_code == 200
        risk_data = response_risk.json()
        assert "max_drawdown" in risk_data
        assert "volatility" in risk_data
        assert "risk_level" in risk_data
        print("[OK] Risikozusammenfassung erfolgreich!")

        # Economic Calendar
        print("\n[7/7] Teste Wirtschaftskalender...")
        response_calendar = await client.get("/api/economic-calendar")
        assert response_calendar.status_code == 200
        calendar_data = response_calendar.json()
        assert isinstance(calendar_data.get("events"), list)
        assert len(calendar_data["events"]) > 0
        print("[OK] Wirtschaftskalender erfolgreich!")

        # Daily AI Summary
        print("\n[8/8] Teste Tägliche Portfolio-Zusammenfassung...")
        response_summary = await client.post("/api/portfolio/daily-summary", json={
            "portfolio_id": 1,
            "strategy": "Ausgewogen"
        })
        assert response_summary.status_code == 200
        summary_data = response_summary.json()
        assert "headline" in summary_data
        assert "summary" in summary_data
        print("[OK] Tägliche Portfolio-Zusammenfassung erfolgreich!")

    print("\n==================================================")
    print("             ALLE ENDPUNKT-TESTS ERFOLGREICH!      ")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(run_tests())
