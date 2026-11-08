#!/usr/bin/env python3
"""Predeclared, research-only interaction screen for Hydra's frozen M5 setup.

Rules are fixed before execution. Train-only medians define numeric cutoffs;
TRAIN/VALIDATION/TEST are chronological and expiry-boundary purged. TEST is
reported descriptively and is not used to choose or tune any rule.
"""
from __future__ import annotations
import argparse, math, statistics
from collections import defaultdict
from pathlib import Path
from long_history_validation import read_duka, make_events, PAYOUT, m5_close_time, chronological_period
from reproduce_m5_bb_williams_adx import make_m5, indicators

HORIZON = 4
MIN_WARMUP = 50

def ema(values, period):
    out=[None]*len(values)
    if len(values)<period: return out
    state=sum(values[:period])/period; out[period-1]=state
    alpha=2/(period+1)
    for i in range(period,len(values)):
        state=values[i]*alpha+state*(1-alpha); out[i]=state
    return out

def metric(rows):
    w=sum(r["outcome"]=="WIN" for r in rows)
    l=sum(r["outcome"]=="LOSS" for r in rows)
    d=len(rows)-w-l
    dec=w+l
    return {"n":len(rows),"w":w,"l":l,"d":d,
            "wr":100*w/dec if dec else float("nan"),
            "net":w*PAYOUT-l}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--out",type=Path,default=Path("research/PREDECLARED_INTERACTION_SCREEN.md"))
    a=ap.parse_args()
    m1=read_duka(a.data); segments=make_m5(m1)
    events=make_events(segments,15)
    days=sorted({e["signal_time"].date() for e in events})
    if len(days)<30: raise SystemExit("Insufficient signal days.")
    d1,d2=days[int(len(days)*.60)],days[int(len(days)*.80)]
    byseg=defaultdict(list)
    for e in events: byseg[e["segment"]].append(e)
    rows=[]
    for sid,bars in enumerate(segments):
        if not byseg[sid]: continue
        ind=indicators(bars); closes=[b.close for b in bars]
        e20,e50=ema(closes,20),ema(closes,50)
        tr=[None]*len(bars)
        for i in range(1,len(bars)):
            b,p=bars[i],bars[i-1]
            tr[i]=max(b.high-b.low,abs(b.high-p.close),abs(b.low-p.close))
        atr=[None]*len(bars)
        for i in range(14,len(bars)):
            vals=tr[i-13:i+1]
            if all(v is not None for v in vals): atr[i]=sum(vals)/14
        atr_pct=[atr[i]/bars[i].close if atr[i] and bars[i].close else None for i in range(len(bars))]
        for e in byseg[sid]:
            i=e["bar_index"]
            if i<MIN_WARMUP or i+HORIZON>=len(bars): continue
            cur=bars[i]; x=ind[i]; av=atr[i]
            if not av or not e20[i] or not e50[i] or x["adx"] is None: continue
            settle=m5_close_time(bars[i+HORIZON].timestamp)
            period=chronological_period(cur.timestamp,settle,d1,d2)
            if period is None: continue
            p12=bars[i-12:i]
            hi=max(b.high for b in p12); lo=min(b.low for b in p12)
            sweep_hi=cur.high>hi and cur.close<hi
            sweep_lo=cur.low<lo and cur.close>lo
            aligned=sweep_lo if e["direction"]=="CALL" else sweep_hi
            prior_ranges=[b.high-b.low for b in bars[i-12:i]]
            recent_ranges=[b.high-b.low for b in bars[i-2:i+1]]
            compression=(sum(recent_ranges)/3)/(sum(prior_ranges)/12) if sum(prior_ranges)>0 else None
            body=((cur.close-cur.open)/av)*(1 if e["direction"]=="CALL" else -1)
            delta=bars[i+HORIZON].close-bars[i+1].open
            signed=delta*(1 if e["direction"]=="CALL" else -1)
            outcome="DRAW" if abs(signed)<1e-12 else "WIN" if signed>0 else "LOSS"
            volhist=[v for v in atr_pct[max(14,i-120):i] if v is not None]
            volrank=sum(v<=atr_pct[i] for v in volhist)/len(volhist) if atr_pct[i] is not None and len(volhist)>=60 else None
            rows.append({"time":cur.timestamp,"period":period,"side":e["direction"],"outcome":outcome,
                "trend":"UP" if e20[i]>e50[i] else "DOWN" if e20[i]<e50[i] else "FLAT",
                "adx":x["adx"],"aligned_sweep":aligned,"compression":compression,
                "aligned_body":body,"volrank":volrank})
    if not rows: raise SystemExit("No eligible rows.")
    train=[r for r in rows if r["period"]=="TRAIN"]
    if len(train)<100: raise SystemExit("Too few TRAIN rows.")
    comp_cut=statistics.median(r["compression"] for r in train if r["compression"] is not None)
    body_cut=statistics.median(r["aligned_body"] for r in train)
    # All rule definitions are predeclared. Numeric thresholds are derived from TRAIN only.
    rules={
      "PUT sweep + UP trend + ADX 20-25":lambda r:r["side"]=="PUT" and r["aligned_sweep"] and r["trend"]=="UP" and 20<=r["adx"]<25,
      "PUT sweep + UP trend + ADX >=20":lambda r:r["side"]=="PUT" and r["aligned_sweep"] and r["trend"]=="UP" and r["adx"]>=20,
      "CALL sweep + UP trend + ADX 20-25":lambda r:r["side"]=="CALL" and r["aligned_sweep"] and r["trend"]=="UP" and 20<=r["adx"]<25,
      "CALL sweep + DOWN trend + ADX 20-25":lambda r:r["side"]=="CALL" and r["aligned_sweep"] and r["trend"]=="DOWN" and 20<=r["adx"]<25,
      "Either sweep + ADX >=20 + compressed path":lambda r:r["aligned_sweep"] and r["adx"]>=20 and r["compression"] is not None and r["compression"]<=comp_cut,
      "Either sweep + ADX >=20 + weak aligned body":lambda r:r["aligned_sweep"] and r["adx"]>=20 and r["aligned_body"]<=body_cut,
    }
    lines=["# HYDRA — predeclared interaction screen","",
      f"Source: Dukascopy EURUSD M1 BID; raw M1={len(m1):,}; complete continuous M5 bars={sum(map(len,segments)):,}; segments={len(segments)}.",
      f"Coverage: {m1[0].timestamp.isoformat()} — {m1[-1].timestamp.isoformat()}.",
      f"Eligible events after {MIN_WARMUP}-bar warmup and complete 20m path: {len(rows):,}. Split: TRAIN < {d1}; VALIDATION {d1} through {d2}; TEST >= {d2}.",
      "Frozen trigger unchanged: BB(20,2) re-entry + Williams %R(14) cross + ADX>=15; next M5 open to fourth M5 close; payout +0.92/-1/0.",
      "Predeclared rule list; no threshold optimization. Compression/body cutoffs are TRAIN medians only. Boundary-crossing outcomes are purged.",
      "External Dukascopy BID proxy, not Pocket Option quotes. Exploratory screen only; no filter is deployed. TEST is previously exposed to research and is descriptive, not independent confirmation.",
      f"TRAIN-derived medians: compression_3v12={comp_cut:.6f}; direction-aligned body/ATR={body_cut:.6f}.",
      "", "## Baseline","", "| Split | Direction | n | W/L/D | Decisive WR | Net |","|---|---|---:|---|---:|---:|"]
    for p in ("TRAIN","VALIDATION","TEST"):
      for side in ("ALL","CALL","PUT"):
        sub=[r for r in rows if r["period"]==p and (side=="ALL" or r["side"]==side)]
        m=metric(sub); lines.append(f"| {p} | {side} | {m['n']} | {m['w']}/{m['l']}/{m['d']} | {m['wr']:.2f}% | {m['net']:+.2f}u |")
    lines += ["","## Fixed interaction rules","",
      "| Rule | Split | n | W/L/D | Decisive WR | Net | vs same-side baseline (pp) |",
      "|---|---|---:|---|---:|---:|---:|"]
    for name,fn in rules.items():
      for p in ("TRAIN","VALIDATION","TEST"):
        sub=[r for r in rows if r["period"]==p and fn(r)]
        m=metric(sub)
        sides={r["side"] for r in sub}
        if len(sides)==1:
          side=next(iter(sides)); base=metric([r for r in rows if r["period"]==p and r["side"]==side])
        else:
          base=metric([r for r in rows if r["period"]==p])
        lift=m["wr"]-base["wr"]
        lines.append(f"| {name} | {p} | {m['n']} | {m['w']}/{m['l']}/{m['d']} | {m['wr']:.2f}% | {m['net']:+.2f}u | {lift:+.2f} |")
    lines += ["","## Decision protocol","",
      "- Candidate can advance only if VALIDATION has at least 40 decisive outcomes, positive net, and positive lift versus its same-direction baseline.",
      "- TRAIN is descriptive and used only to establish the fixed numeric cutoffs; it cannot rescue a failed VALIDATION result.",
      "- TEST is not used to select rules. Report it only after the validation gate is frozen.",
      "- Small samples, serial dependence, overlapping outcomes, multiple candidate rules, and prior TEST exposure create selection risk.",
      "- Even a passing historical screen requires prospective confirmation on fresh Pocket Option DEMO candles before integration.",""]
    a.out.parent.mkdir(parents=True,exist_ok=True)
    report="\n".join(lines); a.out.write_text(report+"\n",encoding="utf-8"); print(report)

if __name__=="__main__": main()
