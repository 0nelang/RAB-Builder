from __future__ import annotations

import base64
import sys
import io
import re
import json
import logging

from pathlib import Path
from pydantic import ValidationError
from src.services.llm_client import get_llm_client
from PIL import Image

sys.path.insert(0,str(Path(__file__).parent.parent.parent))
from src.models import HousePlanParsed
from src.config import settings


logger = logging.getLogger(__name__)
PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "vision_instruction.md"

class VisionParseError(Exception):
    """Raised ketika parsing denah gagal setelah retry."""

def compress_image(image_bytes: bytes, max_size: int | None = None) -> bytes :
    max_size = max_size or settings.max_image_size_px
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode != 'RGB':
        img = img.convert('RGB')

    if max(img.size) > max_size:
        img.thumbnail((max_size,max_size), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    img.save(out, format='JPEG', quality=85, optimize=True)
    return out.getvalue()
    
def img_to_base64_url(img_bytes: bytes, mime_type: str = 'image/jpeg') -> str:
    b64 = base64.b64encode(img_bytes).decode('utf-8')

    return f"data:{mime_type};base64,{b64}"

def _load_prompt() -> str:
    if not PROMPT_PATH.exists():
        raise FileNotFoundError(f"Prompt file tidak ditemukan: {PROMPT_PATH}")
    return PROMPT_PATH.read_text(encoding="utf-8")

def _clean_llm_output(raw:str) -> str:
    cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
 
    # Strip markdown code fence
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip())

    return cleaned.strip()

def _call_vision_model(img_url: str, prompt: str, temp: float) -> str:
    client = get_llm_client()
    response = client.chat.completions.create(
        model=settings.vision_model,
        temperature=temp,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                    "type": "image_url",
                    "image_url": {"url": img_url, "detail": "high"} 
                    }
                ]
            }
        ]
    )
    content = response.choices[0].message.content
    if not content:
        raise VisionParseError("LLM Mengembalikan response kosong")
    return content

def _parse_response(raw:str) -> HousePlanParsed:
    cleaned = _clean_llm_output(raw)
    print("--- parse response ---")
    print(cleaned)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.warning("JSON decode error: %s. Raw (first 500 chars): %s", e, cleaned[:500])
        raise VisionParseError(f"Output LLM bukan JSON valid: {e}") from e
    
    try:
        return HousePlanParsed.model_validate(data)
    except ValidationError as e:
        logger.warning("Pydantic validation error: %s", e)
        raise VisionParseError(f"Schema tidak sesuai: {e}") from e
    
def hause_plan_result(img_bytes: bytes) -> HousePlanParsed:
    compressed_img = compress_image(img_bytes)
    data_url = img_to_base64_url(compressed_img)
    prompt = _load_prompt()

    last_error: Exception | None = None

    for attempt in range(settings.max_retry_attempts + 1):
        temp = settings.llm_temperature + (0.3 * attempt)

        logger.info(
            "Vision parse attempt %d/%d (temp=%.2f)",
            attempt + 1,
            settings.max_retry_attempts + 1,
            temp,
        )

        try:
            raw = _call_vision_model(data_url,prompt, temp)
            result = _parse_response(raw)
            logger.info(
                "Vision parse berhasil: %d ruangan, %d warnings",
                len(result.rooms),
                len(result.warning),
            )
            return result
        except VisionParseError as e:
            last_error = e
            logger.warning("Attempt %d gagal: %s", attempt + 1, e)
            continue
        except Exception as e:
            # Network error, API error, dll — jangan retry, langsung raise
            logger.error("Error tak terduga saat call LLM: %s", e)
            raise VisionParseError(f"Gagal call LLM: {e}") from e
        
    raise VisionParseError(
    f"Parsing gagal setelah {settings.max_retry_attempts + 1} percobaan. "
    f"Last error: {last_error}"
    )