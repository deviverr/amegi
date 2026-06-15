"""Pydantic-моделі запитів та відповідей API."""
from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(default="", description="Текстове питання користувача")
    game: str = Field(default="auto", description="ID гри або 'auto'")
    image: str | None = Field(default=None, description="Скріншот як data-URL (base64)")
    provider: str | None = Field(default=None, description="groq | openrouter")
    api_key: str | None = Field(default=None, description="Тимчасовий ключ з інтерфейсу")


class Source(BaseModel):
    n: int
    title: str
    url: str


class AskResponse(BaseModel):
    game: str
    game_name: str
    answer: str
    sources: list[Source]
    queries: list[str]
    provider: str
    used_image: bool
