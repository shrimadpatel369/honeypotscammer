from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os


class Settings(BaseSettings):
    """Application configuration settings"""
    
    # Application
    app_name: str = "Honeypot Scam Detection API"
    env: str = "production"
    debug: bool = False
    api_key: str = "Dm59xTVhENeQ2x2Jr9xt5qEpTYWbKhiYDkOuZ2rVdC63yMaWTg"
    
    # Server (PORT is auto-set by Cloud Run)
    host: str = "0.0.0.0"
    port: int = int(os.environ.get("PORT", "8000"))  # Cloud Run sets PORT automatically
    workers: int = 4
    
    # MongoDB (Cloud Optimized)
    mongodb_url: str = "mongodb://shrimad:OHXiq3rWMFCfm7eR@34.131.176.117:27017/honeypotfraud?authSource=admin"
    mongodb_db_name: str = "honeypotfraud"
    mongodb_max_pool_size: int = 100
    mongodb_min_pool_size: int = 10
    mongodb_max_idle_time_ms: int = 45000
    mongodb_connect_timeout_ms: int = 5000
    mongodb_server_selection_timeout_ms: int = 5000
    
    # Google Gemini (Premium) - Optimized for human-like responses
    gemini_api_key: str = "AIzaSyBfTE4ivJFNh3UR2MUS2zogOJh2JU4SORI"
    gemini_model: str = "gemini-2.5-flash-lite"    # Fast base detection model
    gemini_max_retries: int = 3
    gemini_timeout: int = 12                       # Internal limit of 10-15s
    gemini_context_messages: int = 30              # Full conversation history
    gemini_max_output_tokens: int = 1000
    gemini_temperature: float = 0.95
    
    # GUVI Callback
    guvi_callback_url: str = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"
    
    # Performance
    max_connections: int = 100
    connection_timeout: int = 180
    request_timeout: int = 180
    enable_caching: bool = False
    cache_ttl: int = 300
    inactivity_threshold_minutes: float = 0.5  # 30 seconds for faster e2e testing
    
    # Security
    cors_origins: List[str] = ["*"]
    rate_limit_per_minute: int = 100
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


settings = Settings()
