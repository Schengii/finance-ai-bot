# pyrefly: ignore [missing-import]
import yfinance as yf
# pyrefly: ignore [missing-import]
import pandas as pd
# pyrefly: ignore [missing-import]
import numpy as np
from datetime import datetime, timedelta
import logging
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def calculate_rsi(prices, period=14):
    """Berechnet den Relative Strength Index (RSI)."""
    if len(prices) < period + 1:
        return 50.0 # Standardwert falls nicht genug Daten
    
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    # Vermeidung von Division durch Null
    loss = loss.replace(0, 0.00001)
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    val = rsi.iloc[-1]
    if pd.isna(val) or np.isnan(val) or np.isinf(val):
        return 50.0
    return float(val)

def calculate_macd(prices):
    """Berechnet MACD und Signal-Linie."""
    if len(prices) < 26:
        return 0.0, 0.0, 0.0
    
    exp1 = prices.ewm(span=12, adjust=False).mean()
    exp2 = prices.ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    
    m = macd.iloc[-1]
    s = signal.iloc[-1]
    h = hist.iloc[-1]
    
    if pd.isna(m) or np.isnan(m) or np.isinf(m): m = 0.0
    if pd.isna(s) or np.isnan(s) or np.isinf(s): s = 0.0
    if pd.isna(h) or np.isnan(h) or np.isinf(h): h = 0.0
    
    return float(m), float(s), float(h)

def calculate_bollinger_bands(prices, period=20, num_std=2):
    """Berechnet Bollinger Bands (Oberes und Unteres Band)."""
    if len(prices) < period:
        cp = float(prices.iloc[-1]) if not prices.empty else 0.0
        return cp, cp
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper = sma + (std * num_std)
    lower = sma - (std * num_std)
    u_val = float(upper.iloc[-1]) if not pd.isna(upper.iloc[-1]) else float(prices.iloc[-1])
    l_val = float(lower.iloc[-1]) if not pd.isna(lower.iloc[-1]) else float(prices.iloc[-1])
    return round(u_val, 2), round(l_val, 2)

def calculate_ema(prices, period=200):
    """Berechnet Exponential Moving Average (EMA)."""
    if len(prices) < 10:
        return float(prices.iloc[-1]) if not prices.empty else 0.0
    ema_series = prices.ewm(span=period, adjust=False).mean()
    val = float(ema_series.iloc[-1])
    if pd.isna(val) or np.isnan(val) or np.isinf(val):
        val = float(prices.iloc[-1])
    return round(val, 2)

def calculate_stochastic(df, period=14):
    """Berechnet den Stochastik-Oszillator (%K)."""
    if len(df) < period or 'Low' not in df or 'High' not in df or 'Close' not in df:
        return 50.0
    low_min = df['Low'].rolling(window=period).min()
    high_max = df['High'].rolling(window=period).max()
    k = 100 * ((df['Close'] - low_min) / (high_max - low_min + 1e-9))
    val = float(k.iloc[-1])
    if pd.isna(val) or np.isnan(val) or np.isinf(val):
        return 50.0
    return round(val, 2)

