"""
Configuration management for the Signal Analyzer application
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # Telegram
    telegram_api_id: int
    telegram_api_hash: str
    telegram_phone: str
    telegram_session_name: str = "signal_analyzer"
    telegram_channel_ids: str = ""  # Comma-separated
    
    # Database
    database_url: str = "sqlite:///./signal_analyzer.db"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = False
    api_reload: bool = False
    
    # Market Data
    market_data_provider: str = "yfinance"
    market_data_base_url: str = "https://api.gold-api.com"
    market_data_poll_interval_seconds: int = 30
    market_data_stale_after_seconds: int = 300
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    # Features
    enable_telegram_listener: bool = True
    enable_analysis_engine: bool = True
    enable_trade_engine: bool = True
    
    @property
    def channel_ids(self) -> list[int]:
        """Parse comma-separated channel IDs"""
        if not self.telegram_channel_ids:
            return []
        return [int(cid.strip()) for cid in self.telegram_channel_ids.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
