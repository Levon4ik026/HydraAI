import csv
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from config import API_KEY

# ============================================================
# HYDRA AI TRADER — MARKET OBSERVER
# Источник: Twelve Data Basic
# Инструмент: EUR/USD, без OTC
# Назначение: сбор данных и статистика, без торговых сигналов
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "observer_data"
RAW_FILE = DATA_DIR / "eurusd_candles.csv"
OBSERVATIONS_FILE = DATA_DIR / "market_observations.csv"
ERRORS_FILE = DATA_DIR / "api_errors.log"

SYMBOL = "EUR/USD"
INTERVAL = "1min"

# Начинаем с одного запроса каждые 5 минут.
POLL_INTERVAL_SECONDS = 300

# Запрашиваем небольшой набор последних свечей.
OUTPUT_SIZE = 30

# Сырые свечи храним 3 дня.
RAW_RETENTION_DAYS = 3

# Пауза после ошибки, чтобы не расходовать кредиты впустую.
ERROR_RETRY_SECONDS = 60

API_URL = "https://api.twelvedata.com/time_series"

RAW_FIELDS = [
    "datetime_utc",
    "open",
    "high",
    "low",
    "close",
]

OBSERVATION_FIELDS = [
    "observed_at_utc",
    "candle_datetime_utc",
    "close",
    "change",
    "change_percent",
    "range",
    "range_percent",
    "direction",
    "volatility",
    "data_status",
]

def utc_now():
    return datetime.now(timezone.utc)

def ensure_files():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not RAW_FILE.exists():
        with RAW_FILE.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=RAW_FIELDS)
            writer.writeheader()

    if not OBSERVATIONS_FILE.exists():
        with OBSERVATIONS_FILE.open(
            "w", newline="", encoding="utf-8"
        ) as f:
            writer = csv.DictWriter(
                f, fieldnames=OBSERVATION_FIELDS
            )
            writer.writeheader()

def log_error(message):
    timestamp = utc_now().isoformat(timespec="seconds")

    with ERRORS_FILE.open("a", encoding="utf-8") as f:
        f.write(f"{timestamp} | {message}\n")

    print(f"[ОШИБКА] {message}")

def parse_candle_time(value):
    """
    Twelve Data возвращает datetime свечи без указания часового
    пояса. По умолчанию API обычно использует часовой пояс,
    связанный с настройками запроса. Поэтому здесь явно запрашиваем
    UTC и сохраняем время в UTC.
    """
    dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    return dt.replace(tzinfo=timezone.utc)

def fetch_candles():
    params = {
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "outputsize": OUTPUT_SIZE,
        "timezone": "UTC",
        "apikey": API_KEY,
    }

    response = requests.get(
        API_URL,
        params=params,
        timeout=20,
    )

    response.raise_for_status()
    data = response.json()

    if "values" not in data:
        raise RuntimeError(
            f"API не вернул свечи: {data}"
        )

    candles = []

    for item in data["values"]:
        candles.append({
            "datetime_utc": parse_candle_time(
                item["datetime"]
            ).isoformat(timespec="seconds"),
            "open": float(item["open"]),
            "high": float(item["high"]),
            "low": float(item["low"]),
            "close": float(item["close"]),
        })

    # От старых свечей к новым.
    candles.sort(key=lambda x: x["datetime_utc"])

    return candles

def load_existing_candle_times():
    existing = set()

    if not RAW_FILE.exists():
        return existing

    with RAW_FILE.open(
        "r", newline="", encoding="utf-8"
    ) as f:
        reader = csv.DictReader(f)

        for row in reader:
            existing.add(row["datetime_utc"])

    return existing

def append_new_candles(candles):
    existing = load_existing_candle_times()
    added = []

    with RAW_FILE.open(
        "a", newline="", encoding="utf-8"
    ) as f:
        writer = csv.DictWriter(
            f, fieldnames=RAW_FIELDS
        )

        for candle in candles:
            timestamp = candle["datetime_utc"]

            if timestamp in existing:
                continue

            writer.writerow(candle)
            existing.add(timestamp)
            added.append(candle)

    return added

