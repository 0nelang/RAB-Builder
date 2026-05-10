from __future__ import annotations
from openai import OpenAI
from src.config import settings

def get_llm_client() -> OpenAI:
    return OpenAI(
        api_key=settings.model_api_key,
        base_url=settings.openrouter_base_url,
        default_headers={
            'X-Title' : settings.app_name,
        }
    )