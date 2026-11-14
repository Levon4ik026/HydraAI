#!/usr/bin/env python3
"""HYD-CAND-013: profile May/October 2026 seed situations and find historical analogs.

Exploratory only: May/October are already-inspected TEST cohorts. Their causal
pre-entry feature profile is used as a seed to retrieve TRAIN/VALIDATION analogs.
The candidate rule, direction, entry, expiry, non-overlap and payout remain frozen.
"""
from __future__ import annotations
import argparse
import math
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from statistics import median

from expanded_strategy_screen import read_m1, outcome, stats
from long_history_validation import make_m5
from eleventh_wave_impulse_screen import build_events

NAME = "BULL_IMPULSE_CONT_R2.0_C0.75"
H = 4
PAYOUT = 0.92
SEED_MONTHS = {"2026-05", "2026-10"}
FEATURES = (
    "efficiency_12", "return_12_atr", "volatility_12_vs_prior60",
    "range_position_24", "ema20_gap_atr", "ema20_slope6_atr",
)

def quantile(xs, q):
    ys = sorted(float(x) for x in xs if math.isfinite(float(x)))
    if not ys:
        return 0.0
    pos = (len(ys)-1)*q
    lo = int(pos); hi = min(lo+1, len(ys)-1)
    return ys[lo] + (ys[hi]-ys[lo])*(pos-lo)

def ema_series(values, period=20):
    alpha = 2.0/(period+1.0)
    out = []
    value = None
    for x in values:
        value = float(x) if value is None else alpha*float(x)+(1-alpha)*value
        out.append(value)
    return out

def causal_features(bars, i, tr, ema20):
    # Every context feature ends at i-1. The completed signal candle i is not
    # used here; its impulse morphology is already fixed by the candidate rule.
    if i < 72:
        return None
    atr20 = sum(tr[i-20:i])/20.0
    if atr20 <= 0:
        return None
    net12 = bars[i-1].close - bars[i-13].close
    path12 = sum(abs(bars[j].close-bars[j-1].close) for j in range(i-12, i))
    hi24 = max(b.high for b in bars[i-24:i])
    lo24 = min(b.low for b in bars[i-24:i])
    span24 = hi24-lo24
    prior60 = sum(tr[i-72:i-12])/60.0
    recent12 = sum(tr[i-12:i])/12.0
    if span24 <= 0 or prior60 <= 0:
        return None
    return {
        "efficiency_12": abs(net12)/path12 if path12 > 0 else 0.0,
        "return_12_atr": net12/atr20,
        "volatility_12_vs_prior60": recent12/prior60,
        "range_position_24": (bars[i-1].close-lo24)/span24,
        "ema20_gap_atr": (bars[i-1].close-ema20[i-1])/atr20,
        "ema20_slope6_atr": (ema20[i-1]-ema20[i-7])/atr20,
    }

