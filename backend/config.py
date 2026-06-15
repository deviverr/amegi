"""Налаштування застосунку, читаються зі змінних середовища / .env."""
import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Який провайдер використовувати за замовчуванням
    provider: str = os.getenv("AI_PROVIDER", "groq").strip().lower()

    # Ключі API
    groq_api_key: str = os.getenv("GROQ_API_KEY", "").strip()
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "").strip()

    # Моделі
    groq_text_model: str = os.getenv("GROQ_TEXT_MODEL", "llama-3.3-70b-versatile")
    groq_vision_model: str = os.getenv(
        "GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct"
    )
    openrouter_text_model: str = os.getenv(
        "OPENROUTER_TEXT_MODEL", "meta-llama/llama-3.3-70b-instruct:free"
    )
    openrouter_vision_model: str = os.getenv(
        "OPENROUTER_VISION_MODEL", "meta-llama/llama-4-scout:free"
    )

    http_timeout: float = float(os.getenv("HTTP_TIMEOUT", "60"))
    wiki_top_k: int = int(os.getenv("WIKI_TOP_K", "4"))

    def key_for(self, provider: str) -> str:
        return self.groq_api_key if provider == "groq" else self.openrouter_api_key


settings = Settings()
