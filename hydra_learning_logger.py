import csv
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CSV_FILE = BASE_DIR / "observer_data" / "eurusd_candles.csv"
LOG_FILE = BASE_DIR / "observer_data" / "hydra_learning_log.csv"
FIELDS = [
    "recorded_at_utc", "latest_candle_utc", "candles_loaded", "latest_close",
    "change_5_candles_pips", "change_15_candles_pips", "change_30_candles_pips",
    "avg_range_last_5_pips", "avg_range_previous_5_pips", "range_ratio",
    "latest_candle_range_pips", "streak_direction", "streak_length",
]
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
    if not rows:
        print("Нет корректных свечей; запись пропущена.")
        return
    closes = [r[4] for r in rows]
    ranges = [(r[2]-r[3])/PIP for r in rows]
    def move(n):
        return round((closes[-1]-closes[-(n+1)])/PIP, 2) if len(closes) > n else ""
    last5 = ranges[-5:]
    prev5 = ranges[-10:-5]
    avg_last = sum(last5)/len(last5)
    avg_prev = sum(prev5)/len(prev5) if prev5 else 0
    directions = ["рост" if r[4] > r[1] else "снижение" if r[4] < r[1] else "без изменения" for r in rows]
    streak_dir = directions[-1]
    streak_len = 0
    for direction in reversed(directions):
        if direction != streak_dir:
            break
        streak_len += 1
    record = {
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "latest_candle_utc": rows[-1][0].isoformat(),
        "candles_loaded": len(rows),
        "latest_close": f"{closes[-1]:.5f}",
        "change_5_candles_pips": move(5),
        "change_15_candles_pips": move(15),
        "change_30_candles_pips": move(30),
        "avg_range_last_5_pips": f"{avg_last:.2f}",
        "avg_range_previous_5_pips": f"{avg_prev:.2f}" if prev5 else "",
        "range_ratio": f"{avg_last/avg_prev:.2f}" if avg_prev else "",
        "latest_candle_range_pips": f"{ranges[-1]:.2f}",
        "streak_direction": streak_dir,
        "streak_length": streak_len,
    }
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    new_file = not LOG_FILE.exists() or LOG_FILE.stat().st_size == 0
    with LOG_FILE.open("a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow(record)
    print(f"Наблюдение добавлено: {record['latest_candle_utc']} | close={record['latest_close']}")

if __name__ == "__main__":
    main()
