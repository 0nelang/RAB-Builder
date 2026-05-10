"""
Smoke test: cek koneksi ke OpenRouter untuk kedua model.
Run: uv run python scripts/test_llm.py
"""
from __future__ import annotations
import sys
from pathlib import Path

# Biar bisa import src/ dari root
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings
from src.services.llm_client import get_llm_client


def test_text_model() -> None:
    print(f"\n🧪 Testing text model: {settings.text_model}")
    client = get_llm_client()
    response = client.chat.completions.create(
        model=settings.text_model,
        messages=[
            {"role": "user", "content": "Reply with exactly: 'OK'"}
        ],
        max_tokens=20,
        temperature=0,
    )
    content = response.choices[0].message.content
    print(f"✅ Response: {content!r}")
    print(f"   Tokens used: {response.usage.total_tokens}")


def test_vision_model() -> None:
    print(f"\n🧪 Testing vision model: {settings.vision_model}")
    client = get_llm_client()
    # Test pakai gambar publik kecil dari placeholder service
    response = client.chat.completions.create(
        model=settings.vision_model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What color is this image? Reply in 1 word."},
                    {
                        "type": "image_url",
                        "image_url": {"url": "https://placehold.co/100x100/FF0000/FF0000.png"},
                    },
                ],
            }
        ],
        max_tokens=20,
        temperature=0,
    )
    content = response.choices[0].message.content
    print(f"✅ Response: {content!r}")
    print(f"   Tokens used: {response.usage.total_tokens}")


if __name__ == "__main__":
    print(f"🔧 Base URL: {settings.openrouter_base_url}")
    print(f"🔑 API Key: {settings.model_api_key[:12]}...")

    try:
        test_text_model()
        test_vision_model()
        print("\n🎉 Semua test passed! Siap lanjut Hari 2.")
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        sys.exit(1)