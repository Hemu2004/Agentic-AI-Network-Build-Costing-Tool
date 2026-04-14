"""Application settings."""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "fttp_estimator"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    host: str = "0.0.0.0"
    port: int = 8000
    google_maps_api_key: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
