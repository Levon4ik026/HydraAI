#!/usr/bin/env python3
"""Quarterly and payout-stress audit for the frozen exact-reversal cohort.

Cohort selection is TRAIN-only and inherited from reversal_strategy_audit.py.
This script does not optimize parameters or select a regime filter.
"""
from __future__ import annotations

import argparse
from datetime import timedelta
from collections import defaultdict
from pathlib import Path

from reversal_strategy_audit import (
    MIN_TRAIN_TRADES, MAX_TRAIN_WR, invert_outcome, build_records
)
from standalone_strategy_screen import make_m5, read_m1, summarize

PAYOUTS = (0.92, 0.90, 0.88, 0.85, 0.80)


def inverse_counts(rows):
    outcomes = [invert_outcome(row[6]) for row in rows]
    return outcomes.count("W"), outcomes.count("L"), outcomes.count("D")


def net_at(w, l, payout):
    return w * payout - l


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("research/REVERSAL_ROBUSTNESS.md"))
    args = ap.parse_args()

    m1 = read_m1(args.data)
    segments = make_m5(m1)
    d1, d2, accepted = build_records(segments)
    train = {
        (name, horizon): summarize([r[6] for r in rows])
        for (name, horizon, period), rows in accepted.items()
        if period == "TRAIN"
    }
    frozen = sorted(
        key for key, stats in train.items()
        if stats["n"] >= MIN_TRAIN_TRADES and stats["wr"] is not None
        and stats["wr"] <= MAX_TRAIN_WR and stats["net"] < 0
    )

    segment_bars = {sid: bars for sid, bars in enumerate(segments)}
    quarterly = defaultdict(list)
    by_split = defaultdict(list)
    for name, horizon in frozen:
        for period in ("TRAIN", "VALIDATION", "TEST"):
            rows = accepted.get((name, horizon, period), [])
            for row in rows:
                bar = segment_bars[row[2]][row[3]]
                iso = bar.timestamp.isocalendar()
                quarter = f"{bar.timestamp.year}-Q{(bar.timestamp.month - 1)//3 + 1}"
                quarterly[(name, horizon, period, quarter)].append(row)
                by_split[(name, horizon, period)].append(row)

    lines = [
        "# Exact reversal robustness and payout stress",
        "",
        f"Source: {len(m1):,} valid M1 rows; {sum(map(len, segments)):,} complete M5 bars; "
        f"{len(segments)} gap-separated segments.",
        f"Coverage: {m1[0].timestamp.isoformat()} to {m1[-1].timestamp.isoformat()}.",
        f"Splits: TRAIN < {d1}; VALIDATION {d1} through {d2-timedelta(days=1)}; TEST >= {d2}.",
        f"Frozen cohort inherited from TRAIN-only audit: n >= {MIN_TRAIN_TRADES}, "
        f"original decisive WR <= {MAX_TRAIN_WR:.4f}%, original net < 0.",
        "All outcomes are exact paired direction reversals on the same events. "
        "Payout sensitivity changes only WIN credit; losses remain -1u and draws 0u.",
        "This is a robustness diagnostic, not a new selection or parameter-tuning step.",
        "",
        "## Payout sensitivity by split",
        "",
        "| Strategy | Expiry | Split | n | W/L/D | Net @92% | @90% | @88% | @85% | @80% |",
        "|---|---:|---|---:|---|---:|---:|---:|---:|---:|",
    ]
    for key in sorted(by_split):
        name, horizon, period = key
        rows = by_split[key]
        w, l, d = inverse_counts(rows)
        n = w + l + d
        vals = [net_at(w, l, p) for p in PAYOUTS]
        lines.append(
            f"| {name} | {horizon*5}m | {period} | {n} | {w}/{l}/{d} | "
            + " | ".join(f"{v:+.2f}" for v in vals) + " |"
        )

    lines += [
        "",
        "## Quarterly inverse performance at 92% payout",
        "",
        "| Strategy | Expiry | Split | Quarter | n | W/L/D | Decisive WR | Net |",
        "|---|---:|---|---|---:|---|---:|---:|",
    ]
    for key in sorted(quarterly):
        name, horizon, period, quarter = key
        rows = quarterly[key]
        w, l, d = inverse_counts(rows)
        n = w + l + d
        wr = 100 * w / (w + l) if w + l else float("nan")
        lines.append(
            f"| {name} | {horizon*5}m | {period} | {quarter} | {n} | "
            f"{w}/{l}/{d} | {wr:.2f}% | {net_at(w,l,.92):+.2f}u |"
        )

    lines += [
        "",
        "## Interpretation rules",
        "",
        "- A positive aggregate does not establish stability if quarterly results are concentrated in a few periods.",
        "- At 90%, 88%, 85% and 80% payout the report recalculates exact net using the same W/L/D sequence; no win-rate approximation is used.",
        "- Candidate discovery screened 120 distinct strategy/expiry variants, reported across 3 splits (360 variant/split rows). This creates multiple-testing and selection bias; all later-period results are descriptive, not a new independent holdout.",
        "- Dukascopy BID candles are not Pocket Option executable quotes. Spread, latency, quote differences, payout changes by instrument/time, and execution rejection are not modeled.",
        "- No strategy is approved for live use; no trades are executed.",
        "",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {args.out}; frozen_candidates={len(frozen)}; M1={len(m1)}; M5={sum(map(len, segments))}")


if __name__ == "__main__":
    main()
