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
    
    # Google Gemini (Premium)
    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash-lite"
    gemini_max_retries: int = 3
    gemini_timeout: int = 30
    gemini_context_messages: int = 4  # Number of recent messages to include in prompt
    gemini_max_output_tokens: int = 150  # Limit output length for faster generation
    gemini_temperature: float = 0.6  # Lower temp for concise, deterministic responses
    
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
