@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist venv (
    echo [setup] Створення віртуального середовища...
    py -m venv venv 2>nul || python -m venv venv
)

call venv\Scripts\activate.bat

echo [setup] Встановлення залежностей...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

if not exist .env (
    echo [setup] Створюю .env з .env.example - не забудьте додати ключ API!
    copy .env.example .env >nul
)

python run.py
pause
