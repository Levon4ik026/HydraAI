#!/usr/bin/env python3
"""Causal swing-sweep and rejection audit for frozen 20m BB/Williams signals.

All structural predictors use the signal candle and earlier candles only.
Settlement is next M5 open to the close of the 4th M5 candle (20m).
"""
from __future__ import annotations
import argparse
import statistics
from pathlib import Path

try:
    from .win_loss_feature_audit import (
        SPLIT_DATE, load_m1, make_m5, parse_time, feature_rows,
        mann_whitney_p, cliff_delta, benjamini_hochberg,
    )
    from .reproduce_m5_bb_williams_adx import indicators, PAYOUT
except ImportError:
    from win_loss_feature_audit import (
        SPLIT_DATE, load_m1, make_m5, parse_time, feature_rows,
        mann_whitney_p, cliff_delta, benjamini_hochberg,
    )
    from reproduce_m5_bb_williams_adx import indicators, PAYOUT

H = 4
PIP = 0.0001
FEATURES = (
    "sweep_up_12", "sweep_down_12", "sweep_up_24", "sweep_down_24",
    "sweep_up_depth_atr", "sweep_down_depth_atr",
    "close_location", "upper_rejection", "lower_rejection",
    "prior_high_distance_atr", "prior_low_distance_atr",
    "signal_range_atr", "body_direction",
)


def structural_features(bars, i, atr):
    b = bars[i]
    rng = max(b.high - b.low, 1e-12)
    prior12 = bars[max(0, i-12):i]
    prior24 = bars[max(0, i-24):i]
    hi12 = max(x.high for x in prior12) if len(prior12) == 12 else None
    lo12 = min(x.low for x in prior12) if len(prior12) == 12 else None
    hi24 = max(x.high for x in prior24) if len(prior24) == 24 else None
    lo24 = min(x.low for x in prior24) if len(prior24) == 24 else None
    upper = b.high - max(b.open, b.close)
    lower = min(b.open, b.close) - b.low
    return {
        "sweep_up_12": float(hi12 is not None and b.high > hi12 and b.close < hi12),
        "sweep_down_12": float(lo12 is not None and b.low < lo12 and b.close > lo12),
        "sweep_up_24": float(hi24 is not None and b.high > hi24 and b.close < hi24),
        "sweep_down_24": float(lo24 is not None and b.low < lo24 and b.close > lo24),
        "sweep_up_depth_atr": None if hi12 is None or not atr or atr <= 0 else max(0.0, b.high-hi12)/atr,
        "sweep_down_depth_atr": None if lo12 is None or not atr or atr <= 0 else max(0.0, lo12-b.low)/atr,
        "close_location": (b.close-b.low)/rng,
        "upper_rejection": upper/rng,
        "lower_rejection": lower/rng,
        "prior_high_distance_atr": None if hi12 is None or not atr or atr <= 0 else (hi12-b.close)/atr,
        "prior_low_distance_atr": None if lo12 is None or not atr or atr <= 0 else (b.close-lo12)/atr,
        "signal_range_atr": None if not atr or atr <= 0 else rng/atr,
        "body_direction": (b.close-b.open)/rng,
    }


