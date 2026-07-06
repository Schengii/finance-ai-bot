import os
from pathlib import Path
# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings, SettingsConfigDict
# pyrefly: ignore [missing-import]
from pydantic import Field
from typing import List

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    jwt_secret_key: str = Field(default="fallback-insecure-key-change-in-production", alias="JWT_SECRET_KEY")
    allowed_origins: str = Field(default="http://127.0.0.1:8000,http://localhost:8000", alias="ALLOWED_ORIGINS")
    historical_days: int = 90
    update_interval_hours: int = 24

settings = Settings()

# SQLite-Datenbank-Pfad
DB_FILE = DATA_DIR / "finance_bot.db"

# Gemini API Konfiguration
GEMINI_API_KEY = settings.gemini_api_key

# JWT-Konfiguration (sicher aus .env geladen)
JWT_SECRET_KEY = settings.jwt_secret_key

# CORS-Konfiguration (kommagetrennte Liste aus .env)
ALLOWED_ORIGINS: List[str] = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]


# Standardmäßig zu überwachende Aktien und Kryptowährungen
DEFAULT_ASSETS = [
    {"symbol": "AAPL", "name": "Apple Inc.", "type": "stock"},
    {"symbol": "MSFT", "name": "Microsoft Corp.", "type": "stock"},
    {"symbol": "NVDA", "name": "NVIDIA Corp.", "type": "stock"},
    {"symbol": "TSLA", "name": "Tesla Inc.", "type": "stock"},
    {"symbol": "AMZN", "name": "Amazon.com Inc.", "type": "stock"},
    {"symbol": "GOOGL", "name": "Alphabet Inc.", "type": "stock"},
    {"symbol": "META", "name": "Meta Platforms Inc.", "type": "stock"},
    {"symbol": "BTC-USD", "name": "Bitcoin", "type": "crypto"},
    {"symbol": "ETH-USD", "name": "Ethereum", "type": "crypto"},
    {"symbol": "SOL-USD", "name": "Solana", "type": "crypto"},
    {"symbol": "GC=F", "name": "Gold", "type": "commodity"},
    {"symbol": "SI=F", "name": "Silber", "type": "commodity"},
    {"symbol": "CL=F", "name": "Rohöl", "type": "commodity"}
]

# Wie viele Tage historischer Kursdaten geladen werden sollen für Charts & Indikatoren
HISTORICAL_DAYS = settings.historical_days

# Standardmäßiges Aktualisierungsintervall in Stunden (für Scheduler)
UPDATE_INTERVAL_HOURS = settings.update_interval_hours