def summarize(rows):
    vals = [r["result"] for r in rows]
    s = stats(vals)
    ci = "n/a" if s[5] is None else f"[{s[5][0]:.2f},{s[5][1]:.2f}]%"
    wr = "n/a" if s[4] is None else f"{s[4]:.2f}%"
    return f"N={s[0]} W/L/D={s[1]}/{s[2]}/{s[3]} WR={wr} Net={s[6]:+.2f}u CI={ci}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    m1 = read_m1(a.data)
    segments = make_m5(m1)
    dates = sorted({b.timestamp.date() for seg in segments for b in seg})
    d1, d2 = dates[int(.60*len(dates))], dates[int(.80*len(dates))]

    # Build exactly the registered R2.0/C0.75 event family, inverted to PUT.
    by_segment = []
    for sid, bars in enumerate(segments):
        events = build_events(bars)
        closes = [b.close for b in bars]
        ema20 = ema_series(closes, 20)
        tr = []
        for i, b in enumerate(bars):
            if i == 0:
                tr.append(b.high-b.low)
            else:
                prev = bars[i-1].close
                tr.append(max(b.high-b.low, abs(b.high-prev), abs(b.low-prev)))
        raw = []
        for i, _side in events.get(NAME, []):
            if i+H >= len(bars):
                continue
            ts = bars[i].timestamp
            settle_day = (bars[i+H].timestamp+timedelta(minutes=5)).date()
            day = ts.date()
            split = "TRAIN" if day < d1 else "VALIDATION" if day < d2 else "TEST"
            if (split == "TRAIN" and settle_day >= d1) or (split == "VALIDATION" and settle_day >= d2):
                continue
            feat = causal_features(bars, i, tr, ema20)
            if feat is None:
                continue
            raw.append({"i": i, "ts": ts, "split": split, "month": ts.strftime("%Y-%m"),
                        "result": outcome(bars, i, "PUT", H), "features": feat})
        # Same one-active-trade schedule as the original discovery script,
        # separately for split and continuous segment.
        for split in ("TRAIN", "VALIDATION", "TEST"):
            next_allowed = -1
            for row in sorted((x for x in raw if x["split"] == split), key=lambda x:x["i"]):
                if row["i"] < next_allowed:
                    continue
                next_allowed = row["i"]+H
                row["segment"] = sid
                by_segment.append(row)

    seeds = [r for r in by_segment if r["split"]=="TEST" and r["month"] in SEED_MONTHS]
    if len(seeds) < 30:
        raise SystemExit(f"Too few May/October seed events with complete causal features: {len(seeds)}")
    train = [r for r in by_segment if r["split"]=="TRAIN"]
    val = [r for r in by_segment if r["split"]=="VALIDATION"]
    if len(train) < 100 or len(val) < 50:
        raise SystemExit("Insufficient TRAIN/VALIDATION events for analog profiling")

    # Robust scale is estimated on TRAIN only. The seed profile is the median
    # of May+October TEST causal context. Radius encloses 90% of seed distances.
    scale = {}
    for f in FEATURES:
        q1, q3 = quantile([r["features"][f] for r in train], .25), quantile([r["features"][f] for r in train], .75)
        scale[f] = max(q3-q1, 1e-6)
    center = {f: median([r["features"][f] for r in seeds]) for f in FEATURES}
    def distance(row):
        return math.sqrt(sum(((row["features"][f]-center[f])/scale[f])**2 for f in FEATURES)/len(FEATURES))
    seed_distances = [distance(r) for r in seeds]
    radius = quantile(seed_distances, .90)

    historical = [r for r in by_segment if r["split"] in ("TRAIN","VALIDATION")]
    analogs = [r for r in historical if distance(r) <= radius]
    non_analogs = [r for r in historical if distance(r) > radius]

    lines = [
        "# HYD-CAND-013 — May/October 2026 market-situation analog audit", "",
        f"Data: Dukascopy EUR/USD M1 BID; M1={len(m1):,}; M5={sum(map(len,segments)):,}; segments={len(segments)}.",
        f"Chronological splits retained: TRAIN < {d1}; VALIDATION {d1}–{d2}; TEST >= {d2}; split-crossing outcomes purged.",
        "Frozen candidate: bullish M5 impulse with range >=2.0× mean TR of prior 20 completed M5 bars, body/range >=0.60, close in upper 25%; exact-event inverse PUT.",
        "Execution unchanged: next M5 open, 20m expiry, 92% payout (+0.92u/-1u/0u), one active trade per candidate per continuous segment/split.",
        "Seed cohorts: TEST signal months 2026-05 and 2026-10. They were already inspected in prior reports; using them to define a situation is retrospective/exploratory, not independent confirmation.",
        "Context features use only information available before the signal candle: prior 12-bar efficiency/return, prior volatility ratio, prior 24-bar range position, EMA20 gap and slope. Candidate impulse candle itself is fixed by the frozen signal rule.",
        "Similarity: robust IQR scaling fitted on TRAIN; center = feature-wise median of May+October seed events; radius = 90th percentile of seed distances. This rule is frozen before scoring historical analogs. No candidate parameters are optimized.",
        "Historical analog search is restricted to TRAIN and VALIDATION. Compare analogous candidate events with non-analog candidate events under the same exact trade rules.",
        "Important: analogs are candidate-signal events matching a pre-entry context profile, not all market bars. BID proxy; no Pocket Option spread, variable payout, latency, multiple-testing or serial-dependence correction.", "",
        "## Seed cohort outcomes", "",
        f"- May 2026: {summarize([r for r in seeds if r['month']=='2026-05'])}",
        f"- October 2026: {summarize([r for r in seeds if r['month']=='2026-10'])}",
        f"- Combined seed: {summarize(seeds)}",
        f"- Seed distance radius (90th percentile): {radius:.4f}", "",
        "## Frozen causal situation profile — seed medians", "",
        "| Feature | May+October median | TRAIN IQR scale |",
        "|---|---:|---:|",
    ]
    for f in FEATURES:
        lines.append(f"| {f} | {center[f]:.6f} | {scale[f]:.6f} |")
    lines += ["", "## Historical analog performance (same candidate rules)", "",
              f"- TRAIN analogs: {summarize([r for r in analogs if r['split']=='TRAIN'])}",
              f"- VALIDATION analogs: {summarize([r for r in analogs if r['split']=='VALIDATION'])}",
              f"- TRAIN+VALIDATION analogs: {summarize(analogs)}",
              f"- TRAIN+VALIDATION non-analogs: {summarize(non_analogs)}", "",
              "## Interpretation rules", "",
              "- A positive analog result is evidence for a candidate-specific situation hypothesis, not proof; require adequate N, repeated calendar periods, day-block bootstrap and matched controls.",
              "- If analog performance is materially better than non-analogs and repeats in both TRAIN and VALIDATION, retain the situation-candidate pair for deeper validation.",
              "- If only one split supports it or N is small, keep exploratory; do not promote.",
              "- May/October are seed cohorts from an already-inspected TEST. They cannot serve as independent validation after being used to define the profile.",
              "- No weekday/month filter is introduced; calendar labels are not causal features.",
              ""]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"HYD-CAND-013 situation analog audit complete: seeds={len(seeds)} analogs={len(analogs)} report={a.out}")

if __name__ == "__main__":
    main()
