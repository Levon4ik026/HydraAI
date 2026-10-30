import csv
import json
import sys
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

    report = result.stdout.strip()
    if not report:
        raise RuntimeError("Технический расчёт вернул пустой отчёт.")

    return report


def find_data_gaps(candles):
    """Ищет разрывы только в переданном фрагменте свечей."""
    gaps = []

    for previous, current in zip(candles, candles[1:]):
        previous_text = previous.get("datetime_utc", "")
        current_text = current.get("datetime_utc", "")

        try:
            t1 = datetime.fromisoformat(previous_text.replace("Z", "+00:00"))
            t2 = datetime.fromisoformat(current_text.replace("Z", "+00:00"))

            if t1.tzinfo is None or t2.tzinfo is None:
                gaps.append(
                    f"Не удалось подтвердить часовой пояс: "
                    f"{previous_text} / {current_text}"
                )
                continue

            minutes = (t2 - t1).total_seconds() / 60
            if minutes > 1.5:
                gaps.append(
                    f"{previous_text} -> {current_text}: {minutes:.1f} минут"
                )
            elif minutes <= 0:
                gaps.append(
                    f"Некорректный порядок времени: "
                    f"{previous_text} -> {current_text}"
                )
        except (TypeError, ValueError):
            gaps.append(
                f"Не удалось разобрать время: {previous_text} / {current_text}"
            )

    return gaps


def build_prompt(technical_report, candles, gaps):
    """Формирует строгий запрос: числовые факты берутся только из Python."""
    data_status = (
        "\n".join(f"- {gap}" for gap in gaps)
        if gaps
        else "В проверенном фрагменте разрывов более 1,5 минуты не обнаружено."
    )

    return f"""
Ты — аналитический помощник Hydra AI Trader. Отвечай по-русски.

СТРОГИЕ ПРАВИЛА:
1. Единственный источник числовых технических показателей — блок
   «ТЕХНИЧЕСКИЙ ОТЧЁТ PYTHON» ниже. Не пересчитывай проценты, пипсы,
   средние, стандартное отклонение, количество свечей или диапазоны.
2. Не меняй местами интервалы 5, 15 и 30 минут. Если упоминаешь показатель,
   перепиши его значение и временной интервал точно из отчёта Python.
3. Не утверждай, что есть временные пропуски, если Python их не обнаружил.
   Список «ПРОВЕРКА ВРЕМЕНИ» ниже относится только к последним переданным
   свечам. Если там написано, что разрывов нет, так и сообщи.
4. Не придумывай причины движения, новости, уровни поддержки/сопротивления
   или любые данные, которых нет во входных материалах.
5. Если блоки данных расходятся или чего-то не хватает, укажи это явно,
   не пытайся угадывать и не заполняй пробелы.
6. Разделяй подтверждённые факты и осторожную интерпретацию.
7. Не давай торговых сигналов, рекомендаций открыть/закрыть сделку
   и не обещай прибыль.
8. Не называй волатильность «низкой», «высокой» или «небольшой» без
   заданного числового порога для такой классификации.
9. Не утверждай, что построил или просмотрел график: график не передан.
10. Ответ должен быть кратким. Не повторяй все числа без необходимости.

ФОРМАТ ОТВЕТА:
- Факты Python: кратко перечисли динамику, волатильность и качество данных,
  сохраняя значения и интервалы без изменений.
- Наблюдение по последним свечам: только то, что действительно видно
  из переданных OHLC.
- Ограничения: укажи, чего эти данные не позволяют заключить.
Если факт отсутствует, напиши «не рассчитано» или «нет данных».

ТЕХНИЧЕСКИЙ ОТЧЁТ PYTHON (ИСТОЧНИК ИСТИНЫ ДЛЯ ЧИСЕЛ):
{technical_report}

ПРОВЕРКА ВРЕМЕНИ ПОСЛЕДНИХ СВЕЧЕЙ:
{data_status}

ПОСЛЕДНИЕ СВЕЧИ OHLC (только для описания последовательности, не для
самостоятельного пересчёта технических показателей):
{json.dumps(candles[-20:], ensure_ascii=False)}
""".strip()


def main():
    # Не запускаем расчёты и Ollama, если наблюдатель ещё не сохранил свечи.
    if not CSV_FILE.exists():
        raise FileNotFoundError(f"Не найден файл свечей: {CSV_FILE}")

    with CSV_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"datetime_utc", "open", "high", "low", "close"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise RuntimeError("В CSV отсутствуют обязательные столбцы OHLC.")
        candles = list(reader)

    if not candles:
        raise RuntimeError("В CSV нет свечей.")

    candles = candles[-60:]
    gaps = find_data_gaps(candles)
    technical_report = get_technical_metrics()

    print("\n--- ТЕХНИЧЕСКИЙ РАСЧЁТ PYTHON ---\n")
    print(technical_report)

    prompt = build_prompt(technical_report, candles, gaps)
    payload = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1
        }
    }).encode("utf-8")

    request = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    print("\nОтправляю последние свечи в локальную модель...")
    with urllib.request.urlopen(request, timeout=300) as response:
        result = json.loads(response.read().decode("utf-8"))

    answer = result.get("response", "").strip()
    if not answer:
        raise RuntimeError("Qwen вернула пустой ответ.")

    timestamp = datetime.now(timezone.utc).isoformat()
    last_candle_time = candles[-1].get("datetime_utc", "неизвестно")

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"\n{'=' * 70}\n")
        f.write(f"Время анализа UTC: {timestamp}\n")
        f.write(f"Модель: {MODEL}\n")
        f.write(f"Последняя свеча: {last_candle_time}\n")
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
        sys.exit(1)
    except Exception as error:
        print(f"Ошибка анализа: {error!r}")
        sys.exit(1)
