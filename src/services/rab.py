"""RAB generation service.

Pipeline: build context → call text LLM → clean output → validate Pydantic → retry on failure.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import ValidationError

from src.config import settings
from src.models import ParsedRoom, RABItem, RABResult
from src.services.llm_client import get_llm_client
from src.services.vision import _clean_llm_output  # reuse cleanup logic

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "rab_generation.md"


class RABGenerationError(Exception):
    """Raised when RAB generation fails after all retries."""


def _load_prompt() -> str:
    """Load RAB generation system prompt from file."""
    if not PROMPT_PATH.exists():
        raise FileNotFoundError(f"Prompt file tidak ditemukan: {PROMPT_PATH}")
    return PROMPT_PATH.read_text(encoding="utf-8")


def _build_user_message(rooms: list[ParsedRoom], lokasi: str) -> str:
    """Format rooms + lokasi jadi user message yang readable buat LLM."""
    rooms_lines = [
        f"- {r.name}: {r.length}m × {r.width}m (luas {r.area:.2f} m²)"
        for r in rooms
    ]
    rooms_block = "\n".join(rooms_lines)

    return (
        f"**Lokasi proyek**: {lokasi}\n\n"
        f"**Daftar ruangan**:\n{rooms_block}\n\n"
        "Generate RAB lengkap untuk semua ruangan di atas. "
        "Output **HANYA JSON** sesuai schema yang sudah dijelaskan."
    )


def _parse_response(content: str) -> list[RABItem]:
    """Parse cleaned JSON content → list of validated RABItem.

    Raises:
        RABGenerationError: kalau JSON invalid, key 'items' hilang, atau item invalid.
    """
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise RABGenerationError(f"Output LLM bukan JSON valid: {e}") from e

    if not isinstance(data, dict):
        raise RABGenerationError(
            f"Output LLM harus berupa object, dapet: {type(data).__name__}"
        )

    items_raw = data.get("items")
    if items_raw is None:
        raise RABGenerationError(
            f"Output LLM tidak punya key 'items'. Keys yang ada: {list(data.keys())}"
        )
    if not isinstance(items_raw, list):
        raise RABGenerationError(
            f"'items' harus berupa array, dapet: {type(items_raw).__name__}"
        )

    try:
        return [RABItem(**item) for item in items_raw]
    except ValidationError as e:
        raise RABGenerationError(f"RABItem validation error: {e}") from e


def generate_rab(
    rooms: list[ParsedRoom],
    lokasi: str,
    project_name: str,
) -> RABResult:
    """Generate RAB dari list ruangan + lokasi proyek.

    Args:
        rooms: hasil parsing denah (dari vision service).
        lokasi: nama kota/kabupaten — dipakai LLM untuk estimasi harga regional.
        project_name: nama proyek (dari input user di halaman upload).

    Returns:
        RABResult lengkap dengan items hasil generate.

    Raises:
        ValueError: kalau rooms kosong.
        RABGenerationError: kalau semua retry attempt gagal.
    """
    if not rooms:
        raise ValueError("Tidak bisa generate RAB: list rooms kosong")

    client = get_llm_client()
    system_prompt = _load_prompt()
    user_message = _build_user_message(rooms, lokasi)

    last_error: Exception | None = None

    for attempt in range(settings.max_retry_attempts):
        temperature = settings.llm_temperature + (attempt * 0.3)
        logger.info(
            "RAB generation attempt %d/%d (model=%s, temp=%.2f)",
            attempt + 1,
            settings.max_retry_attempts,
            settings.text_model,
            temperature,
        )

        try:
            response = client.chat.completions.create(
                model=settings.text_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
            )

            raw_content = response.choices[0].message.content
            if not raw_content:
                raise RABGenerationError("Response LLM kosong")

            cleaned = _clean_llm_output(raw_content)
            logger.debug("Cleaned LLM output (preview): %s", cleaned[:200])

            items = _parse_response(cleaned)

            # Final validation lewat RABResult constructor
            # (akan raise ValidationError kalau items kosong)
            return RABResult(
                project_name=project_name,
                location=lokasi,
                items=items,
            )

        except (RABGenerationError, ValidationError) as e:
            logger.warning("Attempt %d gagal: %s", attempt + 1, e)
            last_error = e
            continue

    raise RABGenerationError(
        f"RAB generation gagal setelah {settings.max_retry_attempts} attempt. "
        f"Last error: {last_error}"
    )