"""FastAPI-застосунок: API та статичний фронтенд."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import assistant
from .config import settings
from .games import game_choices
from .models import AskRequest, AskResponse
from .providers import ProviderError

app = FastAPI(title="Game AI Assistant", version="1.0")

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "default_provider": settings.provider,
        "groq_key": bool(settings.groq_api_key),
        "openrouter_key": bool(settings.openrouter_api_key),
    }


@app.get("/api/games")
async def games():
    return {"games": game_choices(), "default_provider": settings.provider}


@app.post("/api/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    if not req.question and not req.image:
        return JSONResponse(
            status_code=400,
            content={"error": "Поставте питання або додайте скріншот."},
        )
    try:
        result = await assistant.ask(
            question=req.question,
            game=req.game,
            image=req.image,
            provider=req.provider,
            api_key=req.api_key,
        )
        return result
    except ProviderError as e:
        return JSONResponse(status_code=502, content={"error": str(e)})
    except Exception as e:  # noqa: BLE001
        return JSONResponse(status_code=500, content={"error": f"Внутрішня помилка: {e}"})


# Статичний фронтенд монтуємо ОСТАННІМ, щоб /api/* мали пріоритет
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