def build_events(segments, split, adx_min=15):
    events=[]
    for bars in segments:
        ind=indicators(bars)
        base=feature_rows(bars)
        for i in range(24, len(bars)-H):
            if any(bars[j+1].timestamp-bars[j].timestamp != __import__("datetime").timedelta(minutes=5)
                   for j in range(i, i+H)):
                continue
            prev,cur=ind[i-1],ind[i]
            if any(prev.get(k) is None or cur.get(k) is None for k in ("upper","lower","willr")):
                continue
            if cur["adx"] is None or cur["adx"] < adx_min:
                continue
            call=(bars[i-1].close < prev["lower"] and bars[i].close > cur["lower"]
                  and prev["willr"] <= -80 and cur["willr"] > -80)
            put=(bars[i-1].close > prev["upper"] and bars[i].close < cur["upper"]
                 and prev["willr"] >= -20 and cur["willr"] < -20)
            if not (call or put):
                continue
            entry=bars[i+1].open
            exitp=bars[i+H].close
            signed=(exitp-entry)*(1 if call else -1)
            outcome="DRAW" if abs(signed)<1e-12 else "WIN" if signed>0 else "LOSS"
            atr=base[i].get("atr14_close")
            atr_abs=atr*bars[i].close if atr is not None else None
            f=structural_features(bars,i,atr_abs)
            events.append({
                "time":bars[i].timestamp.isoformat(),
                "period":"TRAIN" if bars[i].timestamp<split else "HOLDOUT",
                "direction":"CALL" if call else "PUT",
                "outcome":outcome,
                "net":0.0 if outcome=="DRAW" else PAYOUT if outcome=="WIN" else -1.0,
                "features":f,
            })
    return events


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,default=Path("eurusd_history_extended.csv"))
    ap.add_argument("--split-date",default=SPLIT_DATE)
    ap.add_argument("--adx-min",type=float,default=15)
    ap.add_argument("--out",type=Path,default=Path("research/SWING_SWEEP_REJECTION_AUDIT.md"))
    a=ap.parse_args()
    m1=load_m1(a.data); segments=make_m5(m1); split=parse_time(a.split_date)
    events=build_events(segments,split,a.adx_min)
    lines=[
      "# HYDRA — causal swing-sweep / rejection audit","",
      f"Data: {a.data}; M1={len(m1):,}; M5={sum(map(len,segments)):,}; segments={len(segments)}.",
      "Frozen trigger: BB(20,2) re-entry + Williams %R(14) cross; ADX >= 15. Entry next M5 open; exit close of 4th M5 candle (20m).",
      "Payout 92%; WIN +0.92u, LOSS -1u, DRAW 0u. All predictors use signal-close OHLC and the preceding 12/24 completed M5 bars only.",
      "A sweep means price pierces the preceding 12/24-bar extreme but the signal candle closes back inside it. No intrabar ordering is inferred.",
      f"Split: {a.split_date}. Historical holdout has already been inspected; it is exploratory, not pristine prospective validation.",
      "This is a hypothesis audit, not a parameter optimization. BH correction is applied to all 13 features separately in each direction/period.","",
      "## Signal outcomes","",
      "| Period | Side | n | W/L/D | Decisive WR | Net u |",
      "|---|---|---:|---:|---:|---:|"
    ]
    for p in ("TRAIN","HOLDOUT","ALL"):
      for side in ("CALL","PUT","ALL"):
        s=[e for e in events if (p=="ALL" or e["period"]==p) and (side=="ALL" or e["direction"]==side)]
        w=sum(e["outcome"]=="WIN" for e in s); l=sum(e["outcome"]=="LOSS" for e in s); d=sum(e["outcome"]=="DRAW" for e in s)
        wr=f"{100*w/(w+l):.1f}%" if w+l else "n/a"
        lines.append(f"| {p} | {side} | {len(s)} | {w}/{l}/{d} | {wr} | {sum(e['net'] for e in s):+.2f} |")
    lines += ["","## Pre-entry structural feature tests","",
      "Winner-vs-loser Mann–Whitney tests (draws excluded); medians and Cliff delta shown. Binary sweep flags are tested as numeric 0/1.",
      "| Side/period | Feature | Winner median | Loser median | Cliff delta | p | BH q |",
      "|---|---|---:|---:|---:|---:|---:|"]
    for side in ("CALL","PUT"):
      for period in ("TRAIN","HOLDOUT"):
        chosen=[e for e in events if e["direction"]==side and e["period"]==period]
        winners=[e for e in chosen if e["outcome"]=="WIN"]
        losers=[e for e in chosen if e["outcome"]=="LOSS"]
        tests=[]; vals={}
        for name in FEATURES:
          x=[e["features"][name] for e in winners if e["features"][name] is not None]
          y=[e["features"][name] for e in losers if e["features"][name] is not None]
          p=mann_whitney_p(x,y); tests.append((name,p)); vals[name]=(x,y,p)
        q=benjamini_hochberg(tests)
        for name in FEATURES:
          x,y,p=vals[name]
          xm=statistics.median(x) if x else float("nan")
          ym=statistics.median(y) if y else float("nan")
          cd=cliff_delta(x,y)
          lines.append(f"| {side}/{period} | {name} | {xm:.5g} | {ym:.5g} | {cd if cd is not None else float('nan'):.3f} | {p if p is not None else float('nan'):.4g} | {q[name] if q[name] is not None else float('nan'):.4g} |")
    lines += ["","## Guardrails","",
      "- A sweep/rejection feature is not causal proof; the signal itself already contains a band re-entry.",
      "- The historical holdout is reused and cannot count as independent confirmation.",
      "- No filter, threshold, expiry, or application behavior is changed.",
      "- Any candidate must show train/holdout directional consistency, survive multiplicity correction, and then pass a frozen prospective test on fresh candles.",""]
    a.out.parent.mkdir(parents=True,exist_ok=True)
    report="\n".join(lines)
    a.out.write_text(report+"\n",encoding="utf-8")
    print(report)

if __name__=="__main__":
    main()
