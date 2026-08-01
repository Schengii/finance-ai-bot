import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from backend.main import app

async def run_tests():
    from backend.db import init_db
    await init_db()

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

        # 9. Test Cash Balance & Performance Metrics
        print("\n[9/12] Teste Cash-Bestand & Finanzkennzahlen...")
        res_cash_post = await client.post("/api/portfolio/1/cash", json={"cash_balance": 2500.0})
        assert res_cash_post.status_code == 200
        res_cash_get = await client.get("/api/portfolio/1/cash")
        assert res_cash_get.status_code == 200
        assert res_cash_get.json()["cash_balance"] == 2500.0

        res_perf = await client.get("/api/portfolio/1/performance-metrics")
        assert res_perf.status_code == 200
        perf_data = res_perf.json()
        assert "total_portfolio_value" in perf_data
        assert "sharpe_ratio" in perf_data
        print("[OK] Cash-Bestand & Performance-Kennzahlen erfolgreich!")

        # 10. Test System Backup
        print("\n[10/12] Teste System-Backup...")
        res_backup = await client.get("/api/system/backup")
        assert res_backup.status_code == 200
        assert "assets" in res_backup.json()
        print("[OK] System-Backup erfolgreich!")

        # 11. Test CSV Import
        print("\n[11/12] Teste Broker-CSV-Import...")
        csv_sample = "Symbol,Anzahl,Kaufpreis,Aktion\nAAPL,5,150.0,BUY\nMSFT,2,300.0,BUY"
        res_csv = await client.post("/api/portfolio/1/import-csv", json={"csv_text": csv_sample})
        assert res_csv.status_code == 200
        assert res_csv.json()["imported_count"] == 2
        print("[OK] Broker-CSV-Import erfolgreich!")

        # 12. Test Asset Comparison
        print("\n[12/16] Teste Asset-Vergleich...")
        res_compare = await client.get("/api/compare?symbols=AAPL,MSFT")
        assert res_compare.status_code == 200
        compare_data = res_compare.json()
        assert len(compare_data) == 2
        print("[OK] Asset-Vergleich erfolgreich!")

        # 13. Test VAPID Key Endpoint
        print("\n[13/16] Teste VAPID Key Endpunkt...")
        res_vapid = await client.get("/api/notifications/vapid-key")
        assert res_vapid.status_code == 200
        assert "public_key" in res_vapid.json()
        print("[OK] VAPID Key Endpunkt erfolgreich!")

        # 14. Test DRIP Simulation
        print("\n[14/16] Teste DRIP Dividenden-Simulation...")
        res_drip = await client.post("/api/portfolio/1/drip-simulation", json={"years": 5, "annual_contribution": 1000, "drip_enabled": True})
        assert res_drip.status_code == 200
        drip_data = res_drip.json()
        assert "projections" in drip_data
        assert len(drip_data["projections"]) == 5
        print("[OK] DRIP Dividenden-Simulation erfolgreich!")

        # 15. Test Monte-Carlo Simulation
        print("\n[15/16] Teste Monte-Carlo Simulation...")
        res_mc = await client.post("/api/portfolio/1/monte-carlo", json={"num_simulations": 100, "time_horizon_years": 3})
        assert res_mc.status_code == 200
        mc_data = res_mc.json()
        assert "percentile_5" in mc_data
        assert "percentile_50_median" in mc_data
        assert "percentile_95" in mc_data
        print("[OK] Monte-Carlo Simulation erfolgreich!")

        # 16. Test Markowitz Efficient Frontier
        print("\n[16/22] Teste Efficient Frontier...")
        res_ef = await client.get("/api/portfolio/1/efficient-frontier")
        assert res_ef.status_code == 200
        ef_data = res_ef.json()
        assert "efficient_frontier" in ef_data
        assert len(ef_data["efficient_frontier"]) > 0
        print("[OK] Efficient Frontier erfolgreich!")

        # 17. Test KI-Komitee Analysis
        print("\n[17/22] Teste Ensemble KI-Komitee...")
        res_comm = await client.get("/api/committee/AAPL")
        assert res_comm.status_code == 200
        comm_data = res_comm.json()
        assert "bull_case" in comm_data
        assert "bear_case" in comm_data
        assert "quant_metrics" in comm_data
        print("[OK] Ensemble KI-Komitee erfolgreich!")

        # 18. Test Fundamental Analysis (Piotroski & Altman)
        print("\n[18/22] Teste Fundamentalanalyse (Piotroski & Altman)...")
        res_fund = await client.get("/api/fundamentals/AAPL")
        assert res_fund.status_code == 200
        fund_data = res_fund.json()
        assert "piotroski_f_score" in fund_data
        assert "altman_z_score" in fund_data
        print("[OK] Fundamentalanalyse (Piotroski & Altman) erfolgreich!")

        # 19. Test Options & Hedging Strategy
        print("\n[19/22] Teste Options & Hedging Strategie...")
        res_hedge = await client.post("/api/portfolio/1/hedging-strategy")
        assert res_hedge.status_code == 200
        hedge_data = res_hedge.json()
        assert "strategies" in hedge_data
        print("[OK] Options & Hedging Strategie erfolgreich!")

        # 20. Test PDF Report Data Generation
        print("\n[20/22] Teste PDF Steuer- & Performance Report...")
        res_report = await client.get("/api/reports/pdf?portfolio_id=1")
        assert res_report.status_code == 200
        report_data = res_report.json()
        assert "fifo_tax" in report_data
        print("[OK] PDF Steuer- & Performance Report erfolgreich!")

        # 21. Test Auto-Trader Rules
        print("\n[21/22] Teste Auto-Trader Regeln...")
        res_add_rule = await client.post("/api/auto-trader/rules", json={"symbol": "AAPL", "min_confidence": 80, "max_rsi": 40.0, "buy_amount_eur": 500.0})
        assert res_add_rule.status_code == 200
        res_get_rules = await client.get("/api/auto-trader/rules")
        assert res_get_rules.status_code == 200
        assert len(res_get_rules.json()["rules"]) > 0
        print("[OK] Auto-Trader Regeln erfolgreich!")

        # 22. Test Notification History
        print("\n[22/22] Teste Notification Historie...")
        res_notifs = await client.get("/api/notifications/history")
        assert res_notifs.status_code == 200
        print("[OK] Notification Historie erfolgreich!")

    print("\n==================================================")
    print("             ALLE ENDPUNKT-TESTS ERFOLGREICH!      ")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(run_tests())
