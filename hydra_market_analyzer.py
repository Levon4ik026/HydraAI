import csv
from collections import Counter
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CSV_FILE = BASE_DIR / "observer_data" / "eurusd_candles.csv"
PIP = 0.0001

def load_candles():
    if not CSV_FILE.exists():
        raise FileNotFoundError(f"Не найден файл свечей: {CSV_FILE}")
    rows = []
    with CSV_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            try:
                dt = datetime.fromisoformat(row["datetime_utc"].replace("Z", "+00:00"))
                o, h, low, close = (float(row[k]) for k in ("open", "high", "low", "close"))
                if min(o, h, low, close) <= 0 or h < max(o, close, low) or low > min(o, close, h):
                    continue
                rows.append((dt, o, h, low, close))
            except (ValueError, KeyError, TypeError):
                continue
    rows.sort(key=lambda x: x[0])
    return rows

def main():
    rows = load_candles()
    if not rows:
        print("В CSV нет корректных свечей.")
        return 1
    latest = rows[-1]
    print("=" * 58)
    print("HYDRA AI TRADER — MARKET ANALYZER")
    print("Инструмент: EUR/USD | режим: наблюдение без сигналов")
    print("=" * 58)
    print("\nПОСЛЕДНЯЯ СВЕЧА")
    print(f"Время UTC: {latest[0].isoformat()}")
    print(f"Open: {latest[1]:.5f} | High: {latest[2]:.5f} | Low: {latest[3]:.5f} | Close: {latest[4]:.5f}")
    closes = [r[4] for r in rows]
    ranges = [(r[2] - r[3]) / PIP for r in rows]
    print("\nНАПРАВЛЕНИЕ ДВИЖЕНИЯ")
    for n in (5, 15, 30):
        if len(closes) >= n:
            delta = (closes[-1] - closes[-n]) / PIP
            direction = "рост" if delta > 0 else "снижение" if delta < 0 else "без изменения"
            print(f"Последние {n} свечей: {direction}; изменение {delta:+.1f} пипса")
        else:
            print(f"Последние {n} свечей: недостаточно данных")
    last = ranges[-5:]
    prev = ranges[-10:-5]
    avg_last = sum(last) / len(last)
    avg_prev = sum(prev) / len(prev) if prev else 0
    ratio = avg_last / avg_prev if avg_prev else 0
    print("\nВОЛАТИЛЬНОСТЬ")
    print(f"Средний диапазон последних 5 свечей: {avg_last:.2f} пипса")
    print(f"Средний диапазон предыдущих 5 свечей: {avg_prev:.2f} пипса")
    print(f"Отношение диапазонов: {ratio:.2f}x" if avg_prev else "Предыдущих свечей для сравнения недостаточно")
    dirs = ["рост" if r[4] > r[1] else "снижение" if r[4] < r[1] else "без изменения" for r in rows]
    streak = 0
    for d in reversed(dirs):
        if d != dirs[-1]:
            break
        streak += 1
    print("\nПОСЛЕДОВАТЕЛЬНОСТЬ")
    print(f"Текущая серия: {dirs[-1]}, {streak} свеч(и) подряд")
    counts = Counter(r[0] for r in rows)
    gaps = [(a[0], b[0], round((b[0]-a[0]).total_seconds()/60)-1) for a,b in zip(rows,rows[1:]) if (b[0]-a[0]).total_seconds() > 90]
    print("\nКАЧЕСТВО ДАННЫХ")
    print(f"Корректных строк: {len(rows)} | уникальных отметок: {len(counts)} | дубликатов: {sum(v-1 for v in counts.values())}")
    print(f"Интервалов с временными разрывами: {len(gaps)}")
    for a,b,missing in gaps[-10:]:
        print(f"{a.isoformat()} -> {b.isoformat()}: около {missing} пропущенных минут")
    print("\nАнализ завершён. Торговые сигналы не формировались.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
