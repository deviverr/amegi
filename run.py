"""Точка входу: запуск веб-сервера помічника."""
import os

import uvicorn
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    print(f"\n  Ігровий ШІ-помічник запущено:  http://{host}:{port}\n")
    uvicorn.run("backend.main:app", host=host, port=port, reload=False)