def fetch_market_data(symbol, days=90):
    """Holt historische Daten und berechnet technische Indikatoren & Fundamentaldaten."""
    logger.info(f"Hole Marktdaten für {symbol}...")
    try:
        ticker = yf.Ticker(symbol)
        # Genügend Daten abrufen für EMA 200 und 52-Wochen-Range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=max(days + 250, 400))
        
        df = ticker.history(start=start_date, end=end_date)
        
        if df.empty:
            logger.error(f"Keine historischen Daten für {symbol} gefunden.")
            return None
            
        close_prices = df['Close']
        
        # Aktueller Preis und historische Kursentwicklung
        current_price = float(close_prices.iloc[-1])
        prev_close = float(close_prices.iloc[-2]) if len(close_prices) > 1 else current_price
        
        price_change_1d = ((current_price - prev_close) / prev_close) * 100
        
        # 7-Tage & 30-Tage Entwicklung
        price_7d_ago = float(close_prices.iloc[-6]) if len(close_prices) >= 6 else float(close_prices.iloc[0])
        price_change_7d = ((current_price - price_7d_ago) / price_7d_ago) * 100
        
        price_30d_ago = float(close_prices.iloc[-22]) if len(close_prices) >= 22 else float(close_prices.iloc[0])
        price_change_30d = ((current_price - price_30d_ago) / price_30d_ago) * 100
        
        # Gleitende Durchschnitte & EMA
        sma_20 = float(close_prices.rolling(window=20).mean().iloc[-1]) if len(close_prices) >= 20 else current_price
        sma_50 = float(close_prices.rolling(window=50).mean().iloc[-1]) if len(close_prices) >= 50 else current_price
        ema_200 = calculate_ema(close_prices, 200)
        
        # RSI, MACD, Bollinger Bands, Stochastik
        rsi = calculate_rsi(close_prices)
        macd, macd_signal, macd_hist = calculate_macd(close_prices)
        bb_upper, bb_lower = calculate_bollinger_bands(close_prices, 20, 2)
        stoch_k = calculate_stochastic(df, 14)
        
        # Trend-Einschätzung (Technisch)
        tech_trend = "Neutral"
        if current_price > sma_20 and sma_20 > sma_50:
            tech_trend = "Bullish"
        elif current_price < sma_20 and sma_20 < sma_50:
            tech_trend = "Bearish"
            
        # Historie für den Chart (letzten 90 Tage) mit Bollinger & EMA
        chart_df = df.tail(days)
        bb_upper_series = df['Close'].rolling(window=20).mean() + (df['Close'].rolling(window=20).std() * 2)
        bb_lower_series = df['Close'].rolling(window=20).mean() - (df['Close'].rolling(window=20).std() * 2)
        ema_200_series = df['Close'].ewm(span=200, adjust=False).mean()
        
        history = []
        for index, row in chart_df.iterrows():
            idx_pos = df.index.get_loc(index)
            history.append({
                "date": index.strftime('%Y-%m-%d'),
                "price": round(float(row['Close']), 2),
                "volume": int(row['Volume']) if 'Volume' in row else 0,
                "ema_200": round(float(ema_200_series.iloc[idx_pos]), 2) if not pd.isna(ema_200_series.iloc[idx_pos]) else round(float(row['Close']), 2),
                "bb_upper": round(float(bb_upper_series.iloc[idx_pos]), 2) if not pd.isna(bb_upper_series.iloc[idx_pos]) else round(float(row['Close']), 2),
                "bb_lower": round(float(bb_lower_series.iloc[idx_pos]), 2) if not pd.isna(bb_lower_series.iloc[idx_pos]) else round(float(row['Close']), 2)
            })
            
        # Fundamentaldaten & Dividenden auslesen
        div_yield = 0.0
        div_rate = 0.0
        pe_ratio = None
        market_cap = None
        fifty_two_high = round(float(close_prices.max()), 2)
        fifty_two_low = round(float(close_prices.min()), 2)
        beta = 1.0
        eps = None
        
        try:
            info = ticker.info
            if info:
                div_yield = float(info.get('dividendYield') or 0.0)
                div_rate = float(info.get('dividendRate') or 0.0)
                if div_yield > 1.0:
                    div_yield = div_yield / 100.0
                
                pe_val = info.get('forwardPE') or info.get('trailingPE')
                if pe_val: pe_ratio = round(float(pe_val), 2)
                
                mcap = info.get('marketCap')
                if mcap: market_cap = int(mcap)
                
                f_high = info.get('fiftyTwoWeekHigh')
                if f_high: fifty_two_high = round(float(f_high), 2)
                
                f_low = info.get('fiftyTwoWeekLow')
                if f_low: fifty_two_low = round(float(f_low), 2)
                
                beta_val = info.get('beta')
                if beta_val: beta = round(float(beta_val), 2)
                
                eps_val = info.get('trailingEps') or info.get('forwardEps')
                if eps_val: eps = round(float(eps_val), 2)
        except Exception as e_info:
            logger.warning(f"Fundamentaldaten für {symbol} teilweise nicht verfügbar: {e_info}")

        return {
            "symbol": symbol,
            "current_price": round(current_price, 2),
            "price_change_1d": round(price_change_1d, 2),
            "price_change_7d": round(price_change_7d, 2),
            "price_change_30d": round(price_change_30d, 2),
            "sma_20": round(sma_20, 2),
            "sma_50": round(sma_50, 2),
            "ema_200": round(ema_200, 2),
            "rsi": round(rsi, 2),
            "macd": round(macd, 4),
            "macd_signal": round(macd_signal, 4),
            "macd_hist": round(macd_hist, 4),
            "bb_upper": bb_upper,
            "bb_lower": bb_lower,
            "stoch_k": stoch_k,
            "technical_trend": tech_trend,
            "history": history,
            "dividend_yield": div_yield,
            "dividend_rate": div_rate,
            "pe_ratio": pe_ratio,
            "market_cap": market_cap,
            "fifty_two_high": fifty_two_high,
            "fifty_two_low": fifty_two_low,
            "beta": beta,
            "eps": eps
        }
    except Exception as e:
        logger.error(f"Fehler beim Laden der Marktdaten für {symbol}: {e}")
        return None
    except Exception as e:
        logger.error(f"Fehler beim Laden der Marktdaten für {symbol}: {e}")
        return None

def fetch_exchange_rate():
    """Holt den aktuellen USD/EUR-Wechselkurs."""
    try:
        ticker = yf.Ticker("EURUSD=X")
        df = ticker.history(period="1d")
        if not df.empty:
            rate = float(df['Close'].iloc[-1])
            return rate
    except Exception as e:
        logger.error(f"Fehler beim Laden des USD/EUR-Kurses: {e}")
    return 0.92 # Plausibler Standardwert

