"""
Configuration settings for Stock Market Prediction App
"""
import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """Application settings"""
    
    # API Keys
    alpha_vantage_api_key: str = Field(..., env="ALPHA_VANTAGE_API_KEY")
    yahoo_finance_api_key: str = Field(default="", env="YAHOO_FINANCE_API_KEY")
    
    # Database Configuration
    mongodb_connection_string: str = Field(..., env="MONGODB_CONNECTION_STRING")
    mongodb_database_name: str = Field(default="stock_prediction_app", env="MONGODB_DATABASE_NAME")
    
    postgres_host: str = Field(default="localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")
    postgres_database: str = Field(default="stock_prediction", env="POSTGRES_DATABASE")
    postgres_username: str = Field(..., env="POSTGRES_USERNAME")
    postgres_password: str = Field(..., env="POSTGRES_PASSWORD")
    
    # Application Settings
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    debug_mode: bool = Field(default=True, env="DEBUG_MODE")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Model Configuration
    model_save_path: str = Field(default="./models/saved/", env="MODEL_SAVE_PATH")
    data_cache_path: str = Field(default="./data/cache/", env="DATA_CACHE_PATH")
    prediction_cache_hours: int = Field(default=1, env="PREDICTION_CACHE_HOURS")
    
    # Rate Limiting
    alpha_vantage_rate_limit: int = Field(default=5, env="ALPHA_VANTAGE_RATE_LIMIT")
    yahoo_finance_rate_limit: int = Field(default=2000, env="YAHOO_FINANCE_RATE_LIMIT")
    
    # Security
    secret_key: str = Field(..., env="SECRET_KEY")
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "https://yourdomain.vercel.app"],
        env="CORS_ORIGINS"
    )
    
    @property
    def postgres_url(self) -> str:
        """Generate PostgreSQL connection URL"""
        return f"postgresql://{self.postgres_username}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()
