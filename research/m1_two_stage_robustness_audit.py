#!/usr/bin/env python3
"""Predeclared robustness audit for the two-stage M1 event/direction model.

All model fits use TRAIN only. Event and confidence thresholds are calibrated
on VALIDATION only. TEST is evaluated once; threshold variants are diagnostics,
not candidates for selecting a winner. Includes calendar stability, non-overlap,
payout sensitivity and UTC-day block bootstrap.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
try:
    from m1_move_occurrence_direction_audit import read_bars, split_segments, build_samples, PAYOUT
except ImportError:
    from research.m1_move_occurrence_direction_audit import read_bars, split_segments, build_samples, PAYOUT

HORIZON = 10
SEED = 20261108

def stats(rows, indices, probs, payout=PAYOUT):
    w=l=d=0
    for idx,p in zip(indices,probs):
        y=rows[idx]["outcomes"][HORIZON]
        if y==0: d+=1
        elif (y>0)==(p>=0.5): w+=1
        else: l+=1
    decisive=w+l
    return len(indices),w,l,d,(100*w/decisive if decisive else float("nan")),w*payout-l

def wilson(w,n,z=1.959963984540054):
    if n==0: return float("nan"),float("nan")
    p=w/n; den=1+z*z/n
    mid=(p+z*z/(2*n))/den
    half=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return 100*(mid-half),100*(mid+half)

def bootstrap_daily(rows, indices, probs, payout, reps=5000):
    byday=defaultdict(list)
    for idx,p in zip(indices,probs):
        r=rows[idx]; y=r["outcomes"][HORIZON]
        if y==0: continue
        win=int((y>0)==(p>=0.5))
        byday[r["time"].date().isoformat()].append(payout if win else -1.0)
    days=sorted(byday)
    if len(days)<5: return (float("nan"),float("nan"),len(days))
    rng=np.random.default_rng(SEED)
    daily=np.asarray([np.sum(byday[d]) for d in days],float)
    draws=rng.integers(0,len(days),size=(reps,len(days)))
    means=daily[draws].sum(axis=1)/len(days)
    lo,hi=np.quantile(means,[.025,.975])
    return float(lo),float(hi),len(days)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--out",type=Path,default=Path("research/M1_TWO_STAGE_ROBUSTNESS_AUDIT.md"))
    a=ap.parse_args()
    bars=read_bars(a.data); segments=split_segments(bars)
    X,event_y,records=build_samples(segments,5.0)
    order=np.argsort(np.asarray([r["time"].timestamp() for r in records]))
    X,event_y=X[order],event_y[order]; records=[records[k] for k in order]
    n=len(records); i1,i2=int(n*.60),int(n*.80)
    t1,t2=records[i1]["time"],records[i2]["time"]
    train=np.asarray([i for i,r in enumerate(records[:i1]) if r["time"]+timedelta(minutes=15)<t1],int)
    val=np.asarray([i for i,r in enumerate(records[i1:i2],start=i1) if r["time"]+timedelta(minutes=15)<t2],int)
    test=np.arange(i2,n,dtype=int)
    gate_model=make_pipeline(SimpleImputer(strategy="median"),StandardScaler(),
        LogisticRegression(C=.1,max_iter=1200,solver="lbfgs",random_state=23))
    gate_model.fit(X[train],event_y[train])
    pv=gate_model.predict_proba(X[val])[:,1]; pt=gate_model.predict_proba(X[test])[:,1]
    gate_cut=float(np.quantile(pv,.90))
    vg=val[pv>=gate_cut]; tg=test[pt>=gate_cut]
    train_dir=np.asarray([i for i in train if event_y[i]==1 and records[i]["outcomes"][HORIZON]!=0],int)
    ydir=np.asarray([int(records[i]["outcomes"][HORIZON]>0) for i in train_dir])
    dir_model=make_pipeline(SimpleImputer(strategy="median"),StandardScaler(),
        LogisticRegression(C=.1,max_iter=1200,solver="lbfgs",class_weight="balanced",random_state=29))
    dir_model.fit(X[train_dir],ydir)
    pvg=dir_model.predict_proba(X[vg])[:,1]
    cv=np.maximum(pvg,1-pvg)
    ptg=dir_model.predict_proba(X[tg])[:,1]
    ct=np.maximum(ptg,1-ptg)
    lines=["# HYDRA — two-stage model robustness audit","",
      f"Rows={len(bars):,}; continuous segments={len(segments):,}; samples={n:,}.",
      f"Chronological 60/20/20; 15m purge; TRAIN={len(train):,}, VALIDATION={len(val):,}, TEST={len(test):,}.",
      "Models fitted on TRAIN only. Event gate 90th percentile and confidence thresholds calibrated on VALIDATION only.",
      "Outcome: next-M1-open to 10-minute close, Dukascopy BID proxy; draws excluded from decisive WR; no platform spread/latency.",
      f"Frozen event cutoff={gate_cut:.6f}; TEST gate={len(tg):,}/{len(test):,} ({100*len(tg)/len(test):.2f}%).",
      f"Conditional direction training rows={len(train_dir):,}; TEST gated rows={len(tg):,}.","",
      "## Confidence-threshold sensitivity (all cutoffs from VALIDATION)",
      "| Validation confidence quantile | Cutoff | TEST trades | W/L/D | WR | Wilson 95% CI | Net @85% | @90% | @92% |",
      "|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    main_indices=[]; main_probs=[]
    for q in (.50,.75,.90):
        cut=float(np.quantile(cv,q)); mask=ct>=cut
        inds=tg[mask]; probs=ptg[mask]
        s=stats(records,inds.tolist(),probs.tolist())
        lo,hi=wilson(s[1],s[1]+s[2])
        nets=[s[1]*p-s[2] for p in (.85,.90,.92)]
        lines.append(f"| {q:.0%} | {cut:.6f} | {s[0]} | {s[1]}/{s[2]}/{s[3]} | {s[4]:.2f}% | {lo:.2f}–{hi:.2f}% | {nets[0]:+.2f}u | {nets[1]:+.2f}u | {nets[2]:+.2f}u |")
        if q==.75: main_indices=inds.tolist(); main_probs=probs.tolist()
    s=stats(records,main_indices,main_probs)
    lines += ["","## Calendar stability — frozen 75th-percentile confidence rule",
      "| UTC month | Trades | W/L/D | WR | Net @92% |","|---|---:|---:|---:|---:|"]
    months=defaultdict(list)
    for idx,p in zip(main_indices,main_probs): months[records[idx]["time"].strftime("%Y-%m")].append((idx,p))
    for month,items in sorted(months.items()):
        ms=stats(records,[x[0] for x in items],[x[1] for x in items])
        lines.append(f"| {month} | {ms[0]} | {ms[1]}/{ms[2]}/{ms[3]} | {ms[4]:.2f}% | {ms[5]:+.2f}u |")
    # Greedy chronological one-position schedule: no new entry while prior 10m position is open.
    selected=[]; last=None
    for idx,p in zip(main_indices,main_probs):
        ts=records[idx]["time"]
        if last is None or ts>=last+timedelta(minutes=10):
            selected.append((idx,p)); last=ts
    ns=stats(records,[x[0] for x in selected],[x[1] for x in selected])
    lines += ["","## One-position schedule (10-minute lockout)",
      f"Kept {ns[0]} of {s[0]} filtered opportunities; W/L/D={ns[1]}/{ns[2]}/{ns[3]}, WR={ns[4]:.2f}%, net @92%={ns[5]:+.2f}u.",
      "This removes overlapping positions but does not make market outcomes independent.","",
      "## UTC-day block bootstrap (75th-percentile rule)",
      "| Payout | Mean net per active day | 95% day-block CI | Active days |",
      "|---:|---:|---:|---:|"]
    for payout in (.85,.90,.92):
        lo,hi,days=bootstrap_daily(records,main_indices,main_probs,payout)
        # Point estimate per calendar day with at least one decisive trade.
        day_count=days
        decisive=s[1]+s[2]
        net=s[1]*payout-s[2]
        mean=net/day_count if day_count else float("nan")
        lines.append(f"| {payout:.0%} | {mean:+.4f}u | {lo:+.4f} to {hi:+.4f}u | {day_count} |")
    lines += ["","## Verdict rules",
      "- This is a robustness diagnostic on the same historical TEST segment, not a new untouched holdout.",
      "- A threshold variant is not selected because it performs best on TEST; the 75th-percentile rule remains the predeclared primary rule.",
      "- A positive aggregate net is insufficient if calendar results are concentrated or the day-block interval crosses zero.",
      "- No strategy integration is authorized by this report. Prospective validation on fresh Pocket Option quotes and actual payout is still required."]
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(f"Wrote {a.out}; primary trades={s[0]}; active_days={len(months)} months={len(months)}; nonoverlap={ns[0]}")
if __name__=="__main__": main()
