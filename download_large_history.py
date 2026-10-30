import csv
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from config import API_KEY

# Hydra AI Trader — бережная загрузка истории Twelve Data.
# Сохраняет прогресс после каждой порции, чтобы уже загруженные данные не потерялись.

SYMBOL = "EUR/USD"
INTERVAL = "1min"
TARGET_CANDLES = 10_000
CHUNK_SIZE = 50
PAUSE_BETWEEN_REQUESTS = 15
PROGRESS_FILE = Path("eurusd_history_progress.csv")
FINAL_FILE = Path("eurusd_history_10000.csv")
API_URL = "https://api.twelvedata.com/time_series"


def parse_timestamp(value):
    """Convert Twelve Data timestamps to timezone-aware UTC datetimes."""
    dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    return dt.replace(tzinfo=timezone.utc)


def read_existing_rows():
    """Resume from the progress file if it exists; otherwise start fresh."""
    rows_by_time = {}
    if not PROGRESS_FILE.exists():
        return rows_by_time

    with PROGRESS_FILE.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        for row in reader:
            stamp = row.get("datetime")
            if stamp:
                rows_by_time[stamp] = row
    return rows_by_time


def save_rows(rows_by_time, destination):
    """Save all known candles sorted oldest to newest."""
    fields = ["datetime", "open", "high", "low", "close"]
    sorted_rows = sorted(rows_by_time.values(), key=lambda row: row["datetime"])
    with destination.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(
            {field: row.get(field, "") for field in fields}
            for row in sorted_rows
        )


def request_chunk(end_dt):
    """Request one chunk ending at end_dt, retrying gently on rate limits."""
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

    for attempt in range(1, 4):
        try:
            response = requests.get(API_URL, params=params, timeout=30)
            if response.status_code == 429:
                wait_seconds = 60 * attempt
                print(f"Лимит запросов (429). Ждём {wait_seconds} сек. "
                      f"Попытка {attempt}/3...")
                time.sleep(wait_seconds)
                continue

            response.raise_for_status()
            data = response.json()

            if "values" not in data:
                message = data.get("message", str(data))
                print(f"API не вернул свечи: {message}")
                return None

            return data["values"]

        except (requests.RequestException, ValueError) as exc:
            wait_seconds = 10 * attempt
            print(f"Ошибка запроса: {exc}. Ждём {wait_seconds} сек.")
            time.sleep(wait_seconds)

    return None


def main():
    if not API_KEY or API_KEY.strip() in {"", "YOUR_API_KEY"}:
        print("Не найден API_KEY. Проверь config.py.")
        return

    rows_by_time = read_existing_rows()
    if rows_by_time:
        print(f"Продолжаем загрузку: уже сохранено {len(rows_by_time)} свечей.")
    else:
        print("Начинаем новую загрузку истории.")

    if len(rows_by_time) >= TARGET_CANDLES:
        print(f"Уже есть не меньше {TARGET_CANDLES} свечей. "
              "Формируем итоговый файл.")
        save_rows(rows_by_time, FINAL_FILE)
        print(f"Готово: {FINAL_FILE.resolve()}")
        return

    # Start from the newest timestamp already saved, or current UTC minute.
    if rows_by_time:
        newest_stamp = max(rows_by_time)
        end_dt = parse_timestamp(newest_stamp) - timedelta(minutes=1)
    else:
        now_utc = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        end_dt = now_utc

    consecutive_empty = 0

    while len(rows_by_time) < TARGET_CANDLES:
        start_dt = end_dt - timedelta(minutes=CHUNK_SIZE - 1)
        print(f"\nЗапрашиваем период: {start_dt:%Y-%m-%d %H:%M} — "
              f"{end_dt:%Y-%m-%d %H:%M} UTC")

        values = request_chunk(end_dt)
        if values is None:
            print("Не удалось получить следующую порцию. Прогресс сохранён; "
                  "можно запустить скрипт позже для продолжения.")
            save_rows(rows_by_time, PROGRESS_FILE)
            return

        if not values:
            consecutive_empty += 1
            if consecutive_empty >= 5:
                print("Пять пустых порций подряд. Останавливаемся, чтобы "
                      "не зациклиться. Прогресс сохранён.")
                save_rows(rows_by_time, PROGRESS_FILE)
                return
            end_dt = start_dt - timedelta(minutes=1)
            time.sleep(PAUSE_BETWEEN_REQUESTS)
            continue

        consecutive_empty = 0
        added = 0
        valid_times = []

        for candle in values:
            stamp = candle.get("datetime")
            if not stamp:
                continue
            # Ignore malformed candle rows.
            try:
                parse_timestamp(stamp)
            except ValueError:
                continue

            valid_times.append(stamp)
            if stamp not in rows_by_time:
                rows_by_time[stamp] = {
                    "datetime": stamp,
                    "open": candle.get("open", ""),
                    "high": candle.get("high", ""),
                    "low": candle.get("low", ""),
                    "close": candle.get("close", ""),
                }
                added += 1

        save_rows(rows_by_time, PROGRESS_FILE)
        print(f"В порции от API: {len(values)}; новых свечей: {added}; "
              f"всего сохранено: {len(rows_by_time)}.")

        if not valid_times:
            print("В ответе не оказалось корректных временных меток. "
                  "Останавливаемся; прогресс сохранён.")
            return

        # Move back from the oldest actual candle returned, not the requested
        # start time. This avoids skipping candles when the API returns fewer.
        oldest_dt = min(parse_timestamp(stamp) for stamp in valid_times)
        end_dt = oldest_dt - timedelta(minutes=1)

        if added == 0:
            print("Новых свечей нет в этой порции. Проверяем более ранний период.")

        time.sleep(PAUSE_BETWEEN_REQUESTS)

    save_rows(rows_by_time, FINAL_FILE)
    print(f"\nГОТОВО! Сохранено {len(rows_by_time)} свечей.")
    print(f"Итоговый файл: {FINAL_FILE.resolve()}")
    print(f"Файл прогресса оставлен: {PROGRESS_FILE.resolve()}")


if __name__ == "__main__":
    main()
