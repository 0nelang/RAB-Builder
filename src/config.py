from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )

    model_api_key : str

    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    vision_model: str = "qwen/qwen2.5-vl-72b-instruct"
    text_model: str = "deepseek/deepseek-r1"

    #App Settings
    app_name: str = "RAB Builder AI"
    db_path: str = "data/rab.db"
    max_image_size_px: int = 1568
    max_retry_attempts: int = 2
    llm_temperature: float = 0.0

settings = Settings()