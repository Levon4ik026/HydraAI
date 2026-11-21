#!/usr/bin/env python3
"""Causal sweep morphology audit; descriptive, no rule selection or tuning."""
from __future__ import annotations
import argparse, statistics
from collections import defaultdict
from pathlib import Path
from long_history_validation import read_duka, make_events, PAYOUT, m5_close_time, chronological_period
from reproduce_m5_bb_williams_adx import make_m5, indicators

HORIZON=4
WARMUP=50

def quantile(values, q):
    xs=sorted(x for x in values if x is not None)
    if not xs: return None
    return xs[min(len(xs)-1, int((len(xs)-1)*q))]

def stats(rows):
    w=sum(r["outcome"]=="WIN" for r in rows)
    l=sum(r["outcome"]=="LOSS" for r in rows)
    d=len(rows)-w-l
    dec=w+l
    return len(rows),w,l,d,(100*w/dec if dec else float("nan")),w*PAYOUT-l

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--out",type=Path,default=Path("research/SWEEP_MORPHOLOGY_AUDIT.md"))
    args=ap.parse_args()
    m1=read_duka(args.data); segments=make_m5(m1); events=make_events(segments,15)
    days=sorted({e["signal_time"].date() for e in events})
    d1,d2=days[int(len(days)*.60)],days[int(len(days)*.80)]
    byseg=defaultdict(list)
    for e in events: byseg[e["segment"]].append(e)
    rows=[]
    for sid,bars in enumerate(segments):
        if not byseg[sid]: continue
        ind=indicators(bars)
        tr=[None]*len(bars)
        for i in range(1,len(bars)):
            b,p=bars[i],bars[i-1]
            tr[i]=max(b.high-b.low,abs(b.high-p.close),abs(b.low-p.close))
        atr=[None]*len(bars)
        for i in range(14,len(bars)):
            vals=tr[i-13:i+1]
            if all(v is not None for v in vals): atr[i]=sum(vals)/14
        for e in byseg[sid]:
            i=e["bar_index"]
            if i<WARMUP or i+HORIZON>=len(bars) or not atr[i] or ind[i]["adx"] is None: continue
            cur=bars[i]; prev=bars[i-12:i]
            if e["direction"]=="CALL":
                level=min(b.low for b in prev)
                penetration=level-cur.low
                reclaimed=cur.close-level
                wick=max(0,min(cur.open,cur.close)-cur.low)
                aligned=penetration>0 and reclaimed>0
                close_loc=(cur.close-cur.low)/(cur.high-cur.low) if cur.high>cur.low else .5
            else:
                level=max(b.high for b in prev)
                penetration=cur.high-level
                reclaimed=level-cur.close
                wick=max(0,cur.high-max(cur.open,cur.close))
                aligned=penetration>0 and reclaimed>0
                close_loc=(cur.high-cur.close)/(cur.high-cur.low) if cur.high>cur.low else .5
            if not aligned: continue
            span=max(cur.high-cur.low,1e-12)
            settle=m5_close_time(bars[i+HORIZON].timestamp)
            period=chronological_period(cur.timestamp,settle,d1,d2)
            if period is None: continue
            delta=bars[i+HORIZON].close-bars[i+1].open
            signed=delta if e["direction"]=="CALL" else -delta
            outcome="DRAW" if abs(signed)<1e-12 else "WIN" if signed>0 else "LOSS"
            rows.append({"period":period,"side":e["direction"],"outcome":outcome,
                "penetration_atr":penetration/atr[i],
                "reclaim_atr":reclaimed/atr[i],
                "wick_ratio":wick/span,
                "close_location_aligned":close_loc,
                "penetration_share_range":penetration/span,
                "adx":ind[i]["adx"]})
    if not rows: raise SystemExit("No eligible aligned sweeps.")
    features=("penetration_atr","reclaim_atr","wick_ratio","close_location_aligned","penetration_share_range","adx")
    train=[r for r in rows if r["period"]=="TRAIN"]
    cuts={k:[quantile([r[k] for r in train],q) for q in (.2,.4,.6,.8)] for k in features}
    lines=["# HYDRA — causal sweep morphology audit","",
      f"Source: Dukascopy EURUSD M1 BID; raw M1={len(m1):,}; complete M5={sum(map(len,segments)):,}; segments={len(segments)}.",
      f"Coverage: {m1[0].timestamp.isoformat()} — {m1[-1].timestamp.isoformat()}.",
      f"Aligned-sweep trigger events with {WARMUP}-bar warmup and complete 20m path: {len(rows):,}.",
      f"Chronological split: TRAIN < {d1}; VALIDATION {d1} through {d2}; TEST >= {d2}.",
      "Frozen trigger unchanged: BB(20,2) re-entry + Williams %R(14) cross + ADX>=15; entry next M5 open, exit fourth M5 close; payout +0.92/-1/0.",
      "Sweep features are measured at signal-candle close only. Quintile cutoffs are computed on TRAIN and held fixed.",
      "External Dukascopy BID proxy, not Pocket Option quotes. Descriptive morphology audit only; no filter selected or deployed.",
      "","## Aligned-sweep baseline","","| Split | Side | n | W/L/D | Decisive WR | Net |","|---|---|---:|---|---:|---:|"]
    for p in ("TRAIN","VALIDATION","TEST"):
      for side in ("ALL","CALL","PUT"):
        sub=[r for r in rows if r["period"]==p and (side=="ALL" or r["side"]==side)]
        n,w,l,d,wr,net=stats(sub)
        lines.append(f"| {p} | {side} | {n} | {w}/{l}/{d} | {wr:.2f}% | {net:+.2f}u |")
    for feat in features:
      lines += ["",f"## TRAIN-defined quintiles: {feat}","","| Split | Side | Bin | n | W/L/D | Decisive WR | Net |",
                "|---|---|---|---:|---|---:|---:|"]
      for p in ("TRAIN","VALIDATION","TEST"):
        for side in ("CALL","PUT"):
          for qi in range(5):
            lo=None if qi==0 else cuts[feat][qi-1]
            hi=None if qi==4 else cuts[feat][qi]
            sub=[r for r in rows if r["period"]==p and r["side"]==side and
                 (lo is None or r[feat]>lo) and (hi is None or r[feat]<=hi)]
            if len(sub)<10: continue
            n,w,l,d,wr,net=stats(sub)
            lines.append(f"| {p} | {side} | Q{qi+1} | {n} | {w}/{l}/{d} | {wr:.2f}% | {net:+.2f}u |")
    lines += ["","## Interpretation guardrails","",
      "- Quintiles are descriptive; no bin is a recommended filter, even if its win rate exceeds 52.08%.",
      "- Look for monotonicity and same-direction behavior across TRAIN, VALIDATION and TEST, not isolated high rates.",
      "- Overlapping 20m outcomes, serial dependence, multiple features and repeated historical inspection limit inference.",
      "- A future candidate must be predeclared and tested prospectively on fresh Pocket Option DEMO candles before integration."]
    args.out.parent.mkdir(parents=True,exist_ok=True)
    report="\n".join(lines)+"\n"; args.out.write_text(report,encoding="utf-8"); print(report)

if __name__=="__main__": main()
