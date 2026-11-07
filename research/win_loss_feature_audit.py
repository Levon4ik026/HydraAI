#!/usr/bin/env python3
"""Direction-separated winner/loser feature audit for the frozen M5 BB/Williams/ADX rule.

All predictors are measured at the signal candle close. Outcome is the immediately
following M5 candle. Exploratory feature tests are corrected with Benjamini-Hochberg.
No candidate filter is selected or promoted by this script.
"""
from __future__ import annotations

import argparse
import csv
import math
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    from .reproduce_m5_bb_williams_adx import PAYOUT, Bar, make_m5, indicators
except ImportError:  # direct execution: python research/win_loss_feature_audit.py
    from reproduce_m5_bb_williams_adx import PAYOUT, Bar, make_m5, indicators

SPLIT_DATE = "2026-10-21T19:05:00+00:00"
FEATURES = (
    "rsi14", "adx14", "plus_di", "minus_di", "di_spread",
    "ema20_50_atr", "bb_z20", "bb_width_atr", "atr14_close",
    "return1_atr", "return3_atr", "return6_atr", "return12_atr",
    "body_range", "upper_wick_range", "lower_wick_range",
    "range_atr", "up_streak", "down_streak", "hour_utc",
)


def parse_time(s: str) -> datetime:
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise ValueError("Timestamp must include timezone")
    return d.astimezone(timezone.utc)


