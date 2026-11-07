#!/usr/bin/env python3
"""Reproducible M5 Bollinger + Williams %R + ADX research test.

Standard-library only. Run from repository root:
    python research/reproduce_m5_bb_williams_adx.py
"""
from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import defaultdict

PAYOUT = 0.92
ADX_THRESHOLDS = (15, 20, 25)
DATA_PATH = Path(__file__).resolve().parents[1] / "eurusd_history_extended.csv"


@dataclass(frozen=True)
class Bar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float


def load_m1(path: Path) -> list[Bar]:
    parsed: dict[datetime, Bar] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"datetime", "open", "high", "low", "close"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"CSV must contain columns: {sorted(required)}")
        for row in reader:
            ts = datetime.fromisoformat(row["datetime"].strip().replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            ts = ts.astimezone(timezone.utc)
            o, h, l, c = (float(row[k]) for k in ("open", "high", "low", "close"))
            if not all(math.isfinite(x) and x > 0 for x in (o, h, l, c)):
                raise ValueError(f"Invalid OHLC at {ts.isoformat()}")
            if h < max(o, l, c) or l > min(o, h, c):
                raise ValueError(f"Invalid OHLC ordering at {ts.isoformat()}")
            parsed[ts] = Bar(ts, o, h, l, c)
    return [parsed[t] for t in sorted(parsed)]


def make_m5(m1: list[Bar]) -> list[list[Bar]]:
    """Build only complete UTC-aligned M5 buckets; split on every missing bucket."""
    buckets: dict[datetime, list[Bar]] = defaultdict(list)
    for bar in m1:
        start = bar.timestamp.replace(minute=(bar.timestamp.minute // 5) * 5,
                                      second=0, microsecond=0)
        buckets[start].append(bar)
    complete: list[Bar] = []
    for start in sorted(buckets):
        group = sorted(buckets[start], key=lambda x: x.timestamp)
        expected = [start + timedelta(minutes=i) for i in range(5)]
        if [x.timestamp for x in group] != expected:
            continue
        complete.append(Bar(start, group[0].open, max(x.high for x in group),
                            min(x.low for x in group), group[-1].close))
    segments: list[list[Bar]] = []
    for bar in complete:
        if not segments or bar.timestamp - segments[-1][-1].timestamp != timedelta(minutes=5):
            segments.append([bar])
        else:
            segments[-1].append(bar)
    return segments


def indicators(bars: list[Bar]) -> list[dict[str, float | None]]:
    n = len(bars)
    upper: list[float | None] = [None] * n
    lower: list[float | None] = [None] * n
    willr: list[float | None] = [None] * n
    adx: list[float | None] = [None] * n

    for i in range(19, n):
        window = bars[i - 19:i + 1]
        mean = sum(x.close for x in window) / 20.0
        variance = sum((x.close - mean) ** 2 for x in window) / 20.0
        sd = math.sqrt(variance)
        upper[i], lower[i] = mean + 2.0 * sd, mean - 2.0 * sd

    for i in range(13, n):
        window = bars[i - 13:i + 1]
        highest = max(x.high for x in window)
        lowest = min(x.low for x in window)
        willr[i] = -50.0 if highest == lowest else -100.0 * (highest - bars[i].close) / (highest - lowest)

    # Wilder ADX(14): seed smoothed directional movement with the first 14
    # transitions, then seed ADX with the first 14 valid DX observations.
    dx: list[float | None] = [None] * n
    if n > 14:
        tr_sum = plus_sum = minus_sum = 0.0
        for i in range(1, 15):
            prev, cur = bars[i - 1], bars[i]
            up, down = cur.high - prev.high, prev.low - cur.low
            tr = max(cur.high - cur.low, abs(cur.high - prev.close), abs(cur.low - prev.close))
            tr_sum += tr
            plus_sum += up if up > down and up > 0 else 0.0
            minus_sum += down if down > up and down > 0 else 0.0
        for i in range(14, n):
            if i > 14:
                prev, cur = bars[i - 1], bars[i]
                up, down = cur.high - prev.high, prev.low - cur.low
                tr = max(cur.high - cur.low, abs(cur.high - prev.close), abs(cur.low - prev.close))
                tr_sum += tr - tr_sum / 14.0
                plus_sum += (up if up > down and up > 0 else 0.0) - plus_sum / 14.0
                minus_sum += (down if down > up and down > 0 else 0.0) - minus_sum / 14.0
            plus_di = 100.0 * plus_sum / tr_sum if tr_sum else 0.0
            minus_di = 100.0 * minus_sum / tr_sum if tr_sum else 0.0
            denom = plus_di + minus_di
            dx[i] = 100.0 * abs(plus_di - minus_di) / denom if denom else 0.0
        valid_dx = [(i, value) for i, value in enumerate(dx) if value is not None]
        if len(valid_dx) >= 14:
            seed_index = valid_dx[13][0]
            state = sum(value for _, value in valid_dx[:14]) / 14.0
            adx[seed_index] = state
            for i, value in valid_dx[14:]:
                state = (state * 13.0 + value) / 14.0
                adx[i] = state

    return [{"upper": upper[i], "lower": lower[i], "willr": willr[i], "adx": adx[i]}
            for i in range(n)]


def build_signals(segments: list[list[Bar]]) -> list[dict]:
    output = []
    for segment_id, bars in enumerate(segments):
        ind = indicators(bars)
        for i, bar in enumerate(bars):
            signal = 0
            if i > 0:
                prev = ind[i - 1]
                cur = ind[i]
                if all(prev[k] is not None for k in ("upper", "lower", "willr")) and all(
                    cur[k] is not None for k in ("upper", "lower", "willr", "adx")
                ):
                    if (bars[i - 1].close < prev["lower"] and bar.close > cur["lower"]
                            and prev["willr"] <= -80.0 and cur["willr"] > -80.0):
                        signal = 1
                    elif (bars[i - 1].close > prev["upper"] and bar.close < cur["upper"]
                          and prev["willr"] >= -20.0 and cur["willr"] < -20.0):
                        signal = -1
            output.append({"bar": bar, "signal": signal, "adx": ind[i]["adx"], "segment_id": segment_id})
    return output


def run_trades(rows: list[dict], threshold: float) -> list[dict]:
    trades = []
    i = 0
    while i < len(rows) - 1:
        row = rows[i]
        if not row["signal"] or row["adx"] is None or row["adx"] < threshold:
            i += 1
            continue
        next_row = rows[i + 1]
        # A trade must enter on the immediately following M5 candle in the same segment.
        if (next_row["segment_id"] != row["segment_id"] or
                next_row["bar"].timestamp - row["bar"].timestamp != timedelta(minutes=5)):
            i += 1
            continue
        entry = next_row["bar"]
        change = entry.close - entry.open
        if abs(change) < 1e-12:
            outcome, profit = "DRAW", 0.0
        elif (row["signal"] == 1 and change > 0) or (row["signal"] == -1 and change < 0):
            outcome, profit = "WIN", PAYOUT
        else:
            outcome, profit = "LOSS", -1.0
        trades.append({"direction": "CALL" if row["signal"] == 1 else "PUT",
                       "outcome": outcome, "profit": profit,
                       "signal_time": row["bar"].timestamp,
                       "entry_time": entry.timestamp,
                       "settlement_time": entry.timestamp + timedelta(minutes=5)})
        i += 1  # expiry closes on entry candle; a signal on that close may enter the next candle
    return trades


def wilson_interval(wins: int, decisive: int, z: float = 1.959963984540054) -> tuple[float, float] | None:
    if decisive <= 0:
        return None
    p = wins / decisive
    denom = 1.0 + z * z / decisive
    center = (p + z * z / (2.0 * decisive)) / denom
    radius = z * math.sqrt((p * (1.0 - p) / decisive) + z * z / (4.0 * decisive * decisive)) / denom
    return (100.0 * (center - radius), 100.0 * (center + radius))



def fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> float | None:
    """Two-sided Fisher exact p-value for [[a,b],[c,d]], conditioning on margins."""
    r1, r2, col1 = a + b, c + d, a + c
    total = r1 + r2
    if total == 0 or r1 == 0 or r2 == 0 or col1 == 0 or col1 == total:
        return None
    lo, hi = max(0, r1 - (total - col1)), min(r1, col1)
    denom = math.comb(total, r1)
    def probability(x: int) -> float:
        return math.comb(col1, x) * math.comb(total - col1, r1 - x) / denom
    observed = probability(a)
    return min(1.0, sum(probability(x) for x in range(lo, hi + 1)
                        if probability(x) <= observed + 1e-15))


def direction_comparison(trades: list[dict]) -> dict:
    call = [t for t in trades if t["direction"] == "CALL" and t["outcome"] != "DRAW"]
    put = [t for t in trades if t["direction"] == "PUT" and t["outcome"] != "DRAW"]
    cw = sum(t["outcome"] == "WIN" for t in call)
    pw = sum(t["outcome"] == "WIN" for t in put)
    cl, pl = len(call) - cw, len(put) - pw
    return {"call": summary([t for t in trades if t["direction"] == "CALL"]),
            "put": summary([t for t in trades if t["direction"] == "PUT"]),
            "fisher_two_sided_p": fisher_exact_two_sided(cw, cl, pw, pl)}


def summary(trades: list[dict]) -> dict:
    wins = sum(t["outcome"] == "WIN" for t in trades)
    losses = sum(t["outcome"] == "LOSS" for t in trades)
    draws = sum(t["outcome"] == "DRAW" for t in trades)
    decisive = wins + losses
    equity = peak = max_dd = 0.0
    for trade in trades:
        equity += trade["profit"]
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    ci = wilson_interval(wins, decisive)
    return {"trades": len(trades), "wins": wins, "losses": losses, "draws": draws,
            "decisive": decisive,
            "win_rate": round(100.0 * wins / decisive, 2) if decisive else 0.0,
            "wilson_95_pct": [round(x, 2) for x in ci] if ci else None,
            "net_92": round(sum(t["profit"] for t in trades), 2),
            "max_drawdown_units": round(max_dd, 2)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DATA_PATH)
    parser.add_argument("--verify-known-results", action="store_true",
                        help="verify corrected frozen holdout counts and net units at 92% payout")
    args = parser.parse_args()
    m1 = load_m1(args.data)
    segments = make_m5(m1)
    rows = build_signals(segments)
    boundary = rows[int(len(rows) * 0.70)]["bar"].timestamp
    train = [r for r in rows if r["bar"].timestamp < boundary]
    holdout = [r for r in rows if r["bar"].timestamp >= boundary]
    print(f"M1 rows: {len(m1)} | M5 bars: {len(rows)} | M5 segments: {len(segments)}")
    print(f"Range: {rows[0]['bar'].timestamp.isoformat()} .. {rows[-1]['bar'].timestamp.isoformat()}")
    print(f"Chronological 70/30 boundary: {boundary.isoformat()} | payout: {PAYOUT:.2f}")
    holdout_results = {}
    for threshold in ADX_THRESHOLDS:
        all_trades = run_trades(rows, threshold)
        # Schedule the full continuous history once, then assign each completed
        # trade by its settlement timestamp. This prevents split-boundary overlap
        # and avoids resetting the scheduler at the train/holdout boundary.
        train_trades = [t for t in all_trades if t["settlement_time"] < boundary]
        test_trades = [t for t in all_trades if t["settlement_time"] >= boundary]
        holdout_results[threshold] = summary(test_trades)
        train_cmp = direction_comparison(train_trades)
        holdout_cmp = direction_comparison(test_trades)
        full_cmp = direction_comparison(all_trades)
        print(f"ADX >= {threshold}: train={summary(train_trades)} | holdout={summary(test_trades)}")
        print(f"  FULL direction comparison: CALL={full_cmp['call']} | PUT={full_cmp['put']} | Fisher two-sided p={full_cmp['fisher_two_sided_p']}")
        print(f"  TRAIN direction comparison: CALL={train_cmp['call']} | PUT={train_cmp['put']} | Fisher two-sided p={train_cmp['fisher_two_sided_p']}")
        print(f"  HOLDOUT direction comparison: CALL={holdout_cmp['call']} | PUT={holdout_cmp['put']} | Fisher two-sided p={holdout_cmp['fisher_two_sided_p']}")
        # Weekly slices cover the entire available history, not only holdout.
        # Trades are grouped by signal week (Monday 00:00 UTC), with CALL/PUT
        # split and exact directional comparison shown for each week.
        weekly: dict[str, list[dict]] = defaultdict(list)
        for trade in all_trades:
            stamp = trade["signal_time"]
            week_start = (stamp - timedelta(days=stamp.weekday())).strftime("%Y-%m-%d")
            weekly[week_start].append(trade)
        for week in sorted(weekly):
            week_trades = weekly[week]
            comp = direction_comparison(week_trades)
            print(f"  WEEK {week} UTC: ALL={summary(week_trades)} | CALL={comp['call']} | PUT={comp['put']} | Fisher p={comp['fisher_two_sided_p']}")
    if args.verify_known_results:
        expected = {
            15: (48, 31, 17, 0, 11.52),
            20: (39, 23, 16, 0, 5.16),
            25: (21, 13, 8, 0, 3.96),
        }
        for threshold, (count, wins, losses, draws, net) in expected.items():
            got = holdout_results[threshold]
            actual = (got["trades"], got["wins"], got["losses"], got["draws"], got["net_92"])
            if actual != (count, wins, losses, draws, net):
                raise SystemExit(f"Corrected frozen holdout mismatch for ADX {threshold}: {actual}")
        print("CORRECTED FROZEN HOLDOUT CHECK: PASS (92% payout)")


if __name__ == "__main__":
    main()
