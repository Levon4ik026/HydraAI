
import csv
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CSV_FILE = BASE_DIR / "observer_data" / "eurusd_candles.csv"
LOG_FILE = BASE_DIR / "observer_data" / "ai_analysis_log.txt"
MODEL = "qwen2.5:7b"
OLLAMA_URL = "http://localhost:11434/api/generate"

TECHNICAL_SCRIPT = BASE_DIR / "hydra_technical_metrics.py"


def get_technical_metrics():
    """Запускает отдельный технический расчёт и возвращает его вывод."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, str(TECHNICAL_SCRIPT)],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Технический расчёт завершился с ошибкой:\n"
            + result.stderr[-3000:]
        )

    return result.stdout.strip()



def main():
    technical_report = get_technical_metrics()
    print("\n--- ТЕХНИЧЕСКИЙ РАСЧЁТ PYTHON ---\n")
    print(technical_report)
    if not CSV_FILE.exists():
        print(f"Не найден файл свечей: {CSV_FILE}")
        return

    with CSV_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        candles = list(csv.DictReader(f))

    if not candles:
        print("В CSV нет свечей.")
        return

    candles = candles[-60:]
    times = [c["datetime_utc"] for c in candles]
    closes = [float(c["close"]) for c in candles]

    gaps = []
    for previous, current in zip(times, times[1:]):
        try:
            t1 = datetime.fromisoformat(previous.replace("Z", "+00:00"))
            t2 = datetime.fromisoformat(current.replace("Z", "+00:00"))
            minutes = (t2 - t1).total_seconds() / 60
            if minutes > 1.5:
                gaps.append(f"{previous} -> {current}: {minutes:.0f} минут")
        except ValueError:
            gaps.append(f"Не удалось проверить время: {previous} / {current}")

    change_5 = (closes[-1] / closes[-6] - 1) * 100 if len(closes) >= 6 else None
    change_15 = (closes[-1] / closes[-16] - 1) * 100 if len(closes) >= 16 else None

    summary = {
        "pair": "EUR/USD",
        "timeframe": "1 минута",
        "last_candle": candles[-1],
        "candles_sent": len(candles),
        "change_over_5_intervals_percent": change_5,
        "change_over_15_intervals_percent": change_15,
        "gaps_in_selected_data": gaps,
        "data_warning": (
            "Временные пропуски обнаружены. Не считай соседние строки "
            "непрерывными минутами, если время это не подтверждает."
        ) if gaps else "В выбранном фрагменте крупных временных пропусков не обнаружено."
    }

    prompt = f"""
Ты — локальный аналитический помощник Hydra AI Trader.
Проанализируй предоставленные исторические данные EUR/USD.
Не давай торговых сигналов, не предлагай открывать сделки и не обещай прибыль.
Отделяй наблюдаемые факты от предположений.
Укажи краткосрочную динамику, волатильность по диапазонам high-low,
качество данных, временные пропуски и ограничения вывода.
Если данных недостаточно, прямо скажи об этом.
Ответь по-русски и кратко.

Данные:
{json.dumps(summary, ensure_ascii=False, indent=2)}

Технический расчёт Python:
{technical_report}

Последние свечи:
{json.dumps(candles[-20:], ensure_ascii=False)}
"""

    payload = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }).encode("utf-8")

    request = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    print("Отправляю последние свечи в локальную модель...")
    with urllib.request.urlopen(request, timeout=300) as response:
        result = json.loads(response.read().decode("utf-8"))

    answer = result.get("response", "").strip()
    timestamp = datetime.now(timezone.utc).isoformat()

    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"\n{'=' * 70}\n")
        f.write(f"Время анализа UTC: {timestamp}\n")
        f.write(f"Модель: {MODEL}\n")
        f.write(f"Последняя свеча: {times[-1]}\n")
        f.write(answer + "\n")

    print("\n--- АНАЛИЗ QWEN ---\n")
    print(answer)
    print(f"\nРезультат сохранён в: {LOG_FILE}")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.URLError as error:
        print("Не удалось подключиться к Ollama.")
        print("Проверь, что Ollama запущена и доступна по адресу localhost:11434.")
        print(error)
    except Exception as error:
        print(f"Ошибка анализа: {error!r}")
