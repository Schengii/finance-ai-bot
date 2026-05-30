import os
from pathlib import Path
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# Lade Umgebungsvariablen aus der .env Datei
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Pfad zur Speicherung der Analyseergebnisse
DATA_FILE = DATA_DIR / "predictions.json"

# Gemini API Konfiguration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Standardmäßig zu überwachende Aktien und Kryptowährungen
DEFAULT_ASSETS = [
    {"symbol": "AAPL", "name": "Apple Inc.", "type": "stock"},
    {"symbol": "MSFT", "name": "Microsoft Corp.", "type": "stock"},
    {"symbol": "NVDA", "name": "NVIDIA Corp.", "type": "stock"},
    {"symbol": "TSLA", "name": "Tesla Inc.", "type": "stock"},
    {"symbol": "AMZN", "name": "Amazon.com Inc.", "type": "stock"},
    {"symbol": "BTC-USD", "name": "Bitcoin", "type": "crypto"},
    {"symbol": "ETH-USD", "name": "Ethereum", "type": "crypto"},
    {"symbol": "SOL-USD", "name": "Solana", "type": "crypto"}
]

# Wie viele Tage historischer Kursdaten geladen werden sollen für Charts & Indikatoren
HISTORICAL_DAYS = 90

# Standardmäßiges Aktualisierungsintervall in Stunden (für Scheduler)
UPDATE_INTERVAL_HOURS = 24
