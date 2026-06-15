"""Оркестрація: визначення гри -> пошук у вікі -> обґрунтована відповідь.

Логіка RAG (Retrieval-Augmented Generation):
1. Планувальник: за питанням (та скріншотом) визначає гру і формує
   англомовні пошукові запити для вікі.
2. Пошук: бере перевірені витяги з офіційної вікі гри.
3. Відповідач: генерує відповідь українською, спираючись ТІЛЬКИ на знайдені
   факти, з посиланнями на джерела [1], [2] ...
"""
import json

from . import providers, wiki
from .config import settings
from .games import GAMES, detect_game_by_keywords

VALID_GAME_IDS = list(GAMES.keys())


def _image_part(image: str | None) -> list:
    if not image:
        return []
    return [{"type": "image_url", "image_url": {"url": image}}]


def _extract_json(text: str) -> dict:
    """Витягнути JSON-об'єкт навіть якщо модель обгорнула його в ```json ...```."""
    text = text.strip()
    if "```" in text:
        # прибрати огорожі коду
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                text = part
                break
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    return json.loads(text)


async def _plan(question: str, game: str, image: str | None, provider, api_key) -> dict:
    """Визначити гру та сформувати пошукові запити англійською."""
    games_desc = "\n".join(f'  - "{gid}": {g["name"]}' for gid, g in GAMES.items())
    forced = "auto" if game not in VALID_GAME_IDS else game

    system = (
        "Ти — аналізатор запитів для ігрового асистента. Доступні ігри:\n"
        f"{games_desc}\n\n"
        "Завдання: визнач, про яку гру йдеться, і сформуй 1–3 КОРОТКІ пошукові "
        "запити АНГЛІЙСЬКОЮ мовою для пошуку у вікі цієї гри (назви предметів, "
        "механік, босів, персонажів тощо). Якщо надано скріншот — врахуй те, що "
        "на ньому видно.\n"
        'Поверни ЛИШЕ JSON без пояснень у форматі: '
        '{"game": "<id>", "queries": ["...", "..."]}.'
    )
    if forced != "auto":
        system += f'\nГру вже обрано користувачем: "{forced}" — використай саме її.'

    user_content = [{"type": "text", "text": f"Питання користувача: {question or '(лише скріншот)'}"}]
    user_content += _image_part(image)

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]

    raw = await providers.chat(
        messages,
        provider=provider,
        api_key=api_key,
        has_image=bool(image),
        temperature=0.0,
        max_tokens=300,
    )

    try:
        plan = _extract_json(raw)
    except Exception:
        plan = {}

    game_id = plan.get("game") if plan.get("game") in VALID_GAME_IDS else None
    if forced != "auto":
        game_id = forced
    if not game_id:
        game_id = detect_game_by_keywords(question) or "minecraft"

    queries = plan.get("queries") or []
    queries = [q for q in queries if isinstance(q, str) and q.strip()][:3]
    if not queries and question:
        queries = [question]

    return {"game": game_id, "queries": queries}


def _build_context_block(pages: list[dict]) -> tuple[str, list[dict]]:
    """Сформувати текстовий блок джерел і структурований список для відповіді."""
    lines, sources = [], []
    for i, p in enumerate(pages, start=1):
        lines.append(f"[{i}] {p['title']}\n{p['extract']}\nДжерело: {p['url']}")
        sources.append({"n": i, "title": p["title"], "url": p["url"]})
    return "\n\n".join(lines), sources


async def _answer(question, game_id, image, context_block, has_context, provider, api_key) -> str:
    game = GAMES[game_id]
    system = (
        "Ти — універсальний ШІ-помічник для відеоігор. Завжди відповідай "
        "УКРАЇНСЬКОЮ мовою, дружньо й по суті.\n"
        f"Поточна гра: {game['name']}.\n\n"
        "ПРАВИЛА:\n"
        "1. Як перевірені факти використовуй ТІЛЬКИ наведену нижче інформацію з "
        "офіційної вікі. Не вигадуй чисел, рецептів чи механік.\n"
        "2. Посилайся на джерела в тексті позначками [1], [2] відповідно до "
        "номерів у блоці «ДЖЕРЕЛА».\n"
        "3. Якщо наданої інформації недостатньо — чесно про це скажи і дай "
        "лише загальну пораду, позначивши її як неперевірену.\n"
        "4. Якщо є скріншот — проаналізуй те, що на ньому видно, і пов'яжи з "
        "питанням.\n"
        "5. Відповідай структуровано: коротко й конкретно, за потреби списком."
    )

    if has_context:
        context_text = f"ДЖЕРЕЛА (офіційна вікі {game['wiki_name']}):\n\n{context_block}"
    else:
        context_text = (
            "ДЖЕРЕЛА: у вікі не знайдено релевантних статей. Дай обережну "
            "загальну відповідь і чітко познач, що вона не підтверджена вікі."
        )

    user_content = [
        {"type": "text", "text": f"{context_text}\n\nПИТАННЯ: {question or '(аналіз скріншота)'}"}
    ]
    user_content += _image_part(image)

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]

    return await providers.chat(
        messages,
        provider=provider,
        api_key=api_key,
        has_image=bool(image),
        temperature=0.3,
        max_tokens=1200,
    )


async def ask(question, game, image, provider, api_key) -> dict:
    provider = (provider or settings.provider).lower()

    plan = await _plan(question, game, image, provider, api_key)
    game_id = plan["game"]
    queries = plan["queries"]

    pages = await wiki.gather_context(game_id, queries, top_k=settings.wiki_top_k)
    context_block, sources = _build_context_block(pages)

    answer = await _answer(
        question, game_id, image, context_block, bool(pages), provider, api_key
    )

    return {
        "game": game_id,
        "game_name": GAMES[game_id]["name"],
        "answer": answer,
        "sources": sources,
        "queries": queries,
        "provider": provider,
        "used_image": bool(image),
    }
