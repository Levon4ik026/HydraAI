#!/usr/bin/env python3
"""Exact opposite-direction audit of deliberately weak standalone signals.

Selection is TRAIN-only: at least 100 accepted non-overlapping trades and
decisive WR below the 92%-payout inverse break-even threshold (47.9167%), with negative TRAIN net. The inverse uses the exact
same signal events, entry prices, expiry bars and trade schedule; only CALL
and PUT direction is flipped. No parameter tuning or holdout-based selection.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

from standalone_strategy_screen import (
    HORIZONS,
    PAYOUT,
    build_specs,
    make_m5,
    read_m1,
    signals_for_segment,
    split_dates,
    summarize,
    outcome,
)

MIN_TRAIN_TRADES = 100
MAX_TRAIN_WR = 47.9167


def invert_outcome(value: str) -> str:
    if value == "W":
        return "L"
    if value == "L":
        return "W"
    if value == "D":
        return "D"
    raise ValueError(f"Unknown outcome: {value}")


def build_records(segments):
    d1, d2 = split_dates(segments)
    records = []
    specs = build_specs()
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
                        records.append(
                            (name, horizon, sid, i, side, period,
                             outcome(bars, i, side, horizon))
                        )
    # Match the standalone screen's one-position schedule independently
    # for each signal family, expiry, period and gap-separated segment.
    raw_by_segment = defaultdict(list)
    raw_by_strategy = defaultdict(list)
    for row in records:
        raw_by_segment[(row[0], row[1], row[5], row[2])].append(row)
        raw_by_strategy[(row[0], row[1], row[5])].append(row)

    accepted = defaultdict(list)
    for key, rows in raw_by_segment.items():
        next_i = -1
        for row in sorted(rows, key=lambda item: item[3]):
            if row[3] >= next_i:
                accepted[key[:3]].append(row)
                next_i = row[3] + key[1]
    return d1, d2, accepted


def fmt(summary):
    ci = summary["wilson"]
    ci_text = "n/a" if ci is None else f"[{ci[0]:.2f}, {ci[1]:.2f}]%"
    wr_text = "n/a" if summary["wr"] is None else f'{summary["wr"]:.2f}%'
    pf_text = "inf" if summary["pf"] == float("inf") else f'{summary["pf"]:.2f}'
    return (
        f'{summary["n"]} | {summary["w"]}/{summary["l"]}/{summary["d"]} | '
        f'{wr_text} {ci_text} | {summary["net"]:+.2f}u | '
        f'{summary["roi"]:+.2f}% | {pf_text} | '
        f'{summary["max_dd"]:.2f}u | {summary["max_losing_streak"]}'
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument(
        "--out", type=Path,
        default=Path("research/REVERSAL_STRATEGY_AUDIT.md")
    )
    args = parser.parse_args()

    m1 = read_m1(args.data)
    segments = make_m5(m1)
    d1, d2, accepted = build_records(segments)

    train_stats = {}
    for (name, horizon, period), rows in accepted.items():
        if period == "TRAIN":
            train_stats[(name, horizon)] = summarize([r[6] for r in rows])

    # Freeze the weak-signal cohort using TRAIN only. VALIDATION and TEST
    # are evaluated after this list is fixed and cannot add/remove candidates.
    selected = sorted(
        key for key, stats in train_stats.items()
        if stats["n"] >= MIN_TRAIN_TRADES
        and stats["wr"] is not None
        and stats["wr"] <= MAX_TRAIN_WR
        and stats["net"] < 0
    )

    period_bars = {"TRAIN": 0, "VALIDATION": 0, "TEST": 0}
    period_days = {"TRAIN": set(), "VALIDATION": set(), "TEST": set()}
    for segment in segments:
        for bar in segment:
            day = bar.timestamp.date()
            period = "TRAIN" if day < d1 else "VALIDATION" if day < d2 else "TEST"
            period_bars[period] += 1
            period_days[period].add(day)

    lines = [
        "# Exact signal-reversal audit — EURUSD M5",
        "",
        f"Source: Dukascopy EURUSD M1 BID; {len(m1):,} valid M1 rows; "
        f"{sum(map(len, segments)):,} complete M5 bars; {len(segments)} "
        "gap-separated segments.",
        f"Coverage: {m1[0].timestamp.isoformat()} to {m1[-1].timestamp.isoformat()}.",
        f"Chronological split inherited from standalone screen: TRAIN < {d1}; "
        f"VALIDATION {d1} through {d2}; TEST >= {d2}.",
        f"Selection frozen on TRAIN only: n >= {MIN_TRAIN_TRADES}, "
        f"original decisive WR <= {MAX_TRAIN_WR:.2f}%, and original net < 0.",
        "Payout: WIN +0.92u, LOSS -1u, DRAW 0u; decisive break-even WR 52.0833%.",
        "Signal is evaluated after the closed M5 bar; entry is next M5 open; "
        "expiry is close of the Nth subsequent M5 bar.",
        "One-position non-overlap is enforced independently per strategy/expiry/period/segment.",
        "The inverse is a strict paired counterfactual: identical accepted signal "
        "timestamps, entry and expiry; only CALL/PUT is flipped. W and L swap; "
        "D remains D. No signal is added, removed or retimed.",
        "No transaction costs or Pocket Option quote simulation; Dukascopy BID "
        "is not the platform's executable price stream.",
        "",
        "## Frozen weak-signal cohort",
        "",
        "| Original strategy | Expiry | TRAIN n | Original W/L/D | Original decisive WR | Original net |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    for name, horizon in selected:
        rows = accepted[(name, horizon, "TRAIN")]
        s = summarize([r[6] for r in rows])
        lines.append(
            f'| {name} | {horizon*5}m | {s["n"]} | '
            f'{s["w"]}/{s["l"]}/{s["d"]} | {s["wr"]:.2f}% | {s["net"]:+.2f}u |'
        )

    lines += [
        "",
        "## Paired original vs exact inverse",
        "",
        "| Original strategy | Expiry | Split | Original n W/L/D | Original WR [95% Wilson] | Original net | Inverse n W/L/D | Inverse WR [95% Wilson] | Inverse net | Inverse ROI | Inverse PF | Inverse max DD | Inverse max loss streak |",
        "|---|---:|---|---|---|---:|---|---|---:|---:|---:|---:|---:|",
    ]

    for name, horizon in selected:
        for period in ("TRAIN", "VALIDATION", "TEST"):
            rows = sorted(
                accepted.get((name, horizon, period), []),
                key=lambda r: (r[2], r[3])
            )
            if not rows:
                continue
            original = [r[6] for r in rows]
            inverse = [invert_outcome(value) for value in original]
            so = summarize(original)
            si = summarize(inverse)
            lines.append(
                f'| {name} | {horizon*5}m | {period} | '
                f'{so["n"]} {so["w"]}/{so["l"]}/{so["d"]} | '
                f'{so["wr"]:.2f}% [{so["wilson"][0]:.2f}, {so["wilson"][1]:.2f}]% | '
                f'{so["net"]:+.2f}u | '
                f'{si["n"]} {si["w"]}/{si["l"]}/{si["d"]} | '
                f'{si["wr"]:.2f}% [{si["wilson"][0]:.2f}, {si["wilson"][1]:.2f}]% | '
                f'{si["net"]:+.2f}u | {si["roi"]:+.2f}% | '
                f'{si["pf"]:.2f} | {si["max_dd"]:.2f}u | '
                f'{si["max_losing_streak"]} |'
            )

    lines += [
        "",
        "## Coverage and interpretation",
        "",
        "| Split | M5 bars | Calendar days |",
        "|---|---:|---:|",
    ]
    for period in ("TRAIN", "VALIDATION", "TEST"):
        lines.append(
            f'| {period} | {period_bars[period]} | {len(period_days[period])} |'
        )
    lines += [
        "",
        "- Inverse and original are paired on exactly the same accepted trade timestamps; "
        "the comparison is not against a newly sampled strategy.",
        "- The 50% random-direction reference has negative expectancy at 92% payout "
        "(-0.04u per decisive trade); break-even is 52.0833%.",
        "- Wilson intervals are descriptive and assume independent decisive outcomes; "
        "serial dependence and clustering make them optimistic.",
        "- Candidate selection used TRAIN only. VALIDATION is the first check of "
        "whether the weakness persists; TEST is reported descriptively but is not "
        "a fresh untouched holdout and must not be treated as confirmation.",
        "- Small candidate counts, short coverage, multiple strategy-family screening, "
        "and possible regime changes limit inference.",
        "- No strategy was deployed and no trade was executed.",
        "",
    ]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(
        f"Wrote {args.out}; selected={len(selected)}; M1={len(m1)}; "
        f"M5={sum(map(len, segments))}; split={d1}/{d2}"
    )


if __name__ == "__main__":
    main()
