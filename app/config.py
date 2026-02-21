from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os


class Settings(BaseSettings):
    """Application configuration settings"""
    
    # Application
    app_name: str = "Honeypot Scam Detection API"
    env: str = "production"
    debug: bool = False
    api_key: str
    
    # Server (PORT is auto-set by Cloud Run)
    host: str = "0.0.0.0"
    port: int = int(os.environ.get("PORT", "8000"))  # Cloud Run sets PORT automatically
    workers: int = 4
    
    # MongoDB (Cloud Optimized)
    mongodb_url: str
    mongodb_db_name: str = "honeypot_db"
    mongodb_max_pool_size: int = 100
    mongodb_min_pool_size: int = 10
    mongodb_max_idle_time_ms: int = 45000
    mongodb_connect_timeout_ms: int = 5000
    mongodb_server_selection_timeout_ms: int = 5000
    
    # Google Gemini (Premium) - Optimized for human-like responses
    gemini_api_key: str
    gemini_model: str = "gemini-3-pro-preview"    # Best model first
    gemini_max_retries: int = 3
    gemini_timeout: int = 35                       # Slight buffer for ~30s target response time
    gemini_context_messages: int = 10              # Full conversation history to prevent repetition
    gemini_max_output_tokens: int = 1000            # Increased to prevent JSON truncation (content length controlled by prompt)
    gemini_temperature: float = 0.85               # Higher for more natural, human-like variation
    
    # GUVI Callback
    guvi_callback_url: str = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"
    
    # Performance
    max_connections: int = 100
    connection_timeout: int = 30
    request_timeout: int = 60
    enable_caching: bool = True
    cache_ttl: int = 300
    
    # Security
    cors_origins: List[str] = ["*"]
    rate_limit_per_minute: int = 100
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


settings = Settings()