def fetch_dividend_history(symbol):
    """Holt historische Dividenden der letzten 12 Monate, um Zahlungsmonate zu ermitteln."""
    try:
        ticker = yf.Ticker(symbol)
        divs = ticker.dividends
        if not divs.empty:
            # Letztes Jahr filtern
            one_year_ago = datetime.now() - timedelta(days=365)
            # divs.index hat Zeitzonen, one_year_ago machen wir auch zeitzonenbewusst falls nötig
            if divs.index.tz:
                import pytz
                one_year_ago = one_year_ago.replace(tzinfo=pytz.utc)
            
            recent_divs = divs[divs.index >= one_year_ago]
            months = [int(date.month) for date in recent_divs.index]
            return sorted(list(set(months)))
    except Exception as e:
        logger.error(f"Fehler beim Laden der Dividendenhistorie für {symbol}: {e}")
    # Standard: Vierteljährlich (z.B. März, Juni, September, Dezember)
    return [3, 6, 9, 12]


def fetch_news(symbol, name):
    """Holt Nachrichten zu einem Ticker via yfinance und bereitet sie auf."""
    logger.info(f"Hole Nachrichten für {symbol} ({name})...")
    formatted_news = []
    
    try:
        ticker = yf.Ticker(symbol)
        yf_news = ticker.news
        
        if yf_news:
            for item in yf_news[:10]: # Maximal 10 Nachrichten
                # Support both old flat structure and new nested 'content' structure
                content = item.get("content", {}) if isinstance(item.get("content"), dict) else item
                
                title = content.get("title")
                if not title:
                    continue
                title = str(title).strip()
                if not title:
                    continue
                
                # Publisher
                publisher = content.get("publisher") or item.get("publisher") or ""
                publisher = str(publisher).strip()
                
                # Link
                link = content.get("link") or item.get("link") or ""
                link = str(link).strip()
                
                # Summary
                summary = content.get("summary") or item.get("summary") or ""
                summary = str(summary).strip()
                
                # Time / Date
                pub_time = content.get("providerPublishTime") or item.get("providerPublishTime") or content.get("pubDate")
                
                dt_str = ""
                if pub_time:
                    if isinstance(pub_time, (int, float)):
                        try:
                            dt_str = datetime.fromtimestamp(pub_time).strftime('%Y-%m-%d %H:%M')
                        except Exception:
                            dt_str = str(pub_time)
                    else:
                        # It is likely a string (ISO format or similar)
                        dt_str = str(pub_time)
                        # Try to format it nicer if possible
                        try:
                            # e.g., '2026-05-30T13:54:00Z'
                            if 'T' in dt_str:
                                t_part = dt_str.split('T')
                                date_part = t_part[0]
                                time_part = t_part[1][:5]
                                dt_str = f"{date_part} {time_part}"
                        except Exception:
                            pass
                else:
                    dt_str = datetime.now().strftime('%Y-%m-%d %H:%M')
                
                formatted_news.append({
                    "title": title,
                    "publisher": publisher,
                    "link": link,
                    "time": dt_str,
                    "summary": summary
                })
        
        # Fallback: Wenn Yahoo Finance keine Nachrichten liefert, Google News RSS nutzen
        if not formatted_news:
            query = str(name).replace(" ", "+") if name else symbol
            url = f"https://news.google.com/rss/search?q={query}&hl=de&gl=DE&ceid=DE:de"
            
            logger.info(f"Fallback auf Google News RSS für {name}...")
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                xml_data = response.read()
                
            root = ET.fromstring(xml_data)
            for item in root.findall('.//item')[:10]:
                title = item.find('title').text if item.find('title') is not None else ""
                link = item.find('link').text if item.find('link') is not None else ""
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                
                # Versuche den Publisher aus dem source-Tag auszulesen
                source_elem = item.find('source')
                publisher = source_elem.text if source_elem is not None else "Google News"
                publisher = str(publisher).strip()
                
                # Datumsformat bereinigen
                pub_date_str = ""
                if pub_date:
                    try:
                        dt = parsedate_to_datetime(pub_date)
                        pub_date_str = dt.strftime('%Y-%m-%d %H:%M')
                    except Exception:
                        pub_date_str = pub_date
                else:
                    pub_date_str = datetime.now().strftime('%Y-%m-%d %H:%M')
                
                # Einfache Bereinigung des Titels von Quellenangaben am Ende
                if " - " in title:
                    title = " - ".join(title.split(" - ")[:-1])
                title = str(title).strip()
                
                if title:
                    formatted_news.append({
                        "title": title,
                        "publisher": publisher,
                        "link": link,
                        "time": pub_date_str,
                        "summary": ""
                    })
                
    except Exception as e:
        logger.error(f"Fehler beim Laden der Nachrichten für {symbol}: {e}")
        
    return formatted_news


async def get_asset_market_data(symbol, asset_type="stock"):
    """Async Wrapper für fetch_market_data."""
    return fetch_market_data(symbol)
