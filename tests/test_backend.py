import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# pyrefly: ignore [missing-import]
from backend.data_fetcher import fetch_market_data, fetch_news
# pyrefly: ignore [missing-import]
from backend.ai_analyzer import analyze_asset_with_ai

def main():
    print("==================================================")
    print("          STARTE FINANCE AI BOT TESTLAUF          ")
    print("==================================================")
    
    # Test-Asset: Bitcoin
    symbol = "BTC-USD"
    name = "Bitcoin"
    asset_type = "crypto"
    
    # 1. Test yfinance Data Fetcher
    print(f"\n[1/3] Rufe Marktdaten und Indikatoren ab für {symbol}...")
    data = fetch_market_data(symbol, days=30)
    
    if data:
        print("[OK] Marktdaten erfolgreich geladen!")
        print(f"      Preis:         {data['current_price']} USD")
        print(f"      Änderung (1d): {data['price_change_1d']}%")
        print(f"      Änderung (7d): {data['price_change_7d']}%")
        print(f"      RSI (14):      {data['rsi']}")
        print(f"      MACD:          {data['macd']}")
        print(f"      SMA 20:        {data['sma_20']}")
        print(f"      SMA 50:        {data['sma_50']}")
        print(f"      Trend:         {data['technical_trend']}")
        print(f"      Historie:      {len(data['history'])} Tage geladen")
    else:
        print("[FEHLER] Marktdaten konnten nicht geladen werden.")
        return
        
    # 2. Test News Fetcher
    print(f"\n[2/3] Rufe Nachrichten ab für {symbol} ({name})...")
    news = fetch_news(symbol, name)
    if news:
        print(f"[OK] {len(news)} Nachrichten erfolgreich abgerufen!")
        print(f"      Top-News:      \"{news[0]['title']}\"")
        print(f"      Quelle:        {news[0]['publisher']}")
        print(f"      Veröffentlicht: {news[0]['time']}")
    else:
        print("[FEHLER] Es konnten keine Nachrichten abgerufen werden.")
        return
        
    # 3. Test AI Analyzer (Mock / Gemini)
    print(f"\n[3/3] Führe KI-Analyse durch...")
    asset_info = {"symbol": symbol, "name": name, "type": asset_type}
    prediction = analyze_asset_with_ai(asset_info, data, news)
    
    if prediction:
        print("[OK] KI-Analyse erfolgreich generiert!")
        print(f"      Empfehlung:     {prediction['recommendation']}")
        print(f"      Konfidenz:      {prediction['confidence']}%")
        print(f"      Sentiment-Score: {prediction['sentiment_score']}")
        print(f"      Risikostufe:     {prediction['risk_level']}")
        print(f"      Erklärung:      {prediction['ai_explanation']}")
        print(f"      Haupttreiber:   {prediction['key_drivers']}")
        print(f"      Hauptrisiken:   {prediction['key_risks']}")
    else:
        print("[FEHLER] KI-Analyse fehlgeschlagen.")
        return

    print("\n==================================================")
    print("              TESTLAUF ERFOLGREICH!               ")
    print("==================================================")

if __name__ == "__main__":
    main()
