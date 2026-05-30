import yfinance as yf
import json

try:
    ticker = yf.Ticker("AAPL")
    print("Ticker initialized successfully.")
    
    news = ticker.news
    print(f"Number of news items: {len(news) if news else 0}")
    if news:
        print("First news item keys:", list(news[0].keys()))
        print("First news item:")
        print(json.dumps(news[0], indent=2))
        
        # Check structure of the news
        for i, item in enumerate(news[:3]):
            print(f"\nItem {i}:")
            print(f"Title: {repr(item.get('title'))}")
            print(f"Publisher: {repr(item.get('publisher'))}")
except Exception as e:
    print(f"Error: {e}")
