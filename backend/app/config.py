"""
Configuration management for the Signal Analyzer application
"""

from pydantic_settings import BaseSettings
from pydantic import AliasChoices, Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # Telegram
    telegram_api_id: int
    telegram_api_hash: str
    telegram_phone: str
    telegram_session_name: str = "signal_analyzer"
    telegram_channel_ids: str = ""  # Comma-separated
    telegram_connect_timeout_seconds: float = 12
    telegram_auto_publish: bool = True
    telegram_publish_forex_chat_id: int = Field(
        default=-1004302136634,
        validation_alias=AliasChoices("TELEGRAM_PUBLISH_FOREX_CHAT_ID", "TELEGRAM_PUBLISH_CHAT_ID"),
    )
    telegram_publish_crypto_chat_id: int = -5349907572
    
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
    biquote_base_url: str = "https://biquote.io"
    biquote_poll_interval_seconds: int = 1
    biquote_stale_after_seconds: int = 300
    biquote_symbols: str = "XAUUSD,XAGUSD,EURUSD,GBPUSD,USDJPY"
    
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

    def telegram_publish_chat_id_for(self, category: str) -> Optional[int]:
        if category == "crypto":
            return self.telegram_publish_crypto_chat_id
        if category in ("cfds", "forex"):
            return self.telegram_publish_forex_chat_id
        return None

    @property
    def telegram_publish_chat_ids(self) -> set[int]:
        return {self.telegram_publish_forex_chat_id, self.telegram_publish_crypto_chat_id}
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
