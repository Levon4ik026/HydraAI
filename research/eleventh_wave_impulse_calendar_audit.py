#!/usr/bin/env python3
"""Eleventh-wave follow-up: frozen impulse candidates, calendar stability audit.

No parameter search. Rebuilds the original signal definitions and exact entry,
expiry, split purge, and non-overlap rules. Reports monthly, weekday and UTC-hour
breakdowns for four preselected BULL continuation inversions at 92% payout.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

from expanded_strategy_screen import read_m1, outcome, stats
from long_history_validation import make_m5
from eleventh_wave_impulse_screen import build_events

# Frozen shortlist chosen from VALIDATION only, before this audit.
CANDIDATES = (
    ("BULL_IMPULSE_CONT_R1.5_C0.75", 4, "R1.5/C0.75, 20m"),
    ("BULL_IMPULSE_CONT_R2.0_C0.75", 4, "R2.0/C0.75, 20m"),
    ("BULL_IMPULSE_CONT_R2.0_C0.85", 4, "R2.0/C0.85, 20m"),
    ("BULL_IMPULSE_CONT_R2.5_C0.75", 4, "R2.5/C0.75, 20m"),
)

def fmt(xs):
    s = stats(xs)
    wr = "n/a" if s[4] is None else f"{s[4]:.2f}%"
    ci = "n/a" if s[5] is None else f"[{s[5][0]:.2f},{s[5][1]:.2f}]%"
    return f"{s[0]} | {s[1]}/{s[2]}/{s[3]} | {wr} | {s[6]:+.2f}u | {ci}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    m1 = read_m1(a.data)
    segments = make_m5(m1)
    dates = sorted({b.timestamp.date() for seg in segments for b in seg})
    d1, d2 = dates[int(.60*len(dates))], dates[int(.80*len(dates))]

    # Accepted outcomes keyed by frozen candidate, split and signal calendar buckets.
    buckets = defaultdict(list)
    split_rows = defaultdict(list)
    for sid, bars in enumerate(segments):
        events = build_events(bars)
        for name, h, label in CANDIDATES:
            for i, side in events.get(name, []):
                if i+h >= len(bars):
                    continue
                signal_ts = bars[i].timestamp
                settle_ts = bars[i+h].timestamp + timedelta(minutes=5)
                day = signal_ts.date()
                period = "TRAIN" if day < d1 else "VALIDATION" if day < d2 else "TEST"
                if (period == "TRAIN" and settle_ts.date() >= d1) or (period == "VALIDATION" and settle_ts.date() >= d2):
                    continue
                split_rows[(name, h, period, sid)].append((i, signal_ts, outcome(bars, i, "PUT", h)))

    # Same non-overlap policy as the discovery screen, separately per continuous segment.
    for (name, h, period, sid), rows in split_rows.items():
        next_allowed = -1
        for i, ts, result in sorted(rows):
            if i < next_allowed:
                continue
            next_allowed = i+h
            buckets[(name, h, period, "ALL")].append((ts, result))
            buckets[(name, h, period, ts.strftime("%Y-%m"))].append((ts, result))
            buckets[(name, h, period, f"DOW-{ts.strftime('%a')}")].append((ts, result))
            buckets[(name, h, period, f"HOUR-{ts.hour:02d}")].append((ts, result))

    lines = [
        "# Eleventh-wave frozen impulse shortlist: calendar stability audit", "",
        f"Source: Dukascopy EURUSD M1 BID; rows={len(m1):,}; complete M5={sum(map(len,segments)):,}; segments={len(segments)}.",
        f"Coverage: {m1[0].timestamp.isoformat()} — {m1[-1].timestamp.isoformat()}.",
        f"Original chronological split retained: TRAIN < {d1}; VALIDATION {d1}–{d2}; TEST >= {d2}; split-crossing outcomes purged.",
        "Four candidates were frozen from the discovery VALIDATION results only; no thresholds, expiry or direction were re-optimized.",
        "All rows are the INVERTED direction (PUT after bullish impulse). Entry next M5 open; expiry 20m; 92% payout; one active trade per candidate/segment.",
        "Monthly grouping uses signal month; settlement can fall in the following month. UTC weekday/hour are descriptive diagnostics, not filters.",
        "BID-only proxy; no Pocket Option quote, spread, variable payout, latency, multiple-testing correction or serial-dependence correction.", "",
        "## Whole-split results", "",
        "| Frozen candidate | Split | N | W/L/D | Decisive WR | Net | Wilson 95% CI |",
        "|---|---|---:|---|---:|---:|---|",
    ]
    for name, h, label in CANDIDATES:
        for period in ("TRAIN", "VALIDATION", "TEST"):
            xs = [r for r in buckets[(name,h,period,"ALL")]]
            s = stats([x[1] for x in xs])
            ci = "n/a" if s[5] is None else f"[{s[5][0]:.2f},{s[5][1]:.2f}]%"
            wr = "n/a" if s[4] is None else f"{s[4]:.2f}%"
            lines.append(f"| {label} | {period} | {s[0]} | {s[1]}/{s[2]}/{s[3]} | {wr} | {s[6]:+.2f}u | {ci} |")

    lines += ["", "## Monthly outcomes", "",
              "Only months with at least 20 decisive outcomes are shown; smaller months remain in the underlying whole-split totals but are too noisy for standalone interpretation.",
              "| Candidate | Split | Month | N | W/L/D | Decisive WR | Net | Wilson 95% CI |",
              "|---|---|---|---:|---|---:|---:|---|"]
    for name, h, label in CANDIDATES:
        for period in ("TRAIN", "VALIDATION", "TEST"):
            months = sorted(k[3] for k in buckets if k[0]==name and k[1]==h and k[2]==period and len(k[3])==7)
            for month in months:
                xs = [x[1] for x in buckets[(name,h,period,month)]]
                s = stats(xs)
                if s[1]+s[2] < 20:
                    continue
                wr = "n/a" if s[4] is None else f"{s[4]:.2f}%"
                ci = "n/a" if s[5] is None else f"[{s[5][0]:.2f},{s[5][1]:.2f}]%"
                lines.append(f"| {label} | {period} | {month} | {s[0]} | {s[1]}/{s[2]}/{s[3]} | {wr} | {s[6]:+.2f}u | {ci} |")

    lines += ["", "## Weekday diagnostics", "",
              "| Candidate | Split | Weekday UTC | N | Decisive WR | Net |",
              "|---|---|---:|---:|---:|---:|"]
    for name, h, label in CANDIDATES:
        for period in ("TRAIN", "VALIDATION", "TEST"):
            for wd in ("Mon","Tue","Wed","Thu","Fri","Sat","Sun"):
                xs = [x[1] for x in buckets[(name,h,period,f"DOW-{wd}")]]
                s = stats(xs)
                if s[0] < 25:
                    continue
                wr = "n/a" if s[4] is None else f"{s[4]:.2f}%"
                lines.append(f"| {label} | {period} | {wd} | {s[0]} | {wr} | {s[6]:+.2f}u |")

    lines += ["", "## UTC-hour diagnostics", "",
              "| Candidate | Split | UTC hour | N | Decisive WR | Net |",
              "|---|---|---:|---:|---:|---:|"]
    for name, h, label in CANDIDATES:
        for period in ("TRAIN", "VALIDATION", "TEST"):
            for hour in range(24):
                xs = [x[1] for x in buckets[(name,h,period,f"HOUR-{hour:02d}")]]
                s = stats(xs)
                if s[0] < 25:
                    continue
                wr = "n/a" if s[4] is None else f"{s[4]:.2f}%"
                lines.append(f"| {label} | {period} | {hour:02d}:00 | {s[0]} | {wr} | {s[6]:+.2f}u |")

    lines += ["", "## Interpretation guardrails", "",
              "- This is a stability audit of four frozen hypotheses, not another parameter sweep.",
              "- Month, weekday and hour cells are correlated and multiple comparisons still apply; do not turn the best cell into a filter.",
              "- TEST is descriptive and has already been inspected in the discovery wave; it is not pristine independent confirmation.",
              "- A candidate that is strong in one split/month but weak elsewhere is regime-dependent or unstable, not ready for promotion.",
              "- No candidate is promoted. Any survivor requires calendar-day block bootstrap and prospective Pocket Option quote-level replay.", ""]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Frozen impulse calendar audit complete: M1={len(m1):,}; M5={sum(map(len,segments)):,}; candidates={len(CANDIDATES)}; output={a.out}")

if __name__ == "__main__":
    main()
