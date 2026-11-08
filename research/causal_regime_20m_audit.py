#!/usr/bin/env python3
"""Causal regime and pre-entry feature audit for the frozen 20-minute setup.

All predictors are known at the signal candle close. Outcome is measured from
next M5 open to close of the fourth M5 candle. No parameters are optimized.
"""
from __future__ import annotations
import argparse, math, statistics
from collections import defaultdict
from pathlib import Path
from long_history_validation import read_duka, make_events, stats, PAYOUT
from reproduce_m5_bb_williams_adx import make_m5, indicators

def ema(values, period):
    out=[None]*len(values)
    if len(values)<period: return out
    state=sum(values[:period])/period
    out[period-1]=state
    alpha=2/(period+1)
    for i in range(period,len(values)):
        state=values[i]*alpha+state*(1-alpha); out[i]=state
    return out

def percentile_rank(history, value):
    if not history: return None
    return sum(x<=value for x in history)/len(history)

def quartile_edges(values):
    vals=sorted(x for x in values if x is not None)
    if len(vals)<20: return None
    return [vals[int((len(vals)-1)*q)] for q in (.25,.5,.75)]

def bucket(value, edges):
    if value is None or edges is None: return "NA"
    return "Q1" if value<=edges[0] else "Q2" if value<=edges[1] else "Q3" if value<=edges[2] else "Q4"

def outcome(bars,i,side):
    delta=bars[i+4].close-bars[i+1].open
    if abs(delta)<1e-12: return "DRAW"
    return "WIN" if (delta>0 if side=="CALL" else delta<0) else "LOSS"

def summarize(rows):
    w=sum(x["outcome"]=="WIN" for x in rows); l=sum(x["outcome"]=="LOSS" for x in rows); d=len(rows)-w-l
    dec=w+l; wr=100*w/dec if dec else float("nan")
    return w,l,d,wr,w*PAYOUT-l

