#!/usr/bin/env python3
"""Jointly matched signal-vs-market benchmark: EMA bias x ATR tertile x ADX band.

Exploratory only. Regimes are causal and defined at signal-candle close.
"""
from __future__ import annotations
import argparse
from pathlib import Path
try:
    from .win_loss_feature_audit import SPLIT_DATE, load_m1, make_m5, parse_time, build_ledger, feature_rows
    from .market_regime_audit import classify_regimes
except ImportError:
    from win_loss_feature_audit import SPLIT_DATE, load_m1, make_m5, parse_time, build_ledger, feature_rows
    from market_regime_audit import classify_regimes

PAYOUT = 0.92

def wilson(w, n):
    if not n: return None, None
    z=1.959963984540054; p=w/n; d=1+z*z/n
    c=(p+z*z/(2*n))/d; h=z*(p*(1-p)/n+z*z/(4*n*n))**0.5/d
    return c-h,c+h

def rate(w,n):
    if not n: return "—"
    lo,hi=wilson(w,n)
    return f"{w/n:.1%} [{lo:.1%},{hi:.1%}]"

def key(state):
    if not state or any(state.get(k) is None for k in ("trend_bias","volatility","trend_strength")): return None
    return "|".join(state[k] for k in ("trend_bias","volatility","trend_strength"))

def counts(rows, direction):
    w=d=0
    for r in rows:
        if "outcome" in r:
            w += r["outcome"]=="WIN"; d += r["outcome"]=="DRAW"
        else:
            w += bool(r["up"] if direction=="CALL" else r["down"]); d += r["draw"]
    return w,len(rows)-w-d,d

def build_background(segments, split, signal_times):
    out=[]
    for bars in segments:
        feats=feature_rows(bars); states=classify_regimes(bars,feats)
        for i in range(len(bars)-1):
            cur,nxt=bars[i],bars[i+1]
            if (nxt.timestamp-cur.timestamp).total_seconds()!=300: continue
            k=key(states[i]); ts=cur.timestamp.isoformat()
            if k is None or ts in signal_times: continue
            delta=nxt.close-nxt.open
            out.append({"period":"TRAIN" if cur.timestamp<split else "HOLDOUT","key":k,
                        "up":delta>1e-12,"down":delta< -1e-12,"draw":abs(delta)<=1e-12})
    return out

def report(ledger, background, states, split):
    lines=["# Jointly matched signal vs market baseline","",
    f"Frozen BB(20,2)/Williams %R(14) re-entry + ADX>=15; split={split}; payout=92%; next M5 candle.",
    "Exact matching key = EMA20-EMA50 bias × prior-120-bar ATR14/close tertile × ADX band (<20, 20–<30, >=30).",
    "Background includes every eligible non-signal candle with a contiguous next M5 candle; all signal timestamps excluded.",
    "Only causal variables available at the signal close define cells. CALL and PUT are scored against the same directional background outcome.",
    "Wilson intervals are descriptive; they do not correct serial dependence, overlapping contexts, or multiple cell inspection. Historical holdout has already been inspected.",
    "Cells with fewer than 10 signal decisive outcomes are explicitly exploratory and not interpretable as reliable evidence. No filter selection.",
    "",
    "| Direction | Period | Joint regime | Signal n W/L/D | Signal WR (95% Wilson) | Net u | Background n W/L/D | Background WR (95% Wilson) | Lift |",
    "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for direction in ("CALL","PUT"):
      for period in ("TRAIN","HOLDOUT"):
        sig=[x for x in ledger if x["direction"]==direction and x["period"]==period]
        bg_period=[x for x in background if x["period"]==period]
        keys=sorted({key(states[x["signal_time"]]) for x in sig if key(states[x["signal_time"]])} |
                    {x["key"] for x in bg_period})
        for k in keys:
          s=[x for x in sig if key(states[x["signal_time"]])==k]
          b=[x for x in bg_period if x["key"]==k]
          sw,sl,sd=counts(s,direction); bw,bl,bd=counts(b,direction)
          sr=sw/(sw+sl) if sw+sl else None; br=bw/(bw+bl) if bw+bl else None
          lift="—" if sr is None or br is None else f"{(sr-br)*100:+.1f} pp"
          net=PAYOUT*sw-sl
          label=k + (" ⚠ small n" if sw+sl<10 else "")
          lines.append(f"| {direction} | {period} | {label} | {len(s)} {sw}/{sl}/{sd} | {rate(sw,sw+sl)} | {net:+.2f} | {len(b)} {bw}/{bl}/{bd} | {rate(bw,bw+bl)} | {lift} |")
    lines += ["","## Interpretation rules","",
    "- The decisive WR break-even at 92% payout is 52.08%; net units are included to reflect payout asymmetry.",
    "- Positive lift is descriptive incremental performance within the exact joint regime, not causal proof.",
    "- A missing or tiny cell is inconclusive, not evidence of zero effect. Do not pool directions or train/holdout.",
    "- Even cells with adequate counts remain serially dependent; these intervals are not valid independent-trade confidence claims.",
    "- Do not implement a regime filter from this historical audit. The next meaningful confirmation is a frozen prospective test on fresh continuous non-OTC data."]
    return "\n".join(lines)+"\n"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,default=Path("eurusd_history_extended.csv"))
    ap.add_argument("--split-date",default=SPLIT_DATE)
    ap.add_argument("--adx-min",type=float,default=15.0)
    ap.add_argument("--out",type=Path,default=Path("research/JOINT_MATCHED_BASELINE.md"))
    a=ap.parse_args()
    m1=load_m1(a.data); segments=make_m5(m1); split=parse_time(a.split_date)
    ledger=build_ledger(segments,split,a.adx_min)
    states={}
    for bars in segments:
        for bar,state in zip(bars,classify_regimes(bars,feature_rows(bars))):
            states[bar.timestamp.isoformat()]=state
    bg=build_background(segments,split,{x["signal_time"] for x in ledger})
    out=report(ledger,bg,states,split.isoformat())
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(out,encoding="utf-8")
    print(out); print(f"Signals={len(ledger)}; baseline={len(bg)}")

if __name__=="__main__": main()
