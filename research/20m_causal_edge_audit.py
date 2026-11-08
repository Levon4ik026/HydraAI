#!/usr/bin/env python3
"""Causal 20-minute signal-vs-market and pre-entry feature audit.

Frozen BB/Williams/ADX trigger. Entry at next M5 open, settlement at the close
of the 4th M5 candle including the entry candle. Predictors are signal-close
features only. Exact market matching is EMA bias x prior-120-bar ATR tertile
x ADX band. No thresholds are optimized.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from pathlib import Path

try:
    from .win_loss_feature_audit import (
        SPLIT_DATE, FEATURES, load_m1, make_m5, parse_time, feature_rows,
        mann_whitney_p, cliff_delta, benjamini_hochberg,
    )
    from .reproduce_m5_bb_williams_adx import indicators, PAYOUT
except ImportError:
    from win_loss_feature_audit import (
        SPLIT_DATE, FEATURES, load_m1, make_m5, parse_time, feature_rows,
        mann_whitney_p, cliff_delta, benjamini_hochberg,
    )
    from reproduce_m5_bb_williams_adx import indicators, PAYOUT

HORIZON_BARS = 4
VOL_LOOKBACK = 120
VOL_BINS = 3
FEATURES_20M = (
    "rsi14", "adx14", "di_spread", "ema20_50_atr", "bb_z20",
    "bb_width_atr", "atr14_close", "return1_atr", "return3_atr",
    "return6_atr", "return12_atr", "body_range", "upper_wick_range",
    "lower_wick_range", "range_atr", "up_streak", "down_streak",
)


def classify_states(features):
    states = []
    for i, f in enumerate(features):
        atr, adx, ema = f["atr14_close"], f["adx14"], f["ema20_50_atr"]
        vol = None
        if i >= VOL_LOOKBACK and atr is not None:
            hist = [x["atr14_close"] for x in features[i-VOL_LOOKBACK:i]]
            if all(x is not None for x in hist):
                rank = sum(x <= atr for x in hist) / len(hist)
                vol = "LOW" if rank <= 1/3 else "MID" if rank <= 2/3 else "HIGH"
        bias = None if ema is None else ("UP" if ema > 0 else "DOWN" if ema < 0 else "FLAT")
        strength = None if adx is None else ("WEAK" if adx < 20 else "MODERATE" if adx < 30 else "STRONG")
        states.append(None if vol is None or bias is None or strength is None else (bias, vol, strength))
    return states


def build_events(segments, split, adx_min):
    events, backgrounds = [], []
    for bars in segments:
        feats = feature_rows(bars)
        ind = indicators(bars)
        states = classify_states(feats)
        for i in range(len(bars) - HORIZON_BARS):
            if states[i] is None or ind[i]["adx"] is None:
                continue
            # Require an uninterrupted 20-minute path from signal close through settlement.
            if any((bars[j+1].timestamp - bars[j].timestamp).total_seconds() != 300
                   for j in range(i, i + HORIZON_BARS)):
                continue
            entry = bars[i+1].open
            exit_price = bars[i+HORIZON_BARS].close
            delta = exit_price - entry
            bg_outcome = "DRAW" if abs(delta) < 1e-12 else ("UP" if delta > 0 else "DOWN")
            backgrounds.append({
                "time": bars[i].timestamp, "state": states[i],
                "outcome": bg_outcome, "period": "TRAIN" if bars[i].timestamp < split else "HOLDOUT",
            })
            prev, cur = ind[i-1] if i else {}, ind[i]
            if i == 0 or any(prev.get(k) is None or cur.get(k) is None for k in ("upper","lower","willr")):
                continue
            if cur["adx"] is None or cur["adx"] < adx_min:
                continue
            call = bars[i-1].close < prev["lower"] and bars[i].close > cur["lower"] and prev["willr"] <= -80 and cur["willr"] > -80
            put = bars[i-1].close > prev["upper"] and bars[i].close < cur["upper"] and prev["willr"] >= -20 and cur["willr"] < -20
            if not (call or put):
                continue
            direction = "CALL" if call else "PUT"
            signed = delta if call else -delta
            outcome = "DRAW" if abs(signed) < 1e-12 else ("WIN" if signed > 0 else "LOSS")
            events.append({
                "time": bars[i].timestamp, "direction": direction, "state": states[i],
                "period": "TRAIN" if bars[i].timestamp < split else "HOLDOUT",
                "outcome": outcome, "net": 0.0 if outcome == "DRAW" else PAYOUT if outcome == "WIN" else -1.0,
                "features": feats[i],
            })
    return events, backgrounds


def stats(rows, direction=None):
    chosen = [x for x in rows if direction is None or x.get("direction") == direction]
    w = sum(x["outcome"] == "WIN" for x in chosen)
    l = sum(x["outcome"] == "LOSS" for x in chosen)
    d = sum(x["outcome"] == "DRAW" for x in chosen)
    return len(chosen), w, l, d, (100*w/(w+l) if w+l else None), sum(x.get("net",0) for x in chosen)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path("eurusd_history_extended.csv"))
    ap.add_argument("--split-date", default=SPLIT_DATE)
    ap.add_argument("--adx-min", type=float, default=15)
    ap.add_argument("--out", type=Path, default=Path("research/20M_CAUSAL_EDGE_AUDIT.md"))
    args = ap.parse_args()
    m1 = load_m1(args.data)
    segments = make_m5(m1)
    split = parse_time(args.split_date)
    events, background = build_events(segments, split, args.adx_min)
    lines = [
        "# HYDRA — 20-minute causal edge audit", "",
        f"Data: {args.data}; M1={len(m1):,}; M5={sum(map(len,segments)):,}; segments={len(segments)}.",
        "Frozen BB(20,2) re-entry + Williams %R(14) cross; ADX >= 15. Entry next M5 open; exit at close of 4th M5 candle including entry candle (20m).",
        "Payout 92%; WIN +0.92u, LOSS -1u, DRAW 0u. All predictors measured at signal close; no outcome information enters features.",
        "Market baseline uses every eligible non-gap M5 bar with the same 20m entry/exit convention. It is descriptive and serially dependent.",
        "Exact matching state: EMA20-EMA50 bias x ATR14/close tertile (prior 120 bars) x ADX band (<20, 20-<30, >=30).",
        f"Historical split {args.split_date}; holdout already inspected in earlier research and is not pristine.", "",
        "## Signal outcomes", "",
        "| Period | Side | n | W/L/D | Decisive WR | Net u |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for period in ("TRAIN","HOLDOUT","ALL"):
        for side in ("CALL","PUT","ALL"):
            subset=[x for x in events if (period=="ALL" or x["period"]==period) and (side=="ALL" or x["direction"]==side)]
            n,w,l,d,wr,net=stats(subset)
            lines.append(f"| {period} | {side} | {n} | {w}/{l}/{d} | {wr:.1f}% | {net:+.2f} |" if wr is not None else f"| {period} | {side} | {n} | {w}/{l}/{d} | n/a | {net:+.2f} |")
    lines += ["", "## Exact matched market baseline", "",
              "Only events with an available exact state are included. Background excludes all frozen signal timestamps.",
              "| Period | Side | Matched signals | Signal W/L/D | Signal WR | Background n | Background same-direction rate | Lift |",
              "|---|---|---:|---:|---:|---:|---:|---:|"]
    signal_times={x["time"] for x in events}
    bg=[x for x in background if x["time"] not in signal_times]
    for period in ("TRAIN","HOLDOUT"):
        for side in ("CALL","PUT"):
            sig=[x for x in events if x["period"]==period and x["direction"]==side]
            matched=[x for x in sig if x["state"] is not None]
            keys={x["state"] for x in matched}
            base=[x for x in bg if x["period"]==period and x["state"] in keys]
            # Exact per-event cell weighting: compare each signal to background rate in its own exact state.
            rates={}
            for key in keys:
                cell=[x for x in bg if x["period"]==period and x["state"]==key and x["outcome"] in ("UP","DOWN")]
                if cell:
                    rates[key]=sum(x["outcome"]==("UP" if side=="CALL" else "DOWN") for x in cell)/len(cell)
            valid=[x for x in matched if x["state"] in rates]
            expected=sum(rates[x["state"]] for x in valid)/len(valid) if valid else None
            w=sum(x["outcome"]=="WIN" for x in valid); l=sum(x["outcome"]=="LOSS" for x in valid); d=sum(x["outcome"]=="DRAW" for x in valid)
            wr=100*w/(w+l) if w+l else None
            base_n=sum(1 for x in base if x["outcome"] in ("UP","DOWN"))
            lines.append(f"| {period} | {side} | {len(valid)} | {w}/{l}/{d} | {wr:.1f}% | {base_n} | {expected*100:.1f}% | {(wr-expected*100):+.1f} pp |" if wr is not None and expected is not None else f"| {period} | {side} | {len(valid)} | {w}/{l}/{d} | n/a | {base_n} | n/a | n/a |")
    lines += ["", "## Pre-entry winner vs loser features", "",
              "Feature values are fixed at signal close. Draws excluded. Mann–Whitney tests with BH correction across the 17 predeclared features, separately by direction and period.",
              "| Side / period | Feature | Winner median | Loser median | Cliff delta | MW p | BH q |",
              "|---|---|---:|---:|---:|---:|---:|"]
    for side in ("CALL","PUT"):
        for period in ("TRAIN","HOLDOUT"):
            chosen=[x for x in events if x["direction"]==side and x["period"]==period]
            wins=[x for x in chosen if x["outcome"]=="WIN"]
            losses=[x for x in chosen if x["outcome"]=="LOSS"]
            vals={}
            tests=[]
            for name in FEATURES_20M:
                w=[x["features"][name] for x in wins if x["features"].get(name) is not None]
                l=[x["features"][name] for x in losses if x["features"].get(name) is not None]
                p=mann_whitney_p(w,l)
                vals[name]=(w,l,p)
                tests.append((name,p))
            q=benjamini_hochberg(tests)
            for name in FEATURES_20M:
                w,l,p=vals[name]
                import statistics
                wm=statistics.median(w) if w else float("nan")
                lm=statistics.median(l) if l else float("nan")
                cd=cliff_delta(w,l)
                lines.append(f"| {side}/{period} | {name} | {wm:.5g} | {lm:.5g} | {cd if cd is not None else float('nan'):.3f} | {p if p is not None else float('nan'):.4g} | {q[name] if q[name] is not None else float('nan'):.4g} |")
    lines += ["", "## Interpretation guardrails", "",
              "- A feature is not a filter merely because winners and losers differ; require directionally consistent effects, adequate sample, BH-adjusted evidence, and a prospective frozen test.",
              "- Exact matched baseline is descriptive; background bars overlap in time and are not independent.",
              "- A historical holdout already inspected is not independent confirmation.",
              "- No parameters, filters, or application behavior are changed by this audit.", ""]
    args.out.parent.mkdir(parents=True,exist_ok=True)
    report="\n".join(lines)+"\n"
    args.out.write_text(report,encoding="utf-8")
    print(report)


if __name__=="__main__":
    main()
