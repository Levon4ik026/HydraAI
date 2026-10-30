@echo off
chcp 65001 >nul
cd /d C:\HydraAI

call .venv\Scripts\activate.bat

if not exist observer_data mkdir observer_data

echo ==========================================
echo HYDRA AI TRADER
echo Сбор EUR/USD каждые 5 минут
echo Анализ каждые 15 минут
echo Без торговых сигналов
echo Для остановки нажми Ctrl+C
echo ==========================================

start "Hydra Analyzer" /min cmd /c "cd /d C:\HydraAI && call .venv\Scripts\activate.bat && python hydra_analyzer_loop.py"

python hydra_market_observer.py





