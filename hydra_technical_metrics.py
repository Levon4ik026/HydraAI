import csv
import math
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CSV_FILE = BASE_DIR / "observer_data" / "eurusd_candles.csv"
PIP = 0.0001

def main():
    if not CSV_FILE.exists():
        raise FileNotFoundError(f"Не найден файл свечей: {CSV_FILE}")
    with CSV_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        raw = list(csv.DictReader(f))
    rows = []
    for row in raw:
        try:
            dt = datetime.fromisoformat(row["datetime_utc"].replace("Z", "+00:00"))
            o, h, l, c = (float(row[k]) for k in ("open", "high", "low", "close"))
            if min(o, h, l, c) <= 0 or h < max(o, c, l) or l > min(o, c, h):
                continue
            rows.append((dt, o, h, l, c))
        except (ValueError, KeyError, TypeError):
            continue
    rows.sort(key=lambda x: x[0])
    rows = rows[-120:]
    if not rows:
        print("Недостаточно корректных свечей для технического расчёта.")
        return
    closes = [r[4] for r in rows]
    ranges = [(r[2] - r[3]) / PIP for r in rows]
    returns = [(b / a - 1) * 100 for a, b in zip(closes, closes[1:]) if a > 0]
    gaps = [(a[0], b[0]) for a, b in zip(rows, rows[1:]) if (b[0]-a[0]).total_seconds() > 90]
    mean_range = sum(ranges) / len(ranges)
    variance = sum((x - sum(returns)/len(returns))**2 for x in returns) / len(returns) if returns else 0
    print(f"Корректных свечей в расчёте: {len(rows)}")
    print(f"Последняя свеча UTC: {rows[-1][0].isoformat()}")
    print(f"Последний close: {closes[-1]:.5f}")
    for n in (5, 15, 30):
        if len(closes) > n:
            pct = (closes[-1] / closes[-(n+1)] - 1) * 100
            print(f"Изменение за {n} интервалов: {pct:+.5f}%")
        else:
            print(f"Изменение за {n} интервалов: недостаточно данных")
    print(f"Средний high-low диапазон: {mean_range:.3f} пипса")
    print(f"Максимальный диапазон свечи: {max(ranges):.3f} пипса")
    print(f"Минимальный диапазон свечи: {min(ranges):.3f} пипса")
    print(f"Стандартное отклонение close-to-close: {math.sqrt(variance):.6f}%")
    print(f"Временных разрывов более 90 секунд: {len(gaps)}")
    for a, b in gaps[-8:]:
        mins = (b-a).total_seconds()/60
        print(f"  {a.isoformat()} -> {b.isoformat()}: {mins:.0f} минут")

if __name__ == "__main__":
    main()
