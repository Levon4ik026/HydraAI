#!/usr/bin/env python3
"""Exploratory cohort-drift diagnostics for frozen HYD-CAND-013.

No filters, candidate parameters, profile center, or radius are optimized.
Compares causal context and signal morphology across TRAIN/VALIDATION/seed
cohorts, and uses TRAIN-analog quintile edges only for descriptive transfer
tables in VALIDATION. This is not an independent confirmation.
"""
from __future__ import annotations
import argparse, math
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from statistics import median, mean, pstdev

from expanded_strategy_screen import read_m1, outcome, stats
from long_history_validation import make_m5
from eleventh_wave_impulse_screen import build_events

NAME="BULL_IMPULSE_CONT_R2.0_C0.75"
H=4
PAYOUT=.92
D1=date(2025,9,17)
D2=date(2026,4,14)
SEEDS={"2026-05","2026-10"}
FEATURES=("efficiency_12","return_12_atr","volatility_12_vs_prior60",
          "range_position_24","ema20_gap_atr","ema20_slope6_atr",
          "impulse_range_x_tr20","body_range","close_position")
def qtile(xs,q):
    a=sorted(float(x) for x in xs if math.isfinite(float(x)))
    if not a:return float("nan")
    p=(len(a)-1)*q; lo=int(p); hi=min(lo+1,len(a)-1)
    return a[lo]+(a[hi]-a[lo])*(p-lo)
def ema(values,n=20):
    alpha=2/(n+1); out=[]; v=None
    for x in values:
        v=float(x) if v is None else alpha*float(x)+(1-alpha)*v
        out.append(v)
    return out
def features(bars,i,tr,em):
    if i<72:return None
    atr=sum(tr[i-20:i])/20
    span=max(b.high for b in bars[i-24:i])-min(b.low for b in bars[i-24:i])
    prior=sum(tr[i-72:i-12])/60
    recent=sum(tr[i-12:i])/12
    if atr<=0 or span<=0 or prior<=0:return None
    net=bars[i-1].close-bars[i-13].close
    path=sum(abs(bars[j].close-bars[j-1].close) for j in range(i-12,i))
    b=bars[i]; rng=b.high-b.low
    if rng<=0:return None
    prevtr=sum(tr[i-20:i])/20
    return {
      "efficiency_12":abs(net)/path if path else 0.0,
      "return_12_atr":net/atr,
      "volatility_12_vs_prior60":recent/prior,
      "range_position_24":(bars[i-1].close-min(x.low for x in bars[i-24:i]))/span,
      "ema20_gap_atr":(bars[i-1].close-em[i-1])/atr,
      "ema20_slope6_atr":(em[i-1]-em[i-7])/atr,
      "impulse_range_x_tr20":rng/prevtr,
      "body_range":abs(b.close-b.open)/rng,
      "close_position":(b.close-b.low)/rng,
    }
