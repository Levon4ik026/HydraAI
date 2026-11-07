#!/usr/bin/env python3
"""Day-cluster bootstrap for frozen interaction rules; no parameter selection.

Resamples UTC signal days as blocks, preserving within-day serial dependence.
Rules and thresholds are copied from the already-frozen train-only screen.
This is a sensitivity analysis, not independent validation.
"""
from __future__ import annotations

import argparse
import random
import statistics
from collections import defaultdict
from pathlib import Path

from win_loss_feature_audit import SPLIT_DATE, load_m1, make_m5, parse_time, build_ledger

PAYOUT = 0.92
REPLICATES = 20000
SEED = 20261108
RULES = {
    "CALL": ("ema20_50_atr", -0.43772535, "body_range", 0.56454248, "HL"),
    "PUT": ("atr14_close", 0.00029368424, "upper_wick_range", 0.19354839, "HH"),
}


def profit(outcome: str) -> float:
    return PAYOUT if outcome == "WIN" else -1.0 if outcome == "LOSS" else 0.0


def day_metrics(records: list[dict]) -> tuple[float, int, int, int]:
    wins = sum(r["outcome"] == "WIN" for r in records)
    losses = sum(r["outcome"] == "LOSS" for r in records)
    draws = sum(r["outcome"] == "DRAW" for r in records)
    net = sum(profit(r["outcome"]) for r in records)
    return net, wins, losses, draws


def percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("percentile requires observations")
    pos = (len(ordered) - 1) * p
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def bootstrap(records: list[dict], filtered: list[dict], replicates: int = REPLICATES,
              seed: int = SEED) -> dict:
    """Paired UTC-day block bootstrap for base/filter net and decisive WR."""
    days = sorted({r["signal_time"][:10] for r in records})
    if len(days) < 2:
        raise ValueError("at least two signal days are required")
    base_by_day = defaultdict(list)
    filt_by_day = defaultdict(list)
    for row in records:
        base_by_day[row["signal_time"][:10]].append(row)
    for row in filtered:
        filt_by_day[row["signal_time"][:10]].append(row)

    rng = random.Random(seed)
    base_net, filt_net, delta_net = [], [], []
    base_wr, filt_wr = [], []
    for _ in range(replicates):
        sampled = [days[rng.randrange(len(days))] for _ in days]
        bnet = fnet = bw = bl = fw = fl = 0
        for day in sampled:
            bn, bwi, bli, _ = day_metrics(base_by_day[day])
            fn, fwi, fli, _ = day_metrics(filt_by_day[day])
            bnet += bn
            fnet += fn
            bw += bwi
            bl += bli
            fw += fwi
            fl += fli
        base_net.append(bnet)
        filt_net.append(fnet)
        delta_net.append(fnet - bnet)
        if bw + bl:
            base_wr.append(100 * bw / (bw + bl))
        if fw + fl:
            filt_wr.append(100 * fw / (fw + fl))

    def ci(vals):
        return (percentile(vals, .025), percentile(vals, .975)) if vals else (None, None)

    return {
        "days": len(days),
        "base_net_ci": ci(base_net),
        "filter_net_ci": ci(filt_net),
        "delta_net_ci": ci(delta_net),
        "base_wr_ci": ci(base_wr),
        "filter_wr_ci": ci(filt_wr),
    }


def fmt_ci(value):
    return "not estimable" if value[0] is None else f"[{value[0]:+.2f}, {value[1]:+.2f}]"


def fmt_wr(value):
    return "not estimable" if value[0] is None else f"[{value[0]:.2f}%, {value[1]:.2f}%]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path("eurusd_history_extended.csv"))
    ap.add_argument("--out", type=Path, default=Path("research/CLUSTER_BOOTSTRAP_2026-11-08.md"))
    ap.add_argument("--replicates", type=int, default=REPLICATES)
    args = ap.parse_args()
    if args.replicates < 1000:
        raise ValueError("use at least 1000 bootstrap replicates")

    m1 = load_m1(args.data)
    segments = make_m5(m1)
    ledger = build_ledger(segments, parse_time(SPLIT_DATE), 15.0)
    holdout = [r for r in ledger if r["period"] == "HOLDOUT"]
    lines = [
        "# Paired UTC-day cluster bootstrap: frozen interaction rules", "",
        f"Dataset: {args.data}; M1={len(m1)}; M5={sum(map(len, segments))}; eligible events={len(ledger)}.",
        f"Bootstrap: {args.replicates:,} replicates; seed={SEED}; resampling unit=UTC signal day.",
        "Rules were frozen in the prior train-only screen. This script does not select features, thresholds, or rules.",
        "Intervals are percentile 95% cluster-bootstrap intervals. They preserve within-day dependence but cannot correct for strategy selection, regime drift, or the already-inspected historical holdout.",
        "Net convention: WIN +0.92u, LOSS -1u, DRAW 0u. Difference is filter net minus unfiltered base net on the same resampled days.",
        "", "## Historical holdout sensitivity (not independent confirmation)",
    ]
    for direction, rule in RULES.items():
        xname, xcut, yname, ycut, cell = rule
        base = [r for r in holdout if r["direction"] == direction]
        filt = []
        for row in base:
            xval, yval = row["features"][xname], row["features"][yname]
            if xval is None or yval is None:
                continue
            key = ("H" if xval > xcut else "L") + ("H" if yval > ycut else "L")
            if key == cell:
                filt.append(row)
        if not base:
            lines.append(f"### {direction}\nNo holdout events.")
            continue
        b = day_metrics(base)
        f = day_metrics(filt)
        result = bootstrap(base, filt, args.replicates, SEED + (0 if direction == "CALL" else 1))
        lines += [
            f"### {direction}",
            f"- Frozen rule: {xname} {'>' if cell[0]=='H' else '<='} {xcut:.8g}; {yname} {'>' if cell[1]=='H' else '<='} {ycut:.8g}.",
            f"- Signal days: {result['days']}; base n={len(base)} W/L/D={b[1]}/{b[2]}/{b[3]} net={b[0]:+.2f}u.",
            f"- Filter n={len(filt)} W/L/D={f[1]}/{f[2]}/{f[3]} net={f[0]:+.2f}u.",
            f"- Base net 95% day-bootstrap CI: {fmt_ci(result['base_net_ci'])}; decisive WR CI: {fmt_wr(result['base_wr_ci'])}.",
            f"- Filter net 95% day-bootstrap CI: {fmt_ci(result['filter_net_ci'])}; decisive WR CI: {fmt_wr(result['filter_wr_ci'])}.",
            f"- Paired incremental net (filter - base) 95% CI: {fmt_ci(result['delta_net_ci'])}.",
        ]
    lines += [
        "", "## Interpretation guardrails",
        "- A CI spanning zero does not prove no edge; it means this sample does not resolve the sign reliably.",
        "- Positive incremental net on this already-inspected holdout is not confirmation. Negative incremental net is a reason not to promote the rule.",
        "- The CALL filter's prior point estimate was slightly worse than base and covered 43.8% of signals; the paired cluster interval quantifies how unstable that comparison is across signal days.",
        "- The PUT filter covered only two holdout trades. Its cluster bootstrap is expected to be extremely wide and should not be used to claim performance.",
        "- Next valid evidence must come from prospective, continuous, non-OTC candles with the exact rules frozen before collection.",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"Report written: {args.out}")


if __name__ == "__main__":
    main()
