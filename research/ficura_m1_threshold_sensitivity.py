#!/usr/bin/env python3
"""Causal threshold-length sensitivity for frozen Fičura M1 inverse.

Research-only. No optimization: compares predeclared threshold_n policies using
same k=64, p=.999, next-open entry, exact inverse, 1/2/3/5/8 bar expiries.
"""
from __future__ import annotations
import argparse, math
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
import random

from ficura_jump_replication import (
    load_m1, split_segments, nonoverlap, outcome, split_name,
    SOURCE_PARAMS, BINARY_HORIZONS, PAYOUT, make_events,
)
from lee_mykland_jump import detect_jumps

BOOTSTRAPS = 5000

def make_events_with_n(segments, k, p, threshold_n):
    events=[]
    global_index=0
    for sid,seg in enumerate(segments):
        found=detect_jumps([b.close for b in seg], k=k, confidence=p, threshold_n=threshold_n)
        for jump in found:
            events.append({"sid":sid,"i":jump.index,"global":global_index+jump.index,
                           "ts":seg[jump.index].ts,"direction":jump.direction,
                           "l":jump.l_statistic,"threshold":jump.threshold})
        global_index += len(seg)
    return sorted(events,key=lambda x:x["global"])

def score(seg,e,h):
    base=outcome(seg,e,h,e["direction"])
    if base is None: return None
    delta=base["exit"]-base["entry"]
    if e["direction"]=="CALL": delta=-delta
    label="DRAW" if abs(delta)<=1e-12 else "WIN" if delta>0 else "LOSS"
    return {"outcome":label,"day":e["ts"].date(),"month":e["ts"].strftime("%Y-%m"),
            "signal_ts":e["ts"]}

def summarize(rows):
    w=sum(x["outcome"]=="WIN" for x in rows)
    l=sum(x["outcome"]=="LOSS" for x in rows)
    d=sum(x["outcome"]=="DRAW" for x in rows)
    return len(rows),w,l,d,(100*w/(w+l) if w+l else float("nan")),w*PAYOUT-l

def bootstrap(rows, block_days, iterations, seed):
    if not rows: return None
    first=min(x["day"] for x in rows); last=max(x["day"] for x in rows)
    days=[first+timedelta(days=i) for i in range((last-first).days+1)]
    by=defaultdict(list)
    for x in rows: by[x["day"]].append(x["outcome"])
    rng=random.Random(seed+block_days)
    need=math.ceil(len(days)/block_days); maxstart=max(0,len(days)-block_days)
    nets=[]
    for _ in range(iterations):
        sample=[]
        for _ in range(need):
            start=rng.randint(0,maxstart)
            for day in days[start:start+block_days]: sample.extend(by.get(day,()))
        w=sum(x=="WIN" for x in sample); l=sum(x=="LOSS" for x in sample)
        nets.append(w*PAYOUT-l)
    nets.sort()
    q=lambda p:nets[min(len(nets)-1,int((len(nets)-1)*p))]
    return q(.025),q(.975),100*sum(x>0 for x in nets)/len(nets)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--out",type=Path,default=Path("FICURA_M1_THRESHOLD_SENSITIVITY.md"))
    ap.add_argument("--iterations",type=int,default=BOOTSTRAPS)
    args=ap.parse_args()
    bars=load_m1(args.data)
    segments=split_segments(bars,60)
    k,p,_=SOURCE_PARAMS[1]
    train_end=int(len(bars)*.60); val_end=int(len(bars)*.80)
    n_full=max(3,len(bars)-len(segments))
    n_train=max(3,train_end-sum(1 for s in segments if s and s[0].ts.timestamp()*1000 >= 0)) # replaced below with deterministic train returns
    # Count only bars in chronological TRAIN, minus one return per uninterrupted segment portion.
    train_bars=train_end
    train_segment_count=sum(1 for s in segments if s and s[0].ts <= bars[train_end-1].ts)
    n_train=max(3,train_bars-train_segment_count)
    policies={"FULL_HISTORY_REFERENCE":n_full,"TRAIN_FROZEN":n_train,
              "ROLLING_1D_EQUIVALENT":1440,"ROLLING_1W_EQUIVALENT":10080,
              "ROLLING_1M_EQUIVALENT":43200}
    lines=["# Fičura M1 inverse — threshold length sensitivity","",
      f"Rows={len(bars):,}; segments={len(segments):,}; k={k}; p={p}; payout={PAYOUT:.2f}.",
      "Same causal next-M1-open entry, exact inverse, non-overlap, 60/20/20 chronological split and purge rules.",
      "No parameter optimization. TRAIN_FROZEN uses only the TRAIN partition length; rolling equivalents are fixed, predeclared n policies.",
      "FULL_HISTORY_REFERENCE reproduces the prior audit and is explicitly non-causal as a live policy.",
      "Threshold_n changes only the extreme-value threshold; all other detector and trade rules remain fixed.",
      "Dukascopy BID proxy, not Pocket Option executable quotes. TEST is previously inspected and not pristine.","",
      "## TEST results by threshold policy and expiry","",
      "| Policy | n | h | Events | N | W/L/D | WR | Net u | 5d Net 95% | P(Net>0) |",
      "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    all_event_counts={}
    for policy,n in policies.items():
        events=make_events_with_n(segments,k,p,n)
        all_event_counts[policy]=len(events)
        for h in BINARY_HORIZONS:
            chosen=nonoverlap(events,h); rows=[]
            for e in chosen:
                split=split_name(e["global"],train_end,val_end)
                exit_g=e["global"]+h
                if (split=="TRAIN" and exit_g>=train_end) or (split=="VALIDATION" and exit_g>=val_end): continue
                if split!="TEST": continue
                r=score(segments[e["sid"]],e,h)
                if r: rows.append(r)
            nn,w,l,d,wr,net=summarize(rows)
            b=bootstrap(rows,5,args.iterations,20261111+n+h) if rows else None
            if b:
                lines.append(f"| {policy} | {n} | {h} | {len(events)} | {nn} | {w}/{l}/{d} | {wr:.2f}% | {net:+.2f} | [{b[0]:+.2f}, {b[1]:+.2f}] | {b[2]:.1f}% |")
    lines += ["","## Event-count sensitivity","",
      "| Policy | threshold_n | Total jump events |",
      "|---|---:|---:|"]
    for name,n in policies.items(): lines.append(f"| {name} | {n} | {all_event_counts[name]} |")
    lines += ["","## Decision guardrails","",
      "- The fixed TRAIN_FROZEN policy is the cleanest historical causal alternative: its n is determined before VALIDATION/TEST and then held fixed.",
      "- Rolling 1D/1W/1M equivalents are threshold normalization scenarios, not rolling estimators of volatility; the local bipower estimator remains unchanged.",
      "- Do not choose the best threshold policy from TEST. A robust candidate should retain direction and broadly similar edge across plausible predeclared n policies.",
      "- All five expiries are shown to expose selection effects. No expiry is promoted from this table.",
      "- A final claim requires fresh untouched data and quote-level replay at actual Pocket Option payout/settlement rules.",""]
    args.out.write_text("\n".join(lines),encoding="utf-8")
    print(f"WROTE={args.out} ROWS={len(bars)} EVENTS_BY_POLICY={all_event_counts}")

if __name__=="__main__": main()