def remove_old_raw_candles():
    """
    Удаляет только сырые свечи старше трёх дней.
    Файл наблюдений и журнал ошибок не удаляются.
    """
    if not RAW_FILE.exists():
        return

    cutoff = utc_now() - timedelta(
        days=RAW_RETENTION_DAYS
    )

    kept = []

    with RAW_FILE.open(
        "r", newline="", encoding="utf-8"
    ) as f:
        reader = csv.DictReader(f)

        for row in reader:
            try:
                candle_time = datetime.fromisoformat(
                    row["datetime_utc"]
                )

                if candle_time >= cutoff:
                    kept.append(row)

            except (ValueError, TypeError):
                # Не удаляем строку, которую не смогли разобрать.
                kept.append(row)

    with RAW_FILE.open(
        "w", newline="", encoding="utf-8"
    ) as f:
        writer = csv.DictWriter(
            f, fieldnames=RAW_FIELDS
        )
        writer.writeheader()
        writer.writerows(kept)

def load_recent_closes(limit=30):
    rows = []

    if not RAW_FILE.exists():
        return rows

    with RAW_FILE.open(
        "r", newline="", encoding="utf-8"
    ) as f:
        reader = csv.DictReader(f)

        for row in reader:
            rows.append(row)

    rows.sort(key=lambda x: x["datetime_utc"])

    return rows[-limit:]

def calculate_observation(candle, previous_close):
    close = candle["close"]
    candle_range = candle["high"] - candle["low"]

    if previous_close is None:
        change = None
        change_percent = None
        direction = "нет базы для сравнения"
    else:
        change = close - previous_close
        change_percent = (
            change / previous_close * 100
            if previous_close != 0
            else None
        )

        if change > 0:
            direction = "рост"
        elif change < 0:
            direction = "снижение"
        else:
            direction = "без изменения"

    range_percent = (
        candle_range / close * 100
        if close != 0
        else None
    )

    return {
        "observed_at_utc": utc_now().isoformat(
            timespec="seconds"
        ),
        "candle_datetime_utc": candle["datetime_utc"],
        "close": close,
        "change": change,
        "change_percent": change_percent,
        "range": candle_range,
        "range_percent": range_percent,
        "direction": direction,
        "volatility": "расчёт начального диапазона",
        "data_status": "получена новая свеча",
    }

def save_observations(new_candles):
    if not new_candles:
        return

    recent = load_recent_closes(limit=100)

    # Берём предыдущие закрытия для сравнения.
    close_by_time = {
        row["datetime_utc"]: float(row["close"])
        for row in recent
    }

    with OBSERVATIONS_FILE.open(
        "a", newline="", encoding="utf-8"
    ) as f:
        writer = csv.DictWriter(
            f, fieldnames=OBSERVATION_FIELDS
        )

        for candle in new_candles:
            candle_time = candle["datetime_utc"]

            earlier = [
                timestamp
                for timestamp in close_by_time
                if timestamp < candle_time
            ]

            previous_close = None

            if earlier:
                previous_time = max(earlier)
                previous_close = close_by_time[previous_time]

            observation = calculate_observation(
                candle,
                previous_close,
            )

            writer.writerow(observation)

            close_by_time[candle_time] = candle["close"]

def main():
    ensure_files()

    if not API_KEY or not API_KEY.strip():
        raise RuntimeError("API_KEY не найден. Проверь config.py")

    print("=" * 58)
    print("HYDRA AI TRADER - MARKET OBSERVER")
    print("Инструмент: EUR/USD")
    print("Источник: Twelve Data")
    print("Режим: наблюдение без торговых сигналов")
    print(f"Интервал проверки: {POLL_INTERVAL_SECONDS} сек.")
    print(f"Папка данных: {DATA_DIR}")
    print("Для остановки нажми Ctrl+C")
    print("=" * 58)

    while True:
        cycle_started = time.monotonic()

        try:
            candles = fetch_candles()
            new_candles = append_new_candles(candles)

            save_observations(new_candles)
            remove_old_raw_candles()

            now = utc_now().isoformat(timespec="seconds")

            print(
                f"[{now}] "
                f"Получено свечей: {len(candles)} | "
                f"Новых сохранено: {len(new_candles)}"
            )

            if candles:
                latest = candles[-1]
                print(
                    f"Последняя свеча: "
                    f"{latest['datetime_utc']} | "
                    f"Close: {latest['close']}"
                )

        except KeyboardInterrupt:
            print("\nНаблюдатель остановлен.")
            break

        except Exception as error:
            log_error(repr(error))
            time.sleep(ERROR_RETRY_SECONDS)
            continue

        elapsed = time.monotonic() - cycle_started
        time.sleep(max(0, POLL_INTERVAL_SECONDS - elapsed))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nНаблюдатель остановлен.")
