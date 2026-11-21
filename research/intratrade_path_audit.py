#!/usr/bin/env python3
"""Intratrade path audit for the frozen M5 BB/Williams/ADX signal.

Uses only the saved EURUSD candles. Entry is next M5 open; outcomes settle at
the 1st..5th subsequent M5 close. MFE/MAE use OHLC extremes; intrabar order
is unknowable from M5 OHLC and is never inferred. Paired UTC-day bootstrap
compares 5m and 25m outcomes on identical signal events.
"""
from __future__ import annotations

import argparse
import random
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

try:
    from .reproduce_m5_bb_williams_adx import load_m1, make_m5, build_signals, PAYOUT
except ImportError:
    from reproduce_m5_bb_williams_adx import load_m1, make_m5, build_signals, PAYOUT

PIP = 0.0001
SPLIT = "2026-10-21T19:05:00+00:00"
REPS = 20000
SEED = 20261108


def percentile(values, p):
    values = sorted(values)
    if not values:
        return None
    pos = (len(values) - 1) * p
    lo = int(pos)
    hi = min(lo + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def ci(values):
    return (percentile(values, .025), percentile(values, .975))


def outcome(direction, entry, exit_price):
    delta = (exit_price - entry) * (1 if direction == "CALL" else -1)
    if abs(delta) < 1e-12:
        return "DRAW"
    return "WIN" if delta > 0 else "LOSS"


def profit(result):
    return PAYOUT if result == "WIN" else -1.0 if result == "LOSS" else 0.0


def build_events(rows):
    events = []
    for i, row in enumerate(rows):
        if not row["signal"] or row["adx"] is None or row["adx"] < 15:
            continue
        direction = "CALL" if row["signal"] == 1 else "PUT"
        entry_i = i + 1
        if entry_i >= len(rows):
            continue
        entry_row = rows[entry_i]
        if (entry_row["segment_id"] != row["segment_id"] or
                entry_row["bar"].timestamp - row["bar"].timestamp != timedelta(minutes=5)):
            continue
        path = []
        for h in range(1, 6):
            j = entry_i + h - 1
            if j >= len(rows):
                break
            cur = rows[j]
            if cur["segment_id"] != row["segment_id"]:
                break
            if cur["bar"].timestamp - rows[j-1]["bar"].timestamp != timedelta(minutes=5) if j > entry_i else False:
                break
            path.append(cur)
            close = cur["bar"].close
            signed_close = (close - entry_row["bar"].open) * (1 if direction == "CALL" else -1)
            favorable = ((cur["bar"].high - entry_row["bar"].open) if direction == "CALL"
                         else (entry_row["bar"].open - cur["bar"].low))
            adverse = ((entry_row["bar"].open - cur["bar"].low) if direction == "CALL"
                       else (cur["bar"].high - entry_row["bar"].open))
            # Excursions are cumulative maxima through the current horizon.
            prior = path[:-1]
            if prior:
                favorable = max(favorable, max(
                    ((x["bar"].high - entry_row["bar"].open) if direction == "CALL"
                     else (entry_row["bar"].open - x["bar"].low)) for x in prior))
                adverse = max(adverse, max(
                    ((entry_row["bar"].open - x["bar"].low) if direction == "CALL"
                     else (x["bar"].high - entry_row["bar"].open)) for x in prior))
            result = outcome(direction, entry_row["bar"].open, close)
            events.append({
                "signal_time": row["bar"].timestamp.isoformat(),
                "day": row["bar"].timestamp.date().isoformat(),
                "direction": direction, "h": h, "outcome": result,
                "net": profit(result), "close_pips": signed_close / PIP,
                "mfe_pips": favorable / PIP, "mae_pips": adverse / PIP,
                "period": "PRE_SPLIT" if row["bar"].timestamp.isoformat() < SPLIT else "POST_SPLIT",
            })
    return events


def summary(items):
    w = sum(x["outcome"] == "WIN" for x in items)
    l = sum(x["outcome"] == "LOSS" for x in items)
    d = sum(x["outcome"] == "DRAW" for x in items)
    n = w + l
    return w, l, d, (100*w/n if n else None), sum(x["net"] for x in items)


def paired_day_bootstrap(events, reps=REPS, seed=SEED, h_short=1, h_long=5, direction=None):
    by_signal = defaultdict(dict)
    for x in events:
        if direction is None or x["direction"] == direction:
            by_signal[(x["signal_time"], x["direction"])][x["h"]] = x
    paired = []
    for key, horizons in by_signal.items():
        if h_short in horizons and h_long in horizons:
            paired.append((horizons[h_short], horizons[h_long]))
    by_day = defaultdict(list)
    for short, long in paired:
        by_day[short["day"]].append((short, long))
    days = sorted(by_day)
    if len(days) < 2:
        return {"days": len(days), "n": len(paired), "delta_net_ci": None, "delta_wr_ci": None}
    rng = random.Random(seed)
    net_deltas, wr_deltas = [], []
    for _ in range(reps):
        sample = [days[rng.randrange(len(days))] for _ in days]
        short_w = short_l = long_w = long_l = 0
        delta = 0.0
        for day in sample:
            for short, long in by_day[day]:
                delta += long["net"] - short["net"]
                short_w += short["outcome"] == "WIN"
                short_l += short["outcome"] == "LOSS"
                long_w += long["outcome"] == "WIN"
                long_l += long["outcome"] == "LOSS"
        net_deltas.append(delta)
        sw = 100*short_w/(short_w+short_l) if short_w+short_l else 0
        lw = 100*long_w/(long_w+long_l) if long_w+long_l else 0
        wr_deltas.append(lw-sw)
    return {"days": len(days), "n": len(paired),
            "delta_net_ci": ci(net_deltas), "delta_wr_ci": ci(wr_deltas)}


def fmt_ci(x, suffix=""):
    return "n/a" if x is None else f"[{x[0]:+.2f}, {x[1]:+.2f}]{suffix}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path("eurusd_history_extended.csv"))
    ap.add_argument("--out", type=Path, default=Path("research/INTRATRADE_PATH_AUDIT.md"))
    ap.add_argument("--replicates", type=int, default=REPS)
    args = ap.parse_args()
    m1 = load_m1(args.data)
    segments = make_m5(m1)
    rows = build_signals(segments)
    events = build_events(rows)
    lines = [
        "# HYDRA — Intratrade path and paired expiry audit", "",
        f"Source: {args.data}; M1 rows={len(m1):,}; M5 segments={len(segments)}; M5 bars={sum(map(len, segments)):,}.",
        "Frozen trigger: BB(20,2) re-entry + Williams %R(14) cross; ADX >= 15. Entry next M5 open.",
        "Payout: 92% (WIN +0.92u, LOSS -1u, DRAW 0u). No gaps crossed; no parameters tuned.",
        "MFE/MAE use M5 high/low extremes. OHLC cannot reveal the order of high and low within a candle; no intrabar sequencing is assumed.",
        "Historical post-split data has already been inspected; it is not pristine prospective validation.", "",
        "## Same-event expiry outcomes", "",
        "| Expiry | Side | n | W/L/D | Decisive WR | Net u | Mean MFE pips | Mean MAE pips |",
        "|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for h in range(1, 6):
        for side in ("CALL", "PUT", "ALL"):
            sub = [x for x in events if x["h"] == h and (side == "ALL" or x["direction"] == side)]
            w,l,d,wr,net = summary(sub)
            mfe = sum(x["mfe_pips"] for x in sub)/len(sub) if sub else 0
            mae = sum(x["mae_pips"] for x in sub)/len(sub) if sub else 0
            lines.append(f"| {h*5}m | {side} | {len(sub)} | {w}/{l}/{d} | {wr:.1f}% | {net:+.2f} | {mfe:.2f} | {mae:.2f} |" if wr is not None else f"| {h*5}m | {side} | {len(sub)} | {w}/{l}/{d} | n/a | {net:+.2f} | {mfe:.2f} | {mae:.2f} |")
    lines += ["", "## Excursion profile by final 25-minute outcome", "",
              "These are descriptive event-level path measures, not independent samples.",
              "| Side | Final outcome | n | Mean MFE pips | Median MFE | Mean MAE pips | Median MAE | Mean terminal signed pips |",
              "|---|---|---:|---:|---:|---:|---:|---:|"]
    for side in ("CALL", "PUT"):
        for result in ("WIN", "LOSS", "DRAW"):
            sub = [x for x in events if x["h"] == 5 and x["direction"] == side and x["outcome"] == result]
            if not sub:
                continue
            vals = lambda k: [x[k] for x in sub]
            lines.append(f"| {side} | {result} | {len(sub)} | {sum(vals('mfe_pips'))/len(sub):.2f} | {percentile(vals('mfe_pips'),.5):.2f} | {sum(vals('mae_pips'))/len(sub):.2f} | {percentile(vals('mae_pips'),.5):.2f} | {sum(vals('close_pips'))/len(sub):+.2f} |")
    lines += ["", "## First close-based excursion (25-minute path)", "",
              "Threshold = 1.0 pip from entry, evaluated at completed M5 closes only. This avoids guessing intrabar order.",
              "| Side | First threshold reached | n | Final WIN | Final LOSS | Final DRAW |",
              "|---|---|---:|---:|---:|---:|"]
    for side in ("CALL", "PUT"):
        grouped = defaultdict(list)
        for x in events:
            if x["h"] != 5 or x["direction"] != side:
                continue
            key = ("FAVORABLE_FIRST" if x["close_pips"] >= 1 else "ADVERSE_FIRST" if x["close_pips"] <= -1 else "NO_1PIP_CLOSE_TOUCH")
            # Reconstruct first touch across all horizons for the event.
            event_rows = [z for z in events if z["signal_time"] == x["signal_time"] and z["direction"] == side]
            touched = next((z for z in event_rows if z["close_pips"] >= 1 or z["close_pips"] <= -1), None)
            if touched is not None:
                key = "FAVORABLE_FIRST" if touched["close_pips"] >= 1 else "ADVERSE_FIRST"
            grouped[key].append(x)
        for key, sub in sorted(grouped.items()):
            w,l,d,_,_ = summary(sub)
            lines.append(f"| {side} | {key} | {len(sub)} | {w} | {l} | {d} |")
    lines += ["", "## Paired day-cluster comparisons across expiries", "",
              "Each comparison uses only the same signal events with both expiries available; bootstrap resamples UTC signal days.",
              "| Side | Comparison | Matched n | Days | Incremental net 95% CI (u) | Decisive WR difference 95% CI (pp) |",
              "|---|---:|---:|---:|---:|---:|"]
    comparisons = [(1, 4), (1, 5), (4, 5)]
    for side in ("ALL", "CALL", "PUT"):
        for h_a, h_b in comparisons:
            paired = paired_day_bootstrap(events, args.replicates, SEED + h_a*10 + h_b + (0 if side == "ALL" else 100 if side == "CALL" else 200),
                                          h_short=h_a, h_long=h_b,
                                          direction=None if side == "ALL" else side)
            lines.append(f"| {side} | {h_b*5}m − {h_a*5}m | {paired['n']} | {paired['days']} | {fmt_ci(paired['delta_net_ci'])} | {fmt_ci(paired['delta_wr_ci'], ' pp')} |")
    lines += ["",
              "Intervals preserve within-day dependence but cannot correct strategy selection, regime drift, or the already-inspected historical holdout.", ""]
    lines += ["## Period split: 20m and 25m expiries", "",
              "| Expiry | Period | Side | n | W/L/D | Decisive WR | Net u |",
              "|---:|---|---|---:|---:|---:|---:|"]
    for h in (4, 5):
        for period in ("PRE_SPLIT", "POST_SPLIT"):
            for side in ("CALL", "PUT"):
                sub = [x for x in events if x["h"] == h and x["period"] == period and x["direction"] == side]
                w,l,d,wr,net = summary(sub)
                lines.append(f"| {h*5}m | {period} | {side} | {len(sub)} | {w}/{l}/{d} | {wr:.1f}% | {net:+.2f} |" if wr is not None else f"| {h*5}m | {period} | {side} | {len(sub)} | {w}/{l}/{d} | n/a | {net:+.2f} |")
    lines += ["", "## Guardrails", "",
              "- MFE/MAE are path descriptions, not a tradable stop/target strategy; no stop-loss or take-profit was simulated.",
              "- The first-touch table uses closes only. High/low touch order inside an M5 bar is unknowable from these candles.",
              "- The 5m and 25m outcomes reuse identical signal events and are paired, not independent samples.",
              "- A positive 25m point estimate does not establish that 25m is superior; inspect the paired cluster interval and require fresh prospective data.",
              "- No strategy parameter, filter, expiry, or live application behavior was changed."]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