def summary(rs):
    s=stats([r["result"] for r in rs])
    return f'N={s[0]} W/L/D={s[1]}/{s[2]}/{s[3]} WR={s[4]:.2f}% Net={s[6]:+.2f}u'
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    m1=read_m1(a.data); segments=make_m5(m1); raw=[]
    for sid,bars in enumerate(segments):
        ev=build_events(bars); em=ema([b.close for b in bars]); tr=[]
        for i,b in enumerate(bars):
            if i==0:tr.append(b.high-b.low)
            else:
                p=bars[i-1].close
                tr.append(max(b.high-b.low,abs(b.high-p),abs(b.low-p)))
        candidates=[]
        for i,_ in ev.get(NAME,[]):
            if i+H>=len(bars):continue
            ts=bars[i].timestamp; day=ts.date()
            split="TRAIN" if day<D1 else "VALIDATION" if day<D2 else "TEST"
            settle=(bars[i+H].timestamp+timedelta(minutes=5)).date()
            if (split=="TRAIN" and settle>=D1) or (split=="VALIDATION" and settle>=D2):continue
            f=features(bars,i,tr,em)
            if f is None:continue
            candidates.append({"i":i,"ts":ts,"day":day,"month":ts.strftime("%Y-%m"),
              "split":split,"segment":sid,"result":outcome(bars,i,"PUT",H),"f":f})
        for sp in ("TRAIN","VALIDATION","TEST"):
            nxt=-1
            for r in sorted((x for x in candidates if x["split"]==sp),key=lambda x:x["i"]):
                if r["i"]<nxt:continue
                nxt=r["i"]+H;raw.append(r)
    seeds=[r for r in raw if r["split"]=="TEST" and r["month"] in SEEDS]
    train=[r for r in raw if r["split"]=="TRAIN"]
    val=[r for r in raw if r["split"]=="VALIDATION"]
    if len(seeds)<30 or len(train)<100 or len(val)<50:raise SystemExit("Insufficient cohort size")
    base=("efficiency_12","return_12_atr","volatility_12_vs_prior60",
          "range_position_24","ema20_gap_atr","ema20_slope6_atr")
    scales={}
    for f in base:
        scales[f]=max(qtile([r["f"][f] for r in train],.75)-qtile([r["f"][f] for r in train],.25),1e-6)
    center={f:median([r["f"][f] for r in seeds]) for f in base}
    def dist(r):return math.sqrt(sum(((r["f"][f]-center[f])/scales[f])**2 for f in base)/len(base))
    radius=qtile([dist(r) for r in seeds],.90)
    hist=[r for r in raw if r["split"] in ("TRAIN","VALIDATION")]
    for r in hist:r["analog"]=dist(r)<=radius
    ta=[r for r in hist if r["split"]=="TRAIN" and r["analog"]]
    va=[r for r in hist if r["split"]=="VALIDATION" and r["analog"]]
    ss=seeds
    cohorts=[("TRAIN analog",ta),("VALIDATION analog",va),("May+October seed",ss)]
    lines=["# HYD-CAND-013 — cohort drift diagnostics","",
      f"Data: Dukascopy EUR/USD M1 BID; M1={len(m1):,}; M5={sum(map(len,segments)):,}; segments={len(segments)}.",
      f"Frozen candidate: {NAME}; inverse PUT; next M5 open; H=4 M5 bars (20m); payout scenario 92%.",
      f"Frozen splits: TRAIN < {D1}; VALIDATION {D1}–{D2-timedelta(days=1)}; TEST >= {D2}.",
      f"Frozen seed/profile: TEST May+October 2026; seed N={len(seeds)}; radius={radius:.6f}; no refit.",
      "All six profile features end before the signal candle. Signal morphology describes the completed signal candle, already fixed by the frozen candidate rule.",
      "This is exploratory diagnosis after inspecting TRAIN/VALIDATION and TEST seed cohorts; it is not an independent test. No thresholds or filters are selected from these tables.","",
      "## Cohort outcome overview",""]
    for name,rs in cohorts:lines.append(f"- {name}: {summary(rs)}")
    lines += ["","## Feature distribution drift","",
      "| Feature | TRAIN median [IQR] | VALIDATION median [IQR] | Seed median [IQR] | SMD TRAIN→VAL |",
      "|---|---:|---:|---:|---:|"]
    for f in FEATURES:
        vals=[[r["f"][f] for r in rs] for _,rs in cohorts]
        def cell(x):return f"{median(x):.4f} [{qtile(x,.25):.4f},{qtile(x,.75):.4f}]"
        sd1=pstdev(vals[0]);sd2=pstdev(vals[1]);den=math.sqrt((sd1*sd1+sd2*sd2)/2)
        smd=(mean(vals[1])-mean(vals[0]))/den if den else 0
        lines.append(f"| {f} | {cell(vals[0])} | {cell(vals[1])} | {cell(vals[2])} | {smd:+.3f} |")
    lines += ["","## Monthly outcome concentration","",
      "| Month | Cohort | N | W/L/D | WR | Net u |",
      "|---|---|---:|---|---:|---:|"]
    groups=defaultdict(list)
    for r in ta+va:groups[(r["month"],r["split"])].append(r)
    for (mo,sp),rs in sorted(groups.items()):
        s=stats([r["result"] for r in rs])
        lines.append(f"| {mo} | {sp} | {s[0]} | {s[1]}/{s[2]}/{s[3]} | {s[4]:.2f}% | {s[6]:+.2f} |")
    lines += ["","## TRAIN-defined quintile transfer (descriptive only)","",
      "Quintile cut points are calculated once from TRAIN analog feature values. VALIDATION is scored against those unchanged cut points. No best bin is selected; all five bins are shown.",
      "| Feature | Bin | TRAIN N / WR | VALIDATION N / WR |",
      "|---|---:|---:|---:|"]
    for f in FEATURES:
        edges=[qtile([r["f"][f] for r in ta],q) for q in (.2,.4,.6,.8)]
        def bucket(v):
            for j,e in enumerate(edges):
                if v<=e:return j
            return 4
        for b in range(5):
            cells=[]
            for rs in (ta,va):
                sub=[r for r in rs if bucket(r["f"][f])==b]
                if sub:
                    s=stats([r["result"] for r in sub]);cells.append(f'{s[0]} / {s[4]:.1f}%')
                else:cells.append("0 / n/a")
            lines.append(f"| {f} | Q{b+1} | {cells[0]} | {cells[1]} |")
    lines += ["","## UTC time-of-day composition (descriptive, not a filter)","",
      "| Cohort | 00–05 | 06–11 | 12–17 | 18–23 |",
      "|---|---:|---:|---:|---:|"]
    for name,rs in cohorts:
        counts=[sum(1 for r in rs if (r["ts"].hour//6)==k) for k in range(4)]
        lines.append(f"| {name} | "+" | ".join(map(str,counts))+" |")
    lines += ["","## Guardrails and next decision","",
      "- Feature distribution differences describe cohort drift; they do not establish that any feature causes the performance gap.",
      "- Quintile tables are exploratory, involve multiple comparisons, and must not be converted into entry filters on these same cohorts.",
      "- If one or more pre-entry features appear to explain the split gap, formulate a single causal hypothesis and freeze it before a genuinely untouched forward period.",
      "- Keep HYD-CAND-013 as a candidate. Do not alter its signal, profile radius, expiry, or entry rules based on this report.",
      "- Independent confirmation requires future untouched data and preferably Pocket Option demo quote capture; Dukascopy BID remains only a proxy.",""]
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text("\n".join(lines),encoding="utf-8")
    print(f"HYD-CAND-013 cohort drift audit complete: train_analog={len(ta)} validation_analog={len(va)} seed={len(ss)}")
if __name__=="__main__":main()
