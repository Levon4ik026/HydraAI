#!/usr/bin/env python3
"""TRAIN-frozen multi-feature context screen for exact inverse signals.

All context features use completed M5 bars strictly before the signal bar.
The weak strategy cohort is inherited from reversal_strategy_audit.py.
Fixed bins are predeclared; rules are selected on TRAIN only and evaluated
unchanged on VALIDATION/TEST. This is exploratory, not a deployable strategy.
"""
from __future__ import annotations
import argparse, math
from collections import defaultdict
from pathlib import Path
from reversal_strategy_audit import (
    MIN_TRAIN_TRADES, MAX_TRAIN_WR, invert_outcome, build_records
)
from standalone_strategy_screen import make_m5, read_m1, summarize

PAYOUT = 0.92
PAIRS = (("trend", "vol"), ("trend", "location"), ("vol", "location"))

def context(bars, i):
    # Use only bars [i-48, i-1], never the signal candle or future bars.
    if i < 49:
        return None
    prev = bars[i-1]
    c = [bars[j].close for j in range(i-20, i)]
    ema = c[0]
    alpha = 2.0 / 21.0
    for x in c[1:]:
        ema = alpha*x + (1-alpha)*ema
    tr = []
    for j in range(i-48, i):
        b = bars[j]
        pc = bars[j-1].close
        tr.append(max(b.high-b.low, abs(b.high-pc), abs(b.low-pc)))
    recent = sum(tr[-12:]) / 12
    baseline = sum(tr) / len(tr)
    if baseline <= 1e-12:
        return None
    vol = "HIGH" if recent / baseline >= 1.15 else "LOW"
    net = prev.close - bars[i-13].close
    path = sum(abs(bars[j].close-bars[j-1].close) for j in range(i-12, i))
    er = abs(net)/path if path > 1e-12 else 0.0
    trend = "RANGE" if er < 0.30 else ("UP" if net > 0 else "DOWN")
    atr = baseline
    location = "ABOVE" if (prev.close-ema)/atr >= 0 else "BELOW"
    return {"trend":trend, "vol":vol, "location":location}

def pnl(x):
    return PAYOUT if x == "W" else -1.0 if x == "L" else 0.0

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--out",type=Path,default=Path("research/LONG_HISTORY_MULTI_FEATURE_REVERSAL.md"))
    a=ap.parse_args()
    m1=read_m1(a.data); segments=make_m5(m1)
    _,_,accepted=build_records(segments)
    # Freeze the weak original signal cohort on TRAIN only.
    train_stats={(n,h):summarize([r[6] for r in rows])
                 for (n,h,p),rows in accepted.items() if p=="TRAIN"}
    weak=set(k for k,s in train_stats.items() if s["n"]>=MIN_TRAIN_TRADES
             and s["wr"] is not None and s["wr"]<=MAX_TRAIN_WR and s["net"]<0)
    rows_by_key=defaultdict(list)
    for (name,h,period), rows in accepted.items():
        if (name,h) not in weak: continue
        for r in rows:
            name,h,sid,i,side,period,original=r
            feat=context(segments[sid],i)
            if feat is None: continue
            inv=invert_outcome(original)
            for f1,f2 in PAIRS:
                bucket=f"{feat[f1]}+{feat[f2]}"
                rows_by_key[(name,h,f1+"×"+f2,bucket,period)].append(inv)
    # Freeze each exact strategy/expiry/feature-pair/bucket only if TRAIN has
    # >=100 observations, positive net and PF>1. No holdout-based selection.
    frozen=[]
    for key in sorted({k[:4] for k in rows_by_key}):
        vals=rows_by_key.get((*key,"TRAIN"),[])
        s=summarize(vals)
        if s["n"]>=100 and s["net"]>0 and s["pf"]>1:
            frozen.append(key)
    lines=[
      "# Multi-feature causal context screen — exact inverse signals","",
      f"Data: {len(m1):,} valid Dukascopy M1 rows; {sum(map(len,segments)):,} M5 bars.",
      f"Original weak-signal cohort inherited TRAIN-only (n≥{MIN_TRAIN_TRADES}, WR≤{MAX_TRAIN_WR:.4f}%, net<0): {len(weak)} strategy/expiry candidates.",
      "Features use only completed bars before each signal. Fixed bins: trend efficiency over prior 12 bars (RANGE if ER<0.30, else UP/DOWN); volatility HIGH if mean true range over prior 12 bars is ≥1.15× prior-48-bar mean; location ABOVE/BELOW prior-20-bar EMA.",
      "Tested predeclared pairs: trend×volatility, trend×location, volatility×location. No threshold tuning on VALIDATION/TEST.",
      "A rule is frozen only if TRAIN n≥100, inverse net>0 and PF>1. Exact same strategy, expiry and context bucket are then evaluated in later splits.",
      f"Frozen context rules: {len(frozen)}. Payout 92%; WIN +0.92u, LOSS −1u, DRAW 0u.",
      "",
      "| Strategy | Expiry | Feature pair | Context | TRAIN n | TRAIN Net | TRAIN PF | VALIDATION n | VALIDATION Net | TEST n | TEST Net |",
      "|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|"
    ]
    totals=defaultdict(lambda:{"TRAIN":[],"VALIDATION":[],"TEST":[]})
    for name,h,pair,bucket in frozen:
        ss=[]
        for period in ("TRAIN","VALIDATION","TEST"):
            vals=rows_by_key.get((name,h,pair,bucket,period),[])
            s=summarize(vals); ss.append(s)
            totals[(pair,period)][""+period].extend(vals)
        lines.append(f"| {name} | {h*5}m | {pair} | {bucket} | {ss[0]['n']} | {ss[0]['net']:+.2f}u | {ss[0]['pf']:.2f} | {ss[1]['n']} | {ss[1]['net']:+.2f}u | {ss[2]['n']} | {ss[2]['net']:+.2f}u |")
    lines += ["","## Aggregate by feature pair","",
      "| Feature pair | Split | Frozen rules | Trades | W/L/D | Decisive WR | Net |",
      "|---|---|---:|---:|---|---:|---:|"]
    for pair in ("trend×vol","trend×location","vol×location"):
        for period in ("TRAIN","VALIDATION","TEST"):
            vals=totals[(pair,period)][period]
            s=summarize(vals)
            lines.append(f"| {pair} | {period} | {sum(1 for x in frozen if x[2]==pair)} | {s['n']} | {s['w']}/{s['l']}/{s['d']} | {s['wr'] if s['wr'] is not None else 0:.2f}% | {s['net']:+.2f}u |")
    lines += ["","## Interpretation","",
      "- This is a broad exploratory screen: multiple strategy/context combinations are tested; apparent positives require a new untouched forward period.",
      "- Aggregate rows pool frozen rules and may double-count timestamps across different rules; they are not a single executable portfolio.",
      "- Context bins are fixed and causal, but selection on TRAIN can still overfit. VALIDATION/TEST are descriptive, not fresh untouched holdouts.",
      "- Dukascopy BID is not Pocket Option executable pricing; spread, payout changes, latency and execution are not modeled.",
      "- Research only; no live integration or automatic trading."]
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(f"Wrote {a.out}; weak_candidates={len(weak)}; frozen_context_rules={len(frozen)}")
if __name__=="__main__": main()
