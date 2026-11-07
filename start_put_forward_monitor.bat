@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "DATA_FILE=C:\HydraAI_Desktop\observer_data\eurusd_guest_candles.csv"

if not exist "%DATA_FILE%" (
    echo [ОШИБКА] Не найден файл гостевого потока:
    echo %DATA_FILE%
    echo Проверь, что сборщик HydraAI Desktop уже запускался.
    pause
    exit /b 1
)

if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)

echo ============================================================
echo HYDRA — FROZEN PUT FORWARD MONITOR
echo Исследовательский режим. Торговые операции отключены.
echo Источник: %DATA_FILE%
echo Для остановки нажми Ctrl+C.
echo ============================================================

python "research\watch_frozen_put_candidate.py" --data "%DATA_FILE%"
echo.
echo Монитор остановлен.
pause