def fmt(rows):
    w,l,d,wr,net=summarize(rows)
    return f"{len(rows)} | {w}/{l}/{d} | {wr:.1f}% | {net:+.2f}u"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--out",type=Path,default=Path("research/CAUSAL_REGIME_20M_AUDIT.md"))
    a=ap.parse_args()
    m1=read_duka(a.data); segments=make_m5(m1)
    events=make_events(segments,15)
    days=sorted({e["signal_time"].date() for e in events})
    d1=days[int(len(days)*.60)]; d2=days[int(len(days)*.80)]
    records=[]
    for e in events:
        bars=segments[e["segment"]]; i=e["bar_index"]
        if i+4>=len(bars): continue
        ind=indicators(bars); x=ind[i]
        if i<120 or x["adx"] is None: continue
        closes=[b.close for b in bars]
        e20=ema(closes,20); e50=ema(closes,50)
        # Causal true-range ATR(14), simple rolling mean; no future observations.
        trs=[]
        for j in range(1,len(bars)):
            b,prev=bars[j],bars[j-1]
            trs.append(max(b.high-b.low,abs(b.high-prev.close),abs(b.low-prev.close)))
        atr=[None]*len(bars)
        for j in range(14,len(bars)):
            atr[j]=sum(trs[j-14:j])/14
        av=atr[i]
        if not av or not e20[i] or not e50[i]: continue
        prior_atr=[atr[k]/bars[k].close for k in range(max(14,i-120),i) if atr[k] and bars[k].close]
        volrank=percentile_rank(prior_atr,av/bars[i].close)
        prev12=bars[i-12:i]; prev24=bars[i-24:i]
        cur=bars[i]; span=max(cur.high-cur.low,1e-12)
        upper_wick=cur.high-max(cur.open,cur.close); lower_wick=min(cur.open,cur.close)-cur.low
        bb=x["upper"]-x["lower"]
        side=e["direction"]
        signal_day=cur.timestamp.date()
        period="TRAIN" if signal_day<d1 else "VALIDATION" if signal_day<d2 else "TEST"
        # Signal candle data and trailing structure only.
        features={
          "trend":"UP" if e20[i]>e50[i] else "DOWN" if e20[i]<e50[i] else "FLAT",
          "adx_band":"15-20" if x["adx"]<20 else "20-25" if x["adx"]<25 else "25+",
          "volatility":"LOW" if volrank is not None and volrank<=.333 else "MID" if volrank is not None and volrank<=.667 else "HIGH",
          "hour":"ASIA" if cur.timestamp.hour<7 else "LONDON" if cur.timestamp.hour<13 else "NY" if cur.timestamp.hour<21 else "LATE",
          "weekday":cur.timestamp.strftime("%a"),
          "body_atr":abs(cur.close-cur.open)/av,
          "range_atr":span/av,
          "upper_wick_ratio":upper_wick/span,
          "lower_wick_ratio":lower_wick/span,
          "bb_width_atr":bb/av if bb else None,
          "ema_spread_atr":(e20[i]-e50[i])/av,
          "di_spread":(x["plus_di"] or 0)-(x["minus_di"] or 0),
          "prior12_high_dist_atr":(max(b.high for b in prev12)-cur.close)/av,
          "prior12_low_dist_atr":(cur.close-min(b.low for b in prev12))/av,
          "prior24_high_dist_atr":(max(b.high for b in prev24)-cur.close)/av,
          "prior24_low_dist_atr":(cur.close-min(b.low for b in prev24))/av,
          "momentum3_atr":(cur.close-bars[i-3].close)/av,
          "momentum6_atr":(cur.close-bars[i-6].close)/av,
          "willr":x["willr"],
          "adx":x["adx"],
        }
        records.append({"time":cur.timestamp,"direction":side,"period":period,
                        "outcome":outcome(bars,i,side),"features":features})
    # Quantile thresholds learned on TRAIN only and then held fixed.
    numeric=[k for k in records[0]["features"] if isinstance(records[0]["features"][k],(int,float))]
    edges={}
    for key in numeric:
        edges[key]=quartile_edges([r["features"][key] for r in records if r["period"]=="TRAIN"])
    lines=[
      "# HYDRA — causal 20-minute regime audit","",
      f"Signals with 120-bar warmup and complete 20m path: {len(records):,}.",
      f"Split: TRAIN < {d1}; VALIDATION {d1} to {d2}; TEST >= {d2}.",
      "Frozen trigger: BB(20,2) re-entry + Williams %R(14) cross + ADX(14)>=15. Entry next M5 open; exit fourth M5 close; payout 92%.",
      "All candidate predictors are signal-close or trailing-history values. Numeric quartile cutoffs are learned on TRAIN only and reused unchanged.",
      "External Dukascopy BID prices; no Pocket Option spread/quote model. Exploratory regime audit, not proof of profitability.","",
      "## Overall 20m results","",
      "| Period | Direction | n | W/L/D | Decisive WR | Net |",
      "|---|---|---:|---:|---:|---:|"]
    for p in ("TRAIN","VALIDATION","TEST"):
      for side in ("CALL","PUT"):
        sub=[r for r in records if r["period"]==p and r["direction"]==side]
        lines.append(f"| {p} | {side} | {fmt(sub)} |")
    # categorical splits
    for key in ("trend","adx_band","volatility","hour","weekday"):
      lines += ["",f"## Regime split: {key}","",
                "| Period | Direction | State | n | W/L/D | Decisive WR | Net |",
                "|---|---|---|---:|---:|---:|---:|"]
      states=sorted({r["features"][key] for r in records})
      for p in ("TRAIN","VALIDATION","TEST"):
       for side in ("CALL","PUT"):
        for state in states:
         sub=[r for r in records if r["period"]==p and r["direction"]==side and r["features"][key]==state]
         if sub: lines.append(f"| {p} | {side} | {state} | {fmt(sub)} |")
    # Numeric quartile splits, show only period/direction and bins with >=20 samples.
    for key in numeric:
      lines += ["",f"## Train-defined quartiles: {key}","",
                "| Period | Direction | Bin | n | W/L/D | Decisive WR | Net |",
                "|---|---|---|---:|---:|---:|---:|"]
      for p in ("TRAIN","VALIDATION","TEST"):
       for side in ("CALL","PUT"):
        for q in ("Q1","Q2","Q3","Q4"):
         sub=[r for r in records if r["period"]==p and r["direction"]==side and bucket(r["features"][key],edges[key])==q]
         if len(sub)>=20: lines.append(f"| {p} | {side} | {q} | {fmt(sub)} |")
    # Month diagnostics: use all periods; useful to locate instability, not a filter.
    lines += ["","## Month-by-month 20m results","",
              "| Month UTC | Direction | n | W/L/D | Decisive WR | Net |",
              "|---|---|---:|---:|---:|---:|"]
    for month in sorted({r["time"].strftime("%Y-%m") for r in records}):
      for side in ("CALL","PUT"):
       sub=[r for r in records if r["time"].strftime("%Y-%m")==month and r["direction"]==side]
       if sub: lines.append(f"| {month} | {side} | {fmt(sub)} |")
    lines += ["","## Guardrails","",
      "- A subgroup is not a deployable filter merely because its historical WR exceeds 52.08%.",
      "- Compare the same subgroup across TRAIN, VALIDATION and TEST; instability is evidence against it.",
      "- Small cells, serial dependence and repeated exploratory comparisons make nominal subgroup rates optimistic.",
      "- No strategy parameter or application behavior is changed by this audit.",""]
    a.out.parent.mkdir(parents=True,exist_ok=True); report="\n".join(lines); a.out.write_text(report+"\n",encoding="utf-8"); print(report)

if __name__=="__main__": main()
