"""Єдиний клієнт для безкоштовних провайдерів ШІ (Groq та OpenRouter).

Обидва провайдери сумісні з форматом OpenAI Chat Completions, тому
використовується одна функція. Зображення передаються як data-URL у полі
image_url (підтримується vision-моделями обох провайдерів).
"""
import httpx

from .config import settings

PROVIDERS = {
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "text_model": lambda: settings.groq_text_model,
        "vision_model": lambda: settings.groq_vision_model,
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "text_model": lambda: settings.openrouter_text_model,
        "vision_model": lambda: settings.openrouter_vision_model,
    },
}


class ProviderError(Exception):
    pass


def resolve_model(provider: str, has_image: bool, override: str | None = None) -> str:
    if override:
        return override
    cfg = PROVIDERS[provider]
    return cfg["vision_model"]() if has_image else cfg["text_model"]()


async def chat(
    messages: list[dict],
    *,
    provider: str | None = None,
    api_key: str | None = None,
    has_image: bool = False,
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 1200,
) -> str:
    provider = (provider or settings.provider).lower()
    if provider not in PROVIDERS:
        raise ProviderError(f"Невідомий провайдер: {provider}")

    key = (api_key or settings.key_for(provider)).strip()
    if not key:
        raise ProviderError(
            f"Не вказано ключ API для провайдера «{provider}». "
            f"Додайте його в .env або в налаштуваннях інтерфейсу."
        )

    cfg = PROVIDERS[provider]
    model = resolve_model(provider, has_image, model)

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    if provider == "openrouter":
        # Рекомендовані OpenRouter заголовки
        headers["HTTP-Referer"] = "http://localhost"
        headers["X-Title"] = "Game AI Assistant"

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
        try:
            r = await client.post(cfg["url"], headers=headers, json=payload)
        except httpx.RequestError as e:
            raise ProviderError(f"Помилка мережі під час звернення до {provider}: {e}") from e

    if r.status_code != 200:
        detail = r.text[:500]
        raise ProviderError(
            f"Провайдер {provider} повернув помилку {r.status_code} (модель {model}): {detail}"
        )

    data = r.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise ProviderError(f"Несподівана відповідь від {provider}: {str(data)[:300]}") from e
