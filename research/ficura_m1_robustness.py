#!/usr/bin/env python3
"""Day-block robustness audit for the frozen Fičura EUR/USD M1 inverse signal.

No parameter search. Reuses the exact detector, split, entry, expiry and
non-overlap rules from ficura_jump_replication.py. Research-only.
"""
from __future__ import annotations
import argparse
import random
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

from ficura_jump_replication import (
    load_m1, split_segments, make_events, nonoverlap, outcome,
    split_name, SOURCE_PARAMS, BINARY_HORIZONS, PAYOUT,
)

BOOTSTRAPS = 5000
BLOCK_LENGTHS = (5, 10)  # calendar-day moving blocks, includes zero-event days

def score_inverse(seg, event, horizon):
    base = outcome(seg, event, horizon, event["direction"])
    if base is None:
        return None
    delta = base["exit"] - base["entry"]
    # Exact inversion of the original jump direction.
    if event["direction"] == "CALL":
        delta = -delta
    label = "DRAW" if abs(delta) <= 1e-12 else "WIN" if delta > 0 else "LOSS"
    return {
        "outcome": label,
        "signal_ts": event["ts"],
        "settle_ts": base["settle_ts"],
        "day": event["ts"].date(),
        "month": event["ts"].strftime("%Y-%m"),
    }

def net_of(records):
    return sum(PAYOUT if r["outcome"] == "WIN" else -1.0 if r["outcome"] == "LOSS" else 0.0 for r in records)

def summary(records):
    w = sum(r["outcome"] == "WIN" for r in records)
    l = sum(r["outcome"] == "LOSS" for r in records)
    d = sum(r["outcome"] == "DRAW" for r in records)
    return len(records), w, l, d, (100*w/(w+l) if w+l else float("nan")), net_of(records)

def block_bootstrap(records, block_days, iterations, seed):
    if not records:
        return None
    first = min(r["day"] for r in records)
    last = max(r["day"] for r in records)
    days = [first + timedelta(days=i) for i in range((last-first).days+1)]
    by_day = defaultdict(list)
    for r in records:
        by_day[r["day"]].append(r["outcome"])
    rng = random.Random(seed + block_days)
    wrs, nets = [], []
    blocks_needed = (len(days) + block_days - 1) // block_days
    max_start = max(0, len(days)-block_days)
    for _ in range(iterations):
        sampled = []
        for _b in range(blocks_needed):
            start = rng.randint(0, max_start)
            for day in days[start:start+block_days]:
                sampled.extend(by_day.get(day, ()))
        w = sum(x == "WIN" for x in sampled)
        l = sum(x == "LOSS" for x in sampled)
        if w+l:
            wrs.append(100*w/(w+l))
            nets.append(w*PAYOUT-l)
    if not wrs:
        return None
    wrs.sort(); nets.sort()
    def pct(values, p):
        return values[min(len(values)-1, int((len(values)-1)*p))]
    return {
        "wr_lo": pct(wrs, .025), "wr_med": pct(wrs, .5), "wr_hi": pct(wrs, .975),
        "net_lo": pct(nets, .025), "net_med": pct(nets, .5), "net_hi": pct(nets, .975),
        "p_net_positive": 100*sum(x > 0 for x in nets)/len(nets),
        "valid": len(wrs),
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("FICURA_M1_ROBUSTNESS.md"))
    ap.add_argument("--iterations", type=int, default=BOOTSTRAPS)
    args = ap.parse_args()
    m1 = load_m1(args.data)
    tf = 1
    bars = m1
    segments = split_segments(bars, 60)
    k, p, source_h = SOURCE_PARAMS[tf]
    total_returns = max(3, len(bars)-len(segments))
    events = make_events(segments, k, p, total_returns)
    train_end, val_end = int(len(bars)*.60), int(len(bars)*.80)
    lines = [
        "# Fičura M1 inverse — day-block robustness audit", "",
        f"Input rows: {len(m1):,}; events: {len(events):,}; frozen k={k}, p={p}; payout={PAYOUT:.2f}.",
        "Same causal entry (next M1 open), same expiries, same per-expiry non-overlap and same chronological 60/20/20 split as primary report.",
        "This is a robustness audit of the exploratory TEST slice, not independent confirmation. BID-only proxy; not Pocket Option executable quotes.",
        f"Moving-block bootstrap: {args.iterations:,} resamples; calendar-day blocks preserve within-block clustering and zero-event days.",
        "", "## TEST summary and moving-block bootstrap", "",
        "| Expiry | N | W/L/D | WR | Net u | Block days | WR 95% | Net 95% | P(net>0) |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    test_by_h = {}
    for h in BINARY_HORIZONS:
        chosen = nonoverlap(events, h)
        records = []
        for e in chosen:
            seg = segments[e["sid"]]
            r = score_inverse(seg, e, h)
            if r is None:
                continue
            g = e["global"]
            split = split_name(g, train_end, val_end)
            exit_g = g+h
            if (split == "TRAIN" and exit_g >= train_end) or (split == "VALIDATION" and exit_g >= val_end):
                continue
            r["split"] = split
            records.append(r)
        test = sorted((r for r in records if r["split"] == "TEST"), key=lambda x: x["signal_ts"])
        test_by_h[h] = test
        n,w,l,d,wr,net = summary(test)
        for block in BLOCK_LENGTHS:
            b = block_bootstrap(test, block, args.iterations, 20261111+h*101)
            if b:
                lines.append(
                    f"| {h} | {n} | {w}/{l}/{d} | {wr:.2f}% | {net:+.2f} | {block} | "
                    f"[{b['wr_lo']:.2f}, {b['wr_hi']:.2f}] | "
                    f"[{b['net_lo']:+.2f}, {b['net_hi']:+.2f}] | {b['p_net_positive']:.1f}% |"
                )
        lines.append("")
    lines += ["## Monthly TEST breakdown (inverse)", "",
              "| Expiry | Month | N | W/L/D | WR | Net u |",
              "|---:|---|---:|---:|---:|---:|"]
    for h, records in test_by_h.items():
        months = defaultdict(list)
        for r in records:
            months[r["month"]].append(r)
        for month, group in sorted(months.items()):
            n,w,l,d,wr,net = summary(group)
            lines.append(f"| {h} | {month} | {n} | {w}/{l}/{d} | {wr:.2f}% | {net:+.2f} |")
    lines += [
        "", "## Interpretation rules", "",
        "- The block bootstrap is descriptive; 5- and 10-calendar-day blocks are sensitivity checks, not a magical correction for all dependence.",
        "- A positive point estimate is not enough: examine whether the bootstrap net interval straddles zero and whether performance is concentrated in a small number of months.",
        "- Five expiries are reported together; do not select the best-looking expiry without accounting for multiple comparisons.",
        "- The existing TEST slice was previously inspected in Hydra research and is not pristine. Final confirmation requires a future untouched period and quote-level replay.",
        "- The detector threshold uses the full sample's return count n, as in the current replication implementation. A live deployment would need a predeclared, causal n policy; test threshold-length sensitivity before promotion.",
        "",
    ]
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"WROTE={args.out} M1_ROWS={len(m1)} EVENTS={len(events)}")

if __name__ == "__main__":
    main()