def wilder(values: list[float], period: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if len(values) < period:
        return out
    state = sum(values[:period]) / period
    out[period - 1] = state
    for i in range(period, len(values)):
        state = (state * (period - 1) + values[i]) / period
        out[i] = state
    return out


def feature_rows(bars: list[Bar]) -> list[dict[str, float | None]]:
    n = len(bars)
    tr = []
    for i, b in enumerate(bars):
        tr.append(b.high - b.low if i == 0 else max(
            b.high - b.low, abs(b.high - bars[i - 1].close),
            abs(b.low - bars[i - 1].close)))
    atr = wilder(tr, 14)

    gains, losses = [0.0] * n, [0.0] * n
    for i in range(1, n):
        change = bars[i].close - bars[i - 1].close
        gains[i], losses[i] = max(change, 0.0), max(-change, 0.0)
    # Wilder RSI seeds on 14 close-to-close changes, not the initial zero.
    avg_gain, avg_loss = [None] * n, [None] * n
    if n > 14:
        g, l = sum(gains[1:15]) / 14, sum(losses[1:15]) / 14
        avg_gain[14], avg_loss[14] = g, l
        for i in range(15, n):
            g = (g * 13 + gains[i]) / 14
            l = (l * 13 + losses[i]) / 14
            avg_gain[i], avg_loss[i] = g, l

    ema20, ema50 = [None] * n, [None] * n
    for period, out in ((20, ema20), (50, ema50)):
        if n:
            alpha = 2.0 / (period + 1)
            state = bars[0].close
            out[0] = state
            for i in range(1, n):
                state = alpha * bars[i].close + (1 - alpha) * state
                out[i] = state

    base = indicators(bars)
    result = []
    up_streak = down_streak = 0
    for i, b in enumerate(bars):
        if i and b.close > bars[i - 1].close:
            up_streak, down_streak = up_streak + 1, 0
        elif i and b.close < bars[i - 1].close:
            down_streak, up_streak = down_streak + 1, 0
        else:
            up_streak = down_streak = 0

        a = atr[i]
        positive = avg_gain[i]
        negative = avg_loss[i]
        rsi = None if positive is None or negative is None else (
            100.0 if negative == 0 and positive > 0 else
            0.0 if positive == 0 and negative > 0 else
            50.0 if positive == 0 and negative == 0 else
            100.0 - 100.0 / (1.0 + positive / negative))
        bb = base[i]
        mid = (bb["upper"] + bb["lower"]) / 2 if bb["upper"] is not None and bb["lower"] is not None else None
        half = (bb["upper"] - bb["lower"]) / 2 if mid is not None else None
        rng = b.high - b.low
        body = abs(b.close - b.open)
        upper_wick = b.high - max(b.open, b.close)
        lower_wick = min(b.open, b.close) - b.low

        def ret(k: int) -> float | None:
            if i < k or a is None or a == 0:
                return None
            return (b.close - bars[i-k].close) / a

        result.append({
            "rsi14": rsi, "adx14": bb["adx"], "plus_di": bb["plus_di"],
            "minus_di": bb["minus_di"],
            "di_spread": None if bb["plus_di"] is None or bb["minus_di"] is None
                         else bb["plus_di"] - bb["minus_di"],
            "ema20_50_atr": None if a is None or a == 0 else (ema20[i] - ema50[i]) / a,
            "bb_z20": None if half is None or half == 0 else (b.close - mid) / half,
            "bb_width_atr": None if a is None or a == 0 or half is None else 2 * half / a,
            "atr14_close": None if a is None else a / b.close,
            "return1_atr": ret(1), "return3_atr": ret(3),
            "return6_atr": ret(6), "return12_atr": ret(12),
            "body_range": None if rng == 0 else body / rng,
            "upper_wick_range": None if rng == 0 else upper_wick / rng,
            "lower_wick_range": None if rng == 0 else lower_wick / rng,
            "range_atr": None if a is None or a == 0 else rng / a,
            "up_streak": float(up_streak), "down_streak": float(down_streak),
            "hour_utc": float(b.timestamp.hour),
        })
    return result


def average_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[order[k]] = rank
        i = j
    return ranks


def mann_whitney_p(a: list[float], b: list[float]) -> float | None:
    """Two-sided normal-approximation Mann-Whitney p, tie corrected."""
    if not a or not b:
        return None
    vals = a + b
    ranks = average_ranks(vals)
    n1, n2, n = len(a), len(b), len(vals)
    u1 = sum(ranks[:n1]) - n1 * (n1 + 1) / 2
    tie_counts: dict[float, int] = defaultdict(int)
    for x in vals:
        tie_counts[x] += 1
    tie_term = sum(t**3 - t for t in tie_counts.values())
    variance = n1 * n2 / 12.0 * ((n + 1) - tie_term / (n * (n - 1))) if n > 1 else 0
    if variance <= 0:
        return 1.0
    mean = n1 * n2 / 2.0
    z = (abs(u1 - mean) - 0.5) / math.sqrt(variance)  # continuity correction
    return math.erfc(max(0.0, z) / math.sqrt(2.0))


def cliff_delta(a: list[float], b: list[float]) -> float | None:
    if not a or not b:
        return None
    greater = sum(x > y for x in a for y in b)
    less = sum(x < y for x in a for y in b)
    return (greater - less) / (len(a) * len(b))


def benjamini_hochberg(pairs: list[tuple[str, float | None]]) -> dict[str, float | None]:
    valid = sorted(((name, p) for name, p in pairs if p is not None), key=lambda x: x[1])
    m = len(valid)
    adjusted: dict[str, float | None] = {name: None for name, _ in pairs}
    running = 1.0
    for rank in range(m, 0, -1):
        name, p = valid[rank - 1]
        running = min(running, p * m / rank)
        adjusted[name] = min(1.0, running)
    return adjusted


def quartile_rates(records: list[dict], feature: str) -> str:
    vals = sorted(r["features"][feature] for r in records
                  if r["features"][feature] is not None and r["outcome"] != "DRAW")
    if len(vals) < 8:
        return "insufficient"
    cuts = [vals[round((len(vals)-1)*q/4)] for q in (1, 2, 3)]
    groups = [[] for _ in range(4)]
    for r in records:
        x = r["features"][feature]
        if x is None or r["outcome"] == "DRAW":
            continue
        idx = 0 if x <= cuts[0] else 1 if x <= cuts[1] else 2 if x <= cuts[2] else 3
        groups[idx].append(r["outcome"] == "WIN")
    return " | ".join(
        f"Q{i+1} {sum(g)}/{len(g)}={100*sum(g)/len(g):.1f}%"
        if g else f"Q{i+1} n=0" for i, g in enumerate(groups))


def analyse(records: list[dict], direction: str, period: str) -> list[str]:
    chosen = [r for r in records if r["direction"] == direction and r["period"] == period]
    wins = [r for r in chosen if r["outcome"] == "WIN"]
    losses = [r for r in chosen if r["outcome"] == "LOSS"]
    draws = sum(r["outcome"] == "DRAW" for r in chosen)
    lines = [f"## {direction} / {period}: W={len(wins)} L={len(losses)} D={draws}"]
    tests = []
    samples = {}
    for name in FEATURES:
        a = [r["features"][name] for r in wins if r["features"][name] is not None]
        b = [r["features"][name] for r in losses if r["features"][name] is not None]
        p = mann_whitney_p(a, b)
        tests.append((name, p))
        samples[name] = (a, b, p)
    qvals = benjamini_hochberg(tests)
    lines.append("| Feature | Winners median | Losers median | Cliff delta | MW p | BH q | Quartile win rates |")
    lines.append("|---|---:|---:|---:|---:|---:|---|")
    for name in FEATURES:
        a, b, p = samples[name]
        med_a = statistics.median(a) if a else float("nan")
        med_b = statistics.median(b) if b else float("nan")
        delta = cliff_delta(a, b)
        lines.append(f"| {name} | {med_a:.6g} | {med_b:.6g} | {delta if delta is not None else float('nan'):.3f} | {p if p is not None else float('nan'):.4g} | {qvals[name] if qvals[name] is not None else float('nan'):.4g} | {quartile_rates(chosen, name)} |")
    return lines


def load_m1(path: Path) -> list[Bar]:
    parsed = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        time_col = "datetime_utc" if "datetime_utc" in (reader.fieldnames or []) else "datetime"
        for row in reader:
            ts = parse_time(row[time_col].strip())
            o, h, l, c = (float(row[k]) for k in ("open", "high", "low", "close"))
            if not all(math.isfinite(x) and x > 0 for x in (o, h, l, c)):
                raise ValueError(f"Invalid OHLC at {ts}")
            parsed[ts] = Bar(ts, o, h, l, c)
    return [parsed[t] for t in sorted(parsed)]


def build_ledger(segments: list[list[Bar]], split: datetime, adx_min: float) -> list[dict]:
    ledger = []
    for bars in segments:
        ind = indicators(bars)
        feats = feature_rows(bars)
        for i in range(1, len(bars) - 1):
            prev, cur = ind[i-1], ind[i]
            if any(prev[k] is None or cur[k] is None for k in ("upper", "lower", "willr")):
                continue
            if cur["adx"] is None or cur["adx"] < adx_min:
                continue
            call = bars[i-1].close < prev["lower"] and bars[i].close > cur["lower"] and prev["willr"] <= -80 and cur["willr"] > -80
            put = bars[i-1].close > prev["upper"] and bars[i].close < cur["upper"] and prev["willr"] >= -20 and cur["willr"] < -20
            if not (call or put):
                continue
            nxt = bars[i+1]
            if (nxt.timestamp - cur.timestamp).total_seconds() != 300:
                continue
            change = nxt.close - nxt.open
            direction = "CALL" if call else "PUT"
            outcome = "DRAW" if abs(change) < 1e-12 else (
                "WIN" if (change > 0 if call else change < 0) else "LOSS")
            ledger.append({
                "direction": direction, "outcome": outcome,
                "period": "TRAIN" if cur.timestamp < split else "HOLDOUT",
                "signal_time": cur.timestamp.isoformat(),
                "profit": 0.0 if outcome == "DRAW" else PAYOUT if outcome == "WIN" else -1.0,
                "features": feats[i],
            })
    return ledger


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path("eurusd_history_extended.csv"))
    ap.add_argument("--split-date", default=SPLIT_DATE)
    ap.add_argument("--adx-min", type=float, default=15.0)
    ap.add_argument("--out", type=Path, default=Path("research/WIN_LOSS_FEATURE_AUDIT.md"))
    args = ap.parse_args()
    m1 = load_m1(args.data)
    segments = make_m5(m1)
    split = parse_time(args.split_date)
    ledger = build_ledger(segments, split, args.adx_min)
    lines = [
        "# Direction-separated CALL / PUT winner-vs-loser feature audit",
        "", f"Data: {args.data}; M1 rows={len(m1)}; complete M5 bars={sum(map(len, segments))}; segments={len(segments)}.",
        f"Split: {split.isoformat()}; ADX >= {args.adx_min:g}; payout 92%; next M5 candle settlement.",
        "All predictors are measured on the fully closed signal candle. Draws are reported but excluded from winner/loser tests.",
        "Mann–Whitney p-values use a tie-corrected normal approximation; BH correction is applied separately within each direction/period family.",
        "Naive p-values do not account for serial dependence. This is exploratory and cannot validate a filter.",
        "", f"Eligible trades: {len(ledger)}; CALL={sum(x['direction']=='CALL' for x in ledger)}; PUT={sum(x['direction']=='PUT' for x in ledger)}.",
        ""
    ]
    for direction in ("CALL", "PUT"):
        for period in ("TRAIN", "HOLDOUT"):
            lines.extend(analyse(ledger, direction, period))
            lines.append("")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nReport written: {args.out}")


if __name__ == "__main__":
    main()
