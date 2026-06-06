import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_endpoints():
    print("==================================================")
    print("        STARTE NEUE API-ENDPUNKTE TESTLAUF        ")
    print("==================================================")
    
    # 1. Test /api/search/{symbol}
    print("\n[1/3] Teste Ticker-Such-Endpunkt (/api/search/AAPL)...")
    response = client.get("/api/search/AAPL")
    assert response.status_code == 200, "Suche für AAPL fehlgeschlagen"
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert "Apple" in data["name"]
    assert data["type"] == "stock"
    print("[OK] Ticker-Such-Endpunkt erfolgreich!")
    print(f"      Gefunden: {data['symbol']} -> {data['name']} ({data['type']})")
    
    # Test crypto search
    print("\n      Teste Krypto-Such-Endpunkt (/api/search/BTC-USD)...")
    response_crypto = client.get("/api/search/BTC-USD")
    assert response_crypto.status_code == 200, "Suche für BTC-USD fehlgeschlagen"
    data_crypto = response_crypto.json()
    assert data_crypto["symbol"] == "BTC-USD"
    assert "Bitcoin" in data_crypto["name"]
    assert data_crypto["type"] == "crypto"
    print("[OK] Krypto-Such-Endpunkt erfolgreich!")
    print(f"      Gefunden: {data_crypto['symbol']} -> {data_crypto['name']} ({data_crypto['type']})")
    
    # 2. Test /api/history/{symbol} for SMAs
    print("\n[2/3] Teste Historie-Endpunkt mit SMA-Werten (/api/history/AAPL?period=30d)...")
    response_hist = client.get("/api/history/AAPL?period=30d")
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
    response_acc = client.get("/api/accuracy")
    assert response_acc.status_code == 200, "Erfolgsquote fehlgeschlagen"
    data_acc = response_acc.json()
    assert "accuracy" in data_acc
    assert "total_evaluated" in data_acc
    assert "correct_count" in data_acc
    print("[OK] KI-Erfolgsquote-Endpunkt erfolgreich!")
    print(f"      KI-Trefferquote: {data_acc['accuracy']}% ({data_acc['correct_count']}/{data_acc['total_evaluated']} korrekte Empfehlungen)")
    
    print("\n==================================================")
    print("             ALLE ENDPUNKT-TESTS ERFOLGREICH!      ")
    print("==================================================")

if __name__ == "__main__":
    test_endpoints()
