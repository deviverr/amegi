"""Отримання перевіреної інформації з ігрових вікі через MediaWiki API.

Чому action=parse, а не prop=extracts: розширення TextExtracts встановлене не
на всіх вікі (Terraria wiki.gg, Fandom тощо його не мають). Натомість
action=parse&section=0 повертає HTML вступного розділу на будь-якій MediaWiki —
ми очищаємо його до простого тексту. Канонічні посилання беремо з prop=info
(inprop=url), тож URL завжди коректні.
"""
import asyncio
import html
import re

import httpx

from .games import GAMES

# Чесний описовий User-Agent. Вікі на wiki.gg та Fandom (а надто minecraft.wiki
# від Weird Gloop) блокують підроблені «браузерні» UA, але пропускають
# зрозумілих ботів із контактом — згідно з їхніми правилами доступу.
BROWSER_HEADERS = {
    "User-Agent": (
        "GameAI-Assistant/1.0 (Ukrainian gaming helper; educational project; "
        "+https://github.com/local/game-ai-assistant)"
    ),
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9,uk;q=0.8",
}

MAX_EXTRACT_CHARS = 1500


def _clean_html(raw: str) -> str:
    """Перетворити HTML вступного розділу статті на чистий текст."""
    if not raw:
        return ""
    # Прибрати важкі/шумні блоки повністю
    raw = re.sub(r"(?is)<(script|style|table|sup|figure)[^>]*>.*?</\1>", " ", raw)
    # Прибрати решту тегів
    text = re.sub(r"(?s)<[^>]+>", " ", raw)
    text = html.unescape(text)
    text = text.replace("[edit]", "").replace("[ edit ]", "")
    text = re.sub(r"\[\d+\]", "", text)          # маркери виносок
    text = re.sub(r"[ \t  ]+", " ", text)
    text = re.sub(r"\s*\n\s*", "\n", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


async def _search(client: httpx.AsyncClient, api: str, query: str) -> list[dict]:
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": 3,
        "srprop": "snippet",
        "format": "json",
        "formatversion": "2",
    }
    try:
        r = await client.get(api, params=params)
        if "json" not in r.headers.get("content-type", ""):
            return []
        items = r.json().get("query", {}).get("search", [])
        return [
            {"title": it["title"], "snippet": _clean_html(it.get("snippet", ""))}
            for it in items
        ]
    except Exception:
        return []


async def _fetch_urls(client: httpx.AsyncClient, api: str, titles: list[str]) -> dict[str, str]:
    if not titles:
        return {}
    params = {
        "action": "query",
        "prop": "info",
        "inprop": "url",
        "titles": "|".join(titles),
        "redirects": "1",
        "format": "json",
        "formatversion": "2",
    }
    try:
        r = await client.get(api, params=params)
        pages = r.json().get("query", {}).get("pages", [])
        return {
            p["title"].lower(): p.get("fullurl", "")
            for p in pages
            if not p.get("missing")
        }
    except Exception:
        return {}


async def _fetch_intro(client: httpx.AsyncClient, api: str, title: str) -> tuple[str, str]:
    """Повертає (canonical_title, clean_text) для вступного розділу статті."""
    params = {
        "action": "parse",
        "page": title,
        "prop": "text",
        "section": "0",
        "redirects": "1",
        "disablelimitreport": "1",
        "disableeditsection": "1",
        "format": "json",
        "formatversion": "2",
    }
    try:
        r = await client.get(api, params=params)
        if "json" not in r.headers.get("content-type", ""):
            return title, ""
        parse = r.json().get("parse", {})
        return parse.get("title", title), _clean_html(parse.get("text", ""))
    except Exception:
        return title, ""


async def gather_context(game_id: str, queries: list[str], top_k: int) -> list[dict]:
    """До top_k унікальних статей вікі з чистим текстом і коректними URL."""
    game = GAMES.get(game_id)
    if not game or not queries:
        return []

    api = game["api"]
    async with httpx.AsyncClient(
        timeout=20, headers=BROWSER_HEADERS, follow_redirects=True
    ) as client:
        # 1) Паралельний пошук
        batches = await asyncio.gather(*[_search(client, api, q) for q in queries if q.strip()])

        # 2) Дедуплікація заголовків зі збереженням порядку; запам'ятати snippet
        seen, titles, snippets = set(), [], {}
        for batch in batches:
            for item in batch:
                key = item["title"].lower()
                if key not in seen:
                    seen.add(key)
                    titles.append(item["title"])
                    snippets[key] = item["snippet"]

        if not titles:
            return []

        candidates = titles[: top_k + 1]

        # 3) URL + вступні тексти паралельно
        urls_task = _fetch_urls(client, api, candidates)
        intros_task = asyncio.gather(*[_fetch_intro(client, api, t) for t in candidates])
        urls, intros = await asyncio.gather(urls_task, intros_task)

    pages = []
    for resolved_title, text in intros:
        key = resolved_title.lower()
        # Якщо вступ порожній — взяти snippet із пошуку як резерв
        if not text:
            text = snippets.get(key) or next(
                (snippets[k] for k in snippets if k in key or key in k), ""
            )
        if not text:
            continue
        pages.append(
            {
                "title": resolved_title,
                "extract": text[:MAX_EXTRACT_CHARS],
                "url": urls.get(key, ""),
            }
        )
        if len(pages) >= top_k:
            break

    return pages
