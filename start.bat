@echo off
echo Запуск Lemon Loyalty Bot локально...
echo.

REM Перевірка наявності Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Помилка: Python не знайдено. Встановіть Python 3.11+
    pause
    exit /b 1
)

REM Встановлення залежностей
echo Встановлення залежностей...
pip install -r requirements.txt

REM Запуск бота
echo.
echo Запуск бота...
python bot.py

pause
