import csv
import math
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from config import API_KEY

# Hydra AI Trader: загрузка минутной истории Twelve Data с продолжением назад.
# Уже сохранённые свечи не удаляются; прогресс записывается после каждой порции.

SYMBOL = "EUR/USD"
INTERVAL = "1min"
TARGET_CANDLES = 30_000
CHUNK_SIZE = 50
PAUSE_BETWEEN_REQUESTS = 15
MAX_REQUESTS_PER_RUN = 600
MAX_RETRIES = 3

PROGRESS_FILE = Path("eurusd_history_extended_progress.csv")
FINAL_FILE = Path("eurusd_history_extended.csv")
API_URL = "https://api.twelvedata.com/time_series"
FIELDS = ["datetime", "open", "high", "low", "close"]


def parse_timestamp(value):
    """Parse Twelve Data UTC timestamps into aware datetime objects."""
    dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    return dt.replace(tzinfo=timezone.utc)


def valid_candle(candle):
    """Return a normalized candle only when timestamp and OHLC are valid."""
    stamp = candle.get("datetime")
    if not stamp:
        return None

    try:
        parse_timestamp(stamp)
        prices = {
            name: float(candle[name])
            for name in ("open", "high", "low", "close")
        }
    except (KeyError, TypeError, ValueError):
        return None

    if not all(math.isfinite(value) and value > 0 for value in prices.values()):
        return None

    open_price = prices["open"]
    high_price = prices["high"]
    low_price = prices["low"]
    close_price = prices["close"]

    if high_price < max(open_price, close_price, low_price):
        return None
    if low_price > min(open_price, close_price, high_price):
        return None

    return {
        "datetime": stamp,
        **{name: format(value, ".10g") for name, value in prices.items()},
    }


def read_existing_rows():
    rows_by_time = {}
    if not PROGRESS_FILE.exists():
        return rows_by_time

    with PROGRESS_FILE.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        for row in reader:
            normalized = valid_candle(row)
            if normalized:
                rows_by_time[normalized["datetime"]] = normalized

    return rows_by_time


def save_rows(rows_by_time, destination):
    """Atomically write all known candles in chronological order."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path = destination.with_suffix(destination.suffix + ".tmp")
    ordered = sorted(rows_by_time.values(), key=lambda row: row["datetime"])

    with temp_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(ordered)

    temp_path.replace(destination)


def request_chunk(end_dt):
    start_dt = end_dt - timedelta(minutes=CHUNK_SIZE - 1)
    params = {
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "start_date": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "end_date": end_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "order": "DESC",
        "timezone": "UTC",
        "apikey": API_KEY,
        "format": "JSON",
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(API_URL, params=params, timeout=30)

            if response.status_code == 429:
                wait_seconds = 60 * attempt
                print(f"Лимит запросов (429). Пауза {wait_seconds} сек.")
                time.sleep(wait_seconds)
                continue

            response.raise_for_status()
            payload = response.json()

            if "values" not in payload:
                message = payload.get("message") or payload.get("code") or str(payload)
                print(f"Twelve Data не вернул свечи: {message}")
                return None

            return payload["values"]

        except (requests.RequestException, ValueError) as exc:
            if attempt == MAX_RETRIES:
                print(f"Запрос не выполнен после {MAX_RETRIES} попыток: {exc}")
                return None

            wait_seconds = 10 * attempt
            print(f"Ошибка запроса: {exc}. Повтор через {wait_seconds} сек.")
            time.sleep(wait_seconds)

    return None


def main():
    if not API_KEY:
        print(
            "API-ключ не задан. Установи TWELVE_DATA_API_KEY "
            "в переменных окружения и перезапусти терминал."
        )
        return

    rows_by_time = read_existing_rows()
    print(f"Корректных свечей уже сохранено: {len(rows_by_time)}")

    if len(rows_by_time) >= TARGET_CANDLES:
        save_rows(rows_by_time, FINAL_FILE)
        print(f"Цель уже достигнута. Итоговый файл: {FINAL_FILE.resolve()}")
        return

    # Продолжаем историю в прошлое от самой старой сохранённой свечи.
    if rows_by_time:
        oldest_stamp = min(rows_by_time)
        end_dt = parse_timestamp(oldest_stamp) - timedelta(minutes=1)
        print(f"Продолжаем назад от {oldest_stamp} UTC.")
    else:
        end_dt = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        print("Файл прогресса не найден: начинаем с текущей минуты UTC.")

    requests_made = 0
    consecutive_empty = 0
    max_consecutive_empty = 100  # запас для выходных и длинных рыночных пауз

    while len(rows_by_time) < TARGET_CANDLES:
        if requests_made >= MAX_REQUESTS_PER_RUN:
            print("Достигнут лимит запросов за запуск. Сохраняем прогресс.")
            break

        requests_made += 1
        start_dt = end_dt - timedelta(minutes=CHUNK_SIZE - 1)
        print(
            f"Запрос {requests_made}/{MAX_REQUESTS_PER_RUN}: "
            f"{start_dt:%Y-%m-%d %H:%M} — {end_dt:%Y-%m-%d %H:%M} UTC"
        )

        values = request_chunk(end_dt)
        if values is None:
            print("Получена ошибка API. Останавливаемся, сохранив прогресс.")
            break

        if not values:
            consecutive_empty += 1
            print(f"Пустая порция ({consecutive_empty}/{max_consecutive_empty}).")
            if consecutive_empty >= max_consecutive_empty:
                print("Слишком много пустых порций подряд — остановка.")
                break

            end_dt = start_dt - timedelta(minutes=1)
            time.sleep(PAUSE_BETWEEN_REQUESTS)
            continue

        consecutive_empty = 0
        valid_stamps = []
        added = 0

        for raw_candle in values:
            candle = valid_candle(raw_candle)
            if candle is None:
                continue

            stamp = candle["datetime"]
            valid_stamps.append(stamp)
            if stamp not in rows_by_time:
                rows_by_time[stamp] = candle
                added += 1

        save_rows(rows_by_time, PROGRESS_FILE)
        print(
            f"Свечей в ответе: {len(values)}; новых корректных: {added}; "
            f"всего: {len(rows_by_time)}/{TARGET_CANDLES}."
        )

        if not valid_stamps:
            print("В ответе нет корректных свечей. Останавливаемся.")
            break

        # Берём фактическую самую старую свечу ответа, чтобы не пропустить
        # данные, если API вернул меньше CHUNK_SIZE строк.
        oldest_returned = min(parse_timestamp(stamp) for stamp in valid_stamps)
        next_end = oldest_returned - timedelta(minutes=1)

        if next_end >= end_dt:
            print("Временная граница API не сдвинулась назад. Остановка.")
            break

        end_dt = next_end
        if len(rows_by_time) < TARGET_CANDLES:
            time.sleep(PAUSE_BETWEEN_REQUESTS)

    save_rows(rows_by_time, PROGRESS_FILE)

    if len(rows_by_time) >= TARGET_CANDLES:
        save_rows(rows_by_time, FINAL_FILE)
        print(f"ГОТОВО: {len(rows_by_time)} свечей.")
        print(f"Итоговый файл: {FINAL_FILE.resolve()}")
    else:
        print(f"Сохранено {len(rows_by_time)} свечей из {TARGET_CANDLES}.")
        print("При следующем запуске загрузка продолжится от самой старой свечи.")
        print(f"Файл прогресса: {PROGRESS_FILE.resolve()}")


if __name__ == "__main__":
    main()
