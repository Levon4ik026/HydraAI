#!/usr/bin/env python3
"""Post-hoc causal regime/day diagnostics for the frozen exact-reversal cohort.

This does not select or tune strategies. It reuses the TRAIN-only candidates frozen
by reversal_strategy_audit.py on TRAIN only and partitions their already-fixed
signals by a simple prior-12-bar efficiency-ratio regime.
"""
from __future__ import annotations

import argparse
from datetime import timedelta
from collections import defaultdict
from pathlib import Path

from reversal_strategy_audit import (
    MIN_TRAIN_TRADES, MAX_TRAIN_WR, invert_outcome, build_records
)
from standalone_strategy_screen import (
    build_specs, make_m5, read_m1, signals_for_segment, split_dates,
    summarize, HORIZONS, outcome,
)


def classify_prior_regime(bars, signal_index):
    """Use only completed bars before the signal bar."""
    end = signal_index - 1
    start = end - 12
    if start < 0:
        return "UNKNOWN"
    net_move = bars[end].close - bars[start].close
    path = sum(
        abs(bars[j].close - bars[j - 1].close)
        for j in range(start + 1, end + 1)
    )
    if path <= 1e-12:
        return "RANGE"
    efficiency = abs(net_move) / path
    if efficiency < 0.35:
        return "RANGE"
    return "UP" if net_move > 0 else "DOWN" if net_move < 0 else "RANGE"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path,
                    default=Path("research/REVERSAL_REGIME_DIAGNOSTIC.md"))
    args = ap.parse_args()

    m1 = read_m1(args.data)
    segments = make_m5(m1)
    d1, d2 = split_dates(segments)
    specs = build_specs()
    raw = []
    for sid, bars in enumerate(segments):
        signals = signals_for_segment(bars, specs)
        for name, events in signals.items():
            for horizon in HORIZONS:
                for i, side in events:
                    if i + horizon >= len(bars):
                        continue
                    signal_day = bars[i].timestamp.date()
                    settle_day = bars[i + horizon].timestamp.date()
                    if signal_day < d1:
                        period = "TRAIN" if settle_day < d1 else None
                    elif signal_day < d2:
                        period = "VALIDATION" if settle_day < d2 else None
                    else:
                        period = "TEST"
                    if period:
                        raw.append((name, horizon, sid, i, side, period,
                                    outcome(bars, i, side, horizon)))

    # Same non-overlap rule as the source screen.
    grouped = defaultdict(list)
    for row in raw:
        grouped[(row[0], row[1], row[5], row[2])].append(row)
    accepted = defaultdict(list)
    for key, rows in grouped.items():
        next_i = -1
        for row in sorted(rows, key=lambda r: r[3]):
            if row[3] >= next_i:
                accepted[key[:3]].append(row)
                next_i = row[3] + key[1]

    train = {}
    for (name, horizon, period), rows in accepted.items():
        if period == "TRAIN":
            train[(name, horizon)] = summarize([r[6] for r in rows])
    frozen = sorted(
        key for key, stats in train.items()
        if stats["n"] >= MIN_TRAIN_TRADES
        and stats["wr"] is not None
        and stats["wr"] <= MAX_TRAIN_WR
        and stats["net"] < 0
    )

    # Recreate signal-index -> bar mapping to assign a causal prior-only regime.
    by_segment = {}
    for sid, bars in enumerate(segments):
        by_segment[sid] = bars

    detail = []
    for name, horizon in frozen:
        for period in ("TRAIN", "VALIDATION", "TEST"):
            for row in sorted(accepted.get((name, horizon, period), []),
                              key=lambda r: (r[2], r[3])):
                _, _, sid, i, side, _, original = row
                bars = by_segment[sid]
                regime = classify_prior_regime(bars, i)
                detail.append({
                    "strategy": name, "expiry": horizon * 5,
                    "period": period, "date": bars[i].timestamp.date().isoformat(),
                    "regime": regime, "inverse": invert_outcome(original),
                })

    lines = [
        "# Exact-reversal causal regime and daily diagnostic",
        "",
        f"Source: {len(m1):,} valid Dukascopy M1 rows; "
        f"{sum(map(len, segments)):,} complete M5 bars; "
        f"coverage {m1[0].timestamp.isoformat()} to {m1[-1].timestamp.isoformat()}.",
        f"Splits: TRAIN < {d1}; VALIDATION {d1} through {d2-timedelta(days=1)}; TEST >= {d2}.",
        "Frozen cohort is inherited unchanged from the TRAIN-only reversal audit "
        f"(n >= {MIN_TRAIN_TRADES}, original WR <= {MAX_TRAIN_WR:.1f}%, original net < 0).",
        "Regime uses only the 12 completed M5 bars before the signal candle. "
        "Efficiency ratio = absolute net movement / sum of absolute close-to-close "
        "movements. Ratio < 0.35 is RANGE; otherwise UP or DOWN by net movement.",
        "This is a diagnostic partition, not a new strategy or a threshold optimization.",
        "Inverse outcomes are exact paired W/L swaps; DRAW remains DRAW. Payout 92%.",
        "",
        "## Frozen candidates",
        "",
        "| Strategy | Expiry |",
        "|---|---:|",
    ]
    for name, horizon in frozen:
        lines.append(f"| {name} | {horizon*5}m |")

    lines += [
        "",
        "## Inverse results by split and prior regime",
        "",
        "| Strategy | Expiry | Split | Prior regime | n | W/L/D | Decisive WR | Net u | PF |",
        "|---|---:|---|---|---:|---|---:|---:|---:|",
    ]
    buckets = defaultdict(list)
    for item in detail:
        buckets[(item["strategy"], item["expiry"], item["period"],
                 item["regime"])].append(item["inverse"])
    for key in sorted(buckets):
        s = summarize(buckets[key])
        wr = "n/a" if s["wr"] is None else f'{s["wr"]:.2f}%'
        pf = "inf" if s["pf"] == float("inf") else f'{s["pf"]:.2f}'
        lines.append(
            f"| {key[0]} | {key[1]}m | {key[2]} | {key[3]} | "
            f'{s["n"]} | {s["w"]}/{s["l"]}/{s["d"]} | {wr} | '
            f'{s["net"]:+.2f} | {pf} |'
        )

    lines += [
        "",
        "## Inverse results by UTC signal day",
        "",
        "| Strategy | Expiry | Split | UTC date | n | W/L/D | Decisive WR | Net u |",
        "|---|---:|---|---|---:|---|---:|---:|",
    ]
    days = defaultdict(list)
    for item in detail:
        days[(item["strategy"], item["expiry"], item["period"],
              item["date"])].append(item["inverse"])
    for key in sorted(days):
        s = summarize(days[key])
        wr = "n/a" if s["wr"] is None else f'{s["wr"]:.2f}%'
        lines.append(
            f"| {key[0]} | {key[1]}m | {key[2]} | {key[3]} | "
            f'{s["n"]} | {s["w"]}/{s["l"]}/{s["d"]} | {wr} | {s["net"]:+.2f} |'
        )

    lines += [
        "",
        "## Caveats",
        "",
        "- The prior-regime labels are causal but descriptive; this report does not "
        "prove that a regime filter has predictive value.",
        "- The historical sample spans only a few weeks. Per-day and per-regime "
        "counts are small and highly dependent.",
        "- No thresholds were selected using VALIDATION or TEST. Do not tune a "
        "filter on these diagnostic tables and then report the same periods as "
        "independent confirmation.",
        "- Dukascopy BID candles are not Pocket Option executable quotes; latency, "
        "spread and payout variation are not modeled.",
        "- Research only; no live integration or trades.",
        "",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {args.out}; frozen candidates={len(frozen)}; records={len(detail)}")


if __name__ == "__main__":
    main()
