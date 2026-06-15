"""Реєстр підтримуваних ігор та їхніх офіційних вікі (MediaWiki API)."""

GAMES: dict[str, dict] = {
    "hoi4": {
        "name": "Hearts of Iron IV",
        "short": "HoI4",
        # Офіційна Paradox Wiki захищена JS-перевіркою (недоступна для запитів
        # сервера), тож використовуємо доступну вікі спільноти на Fandom.
        "api": "https://heartsofiron.fandom.com/api.php",
        "wiki_name": "Hearts of Iron Wiki (Fandom)",
        "keywords": [
            "hearts of iron", "hoi4", "paradox", "focus tree", "national focus",
            "division template", "template", "політична влада", "political power",
            "фокус", "дивізія", "war goal", "ідеологія",
        ],
    },
    "minecraft": {
        "name": "Minecraft",
        "short": "Minecraft",
        "api": "https://minecraft.wiki/api.php",
        "wiki_name": "Minecraft Wiki (офіційна)",
        "keywords": [
            "minecraft", "крафт", "craft", "redstone", "редстоун", "enchant",
            "зачарування", "creeper", "крипер", "nether", "незер", "village",
            "село", "biome", "біом", "блок", "block",
        ],
    },
    "terraria": {
        "name": "Terraria",
        "short": "Terraria",
        "api": "https://terraria.wiki.gg/api.php",
        "wiki_name": "Terraria Wiki (wiki.gg, офіційна)",
        "keywords": [
            "terraria", "террарія", "boss", "бос", "hardmode", "expert",
            "wall of flesh", "moon lord", "calamity", "руда", "ore", "npc",
            "pickaxe", "кирка",
        ],
    },
    "dst": {
        "name": "Don't Starve Together",
        "short": "DST",
        "api": "https://dontstarve.fandom.com/api.php",
        "wiki_name": "Don't Starve Wiki (Fandom)",
        "keywords": [
            "don't starve", "dont starve", "dst", "вілсон", "wilson", "wendy",
            "wx-78", "sanity", "розсудливість", "hunger", "голод", "winter",
            "зима", "deerclops", "крафт", "характер", "character",
        ],
    },
    "albion": {
        "name": "Albion Online",
        "short": "Albion",
        # Офіційна wiki.albiononline.com за Cloudflare (JS-перевірка),
        # тож використовуємо доступну вікі на wiki.gg.
        "api": "https://albion.wiki.gg/api.php",
        "wiki_name": "Albion Online Wiki (wiki.gg)",
        "keywords": [
            "albion", "альбіон", "gathering", "збір", "refining", "fame",
            "слава", "tier", "тір", "guild", "гільдія", "zerg", "destiny board",
            "specialization", "силвер", "silver",
        ],
    },
}


def game_choices() -> list[dict]:
    """Список ігор для фронтенду."""
    return [
        {
            "id": gid,
            "name": g["name"],
            "short": g["short"],
            "wiki": g["wiki_name"],
        }
        for gid, g in GAMES.items()
    ]


def detect_game_by_keywords(text: str) -> str | None:
    """Проста евристика визначення гри за ключовими словами в питанні."""
    if not text:
        return None
    low = text.lower()
    best_id, best_score = None, 0
    for gid, g in GAMES.items():
        score = sum(1 for kw in g["keywords"] if kw in low)
        if score > best_score:
            best_id, best_score = gid, score
    return best_id if best_score > 0 else None
