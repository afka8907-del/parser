"""
Application configuration settings using Pydantic Settings.
"""

import os
from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Base paths
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    LOGS_DIR: Path = BASE_DIR / "logs"
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./data/iphone_market.db"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Telegram
    telegram_bot_token: str = ""
    telegram_admin_user_ids: str = ""
    telegram_channel_id: Optional[str] = None
    
    @property
    def admin_user_ids(self) -> List[int]:
        """Parse admin user IDs from string."""
        if not self.telegram_admin_user_ids:
            return []
        return [int(x.strip()) for x in self.telegram_admin_user_ids.split(",") if x.strip()]
    
    # Parser
    target_url: str = "https://999.md/ro/list/phone-and-communication/mobile-phones?o_16_1=776&o_1078_589=6309&o_1084_593=6371,6370&o_2200_795=18895"
    parser_interval_minutes: int = 5
    max_pages_per_run: int = 10
    incremental_pages_per_run: int = 2
    
    # Anti-bot protection
    use_proxies: bool = False
    proxy_list: str = ""
    rotate_user_agents: bool = True
    random_delay_min: int = 2
    random_delay_max: int = 5
    
    @property
    def proxies(self) -> List[str]:
        """Parse proxy list from string."""
        if not self.proxy_list:
            return []
        return [x.strip() for x in self.proxy_list.split(",") if x.strip()]
    
    # OpenAI
    openai_api_key: Optional[str] = None
    enable_ai_analysis: bool = False
    
    # Image Analysis
    enable_image_analysis: bool = False
    
    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = False
    
    # Dashboard
    dashboard_title: str = "iPhone Reseller Intelligence"
    dashboard_theme: str = "dark"
    
    # Alerts
    min_profit_threshold: int = 1000
    min_profit_percent: int = 10
    risk_score_threshold: int = 7
    notify_on_deal: bool = True
    notify_on_price_drop: bool = True
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    log_rotation: str = "500 MB"
    
    # Development
    debug: bool = False
    environment: str = "production"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure directories exist
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.LOGS_DIR.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
