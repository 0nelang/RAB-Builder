from __future__ import annotations

import io

from src.models import HousePlanParsed
from src.config import Settings
from src.services.llm_client import get_llm_client

from PIL import Image

def compress_image(image_bytes: bytes, max_size: int | None = None) -> bytes :
    max_size = max_size or Settings.max_image_size_px
    img = Image.open(io.BytesIO(image_bytes))

    if img.mode != 'RGB':
        img = img.convert('RGB')

    if max(img.size) > max_size:
        img.thumbnail((max_size,max_size), Image.Resampling.LANCZOS)

    out = io.BytesIO()
    img.save(out, format='JPEG', quality=85, optimize=True)
    return out.getvalue()
    
