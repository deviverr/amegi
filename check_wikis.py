"""Діагностика: перевіряє доступність вікі для всіх ігор.

Запуск:  python check_wikis.py
Не потребує ключа API — лише перевіряє з'єднання та пошук у вікі.
"""
import asyncio
import sys

from backend import wiki
from backend.games import GAMES

# Приклад запиту для кожної гри (тема, яка точно є у відповідній вікі)
PROBE = {
    "hoi4": ["Germany"],
    "minecraft": ["Redstone Repeater"],
    "terraria": ["Wall of Flesh"],
    "dst": ["Wilson"],
    "albion": ["Sword"],
}


async def main() -> int:
    print("Перевірка доступності вікі...\n")
    ok = 0
    for gid, game in GAMES.items():
        queries = PROBE.get(gid, [game["name"]])
        try:
            pages = await wiki.gather_context(gid, queries, top_k=1)
        except Exception as e:  # noqa: BLE001
            print(f"  [ПОМИЛКА] {game['name']:24} -> {e}")
            continue
        if pages:
            ok += 1
            print(f"  [OK]      {game['name']:24} -> «{pages[0]['title']}»")
            print(f"            {pages[0]['url']}")
        else:
            print(f"  [ПУСТО]   {game['name']:24} -> вікі недоступна або без результату")

    print(f"\nДоступно вікі: {ok}/{len(GAMES)}")
    return 0 if ok == len(GAMES) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
