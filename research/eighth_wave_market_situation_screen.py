#!/usr/bin/env python3
"""Eighth-wave EURUSD M5 discovery: round-level reactions, retests, impulse aftershock.
Research-only. Causal signals, fixed definitions, exact direction inversion.
"""
from __future__ import annotations
import argparse, statistics
from collections import defaultdict
from pathlib import Path
from expanded_strategy_screen import read_m1, outcome, stats
from long_history_validation import make_m5

HORIZONS=(1,2,3,4,6,12)
PAYOUT=0.92

def events_for_segment(bars):
    ev=defaultdict(list)
    tr=[]
    for i,b in enumerate(bars):
        tr.append(b.high-b.low if i==0 else max(b.high-b.low,abs(b.high-bars[i-1].close),abs(b.low-bars[i-1].close)))
    # EURUSD big figures: 50 pips (0.0050); touch/rejection confirmed on signal close.
    for i in range(25,len(bars)-13):
        b=bars[i]; p=bars[i-1]
        grid=0.0050
        level=round(b.close/grid)*grid
        dist=min(abs(b.low-level),abs(b.high-level),abs(b.close-level))
        rng=max(b.high-b.low,1e-12)
        if dist<=0.00015:
            if b.low<=level+0.00015 and b.close>level+0.00005 and b.close>b.open:
                ev["BIG_FIGURE_SUPPORT_REJECTION_CALL"].append((i,"CALL"))
            if b.high>=level-0.00015 and b.close<level-0.00005 and b.close<b.open:
                ev["BIG_FIGURE_RESISTANCE_REJECTION_PUT"].append((i,"PUT"))
        # Broken 12-bar swing level, then first retest within 1-6 bars with close back in breakout direction.
        prior_hi=max(x.high for x in bars[i-13:i-1])
        prior_lo=min(x.low for x in bars[i-13:i-1])
        for j in range(max(13,i-6),i):
            q=bars[j]
            if q.close>max(x.high for x in bars[j-12:j]):
                if b.low<=q.close+0.00010 and b.close>q.close and b.close>b.open:
                    ev["BROKEN_HIGH_RETEST_CONTINUATION_CALL"].append((i,"CALL")); break
            if q.close<min(x.low for x in bars[j-12:j]):
                if b.high>=q.close-0.00010 and b.close<q.close and b.close<b.open:
                    ev["BROKEN_LOW_RETEST_CONTINUATION_PUT"].append((i,"PUT")); break
        # Aftershock: a completed shock candle in previous bar, then response candle.
        med=statistics.median(tr[i-21:i-1])
        if med>0 and tr[i-1]>=2.0*med:
            shock=bars[i-1]
            if shock.close>shock.open and b.close>b.open and b.close>shock.close:
                ev["UP_SHOCK_SECOND_BAR_CONTINUATION_CALL"].append((i,"CALL"))
            if shock.close<shock.open and b.close<b.open and b.close<shock.close:
                ev["DOWN_SHOCK_SECOND_BAR_CONTINUATION_PUT"].append((i,"PUT"))
            if shock.close>shock.open and b.close<b.open and b.close<shock.close:
                ev["UP_SHOCK_SECOND_BAR_REVERSAL_PUT"].append((i,"PUT"))
            if shock.close<shock.open and b.close>b.open and b.close>shock.close:
                ev["DOWN_SHOCK_SECOND_BAR_REVERSAL_CALL"].append((i,"CALL"))
    return ev

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    m1=read_m1(a.data); segments=make_m5(m1)
    days=sorted({b.timestamp.date() for s in segments for b in s})
    if len(days)<30: raise SystemExit("Insufficient history")
    d1=days[int(.60*len(days))]; d2=days[int(.80*len(days))]
    raw=defaultdict(int); accepted=defaultdict(list); families=set(); purged=0
    for sid,bars in enumerate(segments):
        ev=events_for_segment(bars); families.update(ev)
        for name,items in ev.items():
            for h in HORIZONS:
                rows=[]
                for i,side in items:
                    if i+h>=len(bars): continue
                    day=bars[i].timestamp.date(); settle=(bars[i+h].timestamp.replace(minute=0,second=0,microsecond=0))
                    settle=bars[i+h].timestamp
                    period="TRAIN" if day<d1 else "VALIDATION" if day<d2 else "TEST"
                    boundary=d1 if period=="TRAIN" else d2 if period=="VALIDATION" else None
                    if boundary and settle.date()>=boundary:
                        purged+=1; continue
                    rows.append((i,side,period))
                raw[(name,h)]+=len(rows)
                for period in ("TRAIN","VALIDATION","TEST"):
                    nxt=-1
                    for i,side,p in sorted((r for r in rows if r[2]==period),key=lambda z:z[0]):
                        if i<nxt: continue
                        accepted[(name,h,period,"ORIGINAL")].append(outcome(bars,i,side,h))
                        inverse="PUT" if side=="CALL" else "CALL"
                        accepted[(name,h,period,"INVERTED")].append(outcome(bars,i,inverse,h))
                        nxt=i+h
    lines=[
      "# Eighth-wave EURUSD M5 market-situation discovery","",
      f"Source: Dukascopy EURUSD M1 BID; M1={len(m1):,}; M5={sum(map(len,segments)):,}; gap-separated segments={len(segments)}.",
      f"Coverage: {m1[0].timestamp.isoformat()} — {m1[-1].timestamp.isoformat()}.",
      f"Chronological date splits: TRAIN < {d1}; VALIDATION {d1}–{d2}; TEST >= {d2}. Purged boundary-crossing outcomes={purged:,}.",
      "Predeclared causal families: 50-pip big-figure support/resistance rejection; retest of a prior 12-bar breakout level within six bars; second-bar continuation/reversal after a >=2x prior-20-bar median true-range shock.",
      "Signals use closed M5 bars; entry next M5 open; expiry after 5/10/15/20/30/60 minutes. One position per family/expiry/segment/split. Original and inverse use identical event timestamps and schedule; only direction flips.",
      "Payout assumption +0.92/-1/0; decisive break-even 52.083%. Dukascopy BID is not Pocket Option executable pricing. Exploratory discovery only; serial dependence and multiple testing remain; TEST has prior exploratory exposure.","",
      "| Family | Variant | Expiry | Split | n | W/L/D | Decisive WR | Wilson 95% CI | Net u | Max DD u | Raw events |",
      "|---|---|---:|---|---:|---|---:|---|---:|---:|---:|"
    ]
    for (name,h,period,var),xs in sorted(accepted.items()):
        s=stats(xs); ci=s[5]; wr="n/a" if s[4] is None else f"{s[4]:.2f}%"; ci_txt="n/a" if ci is None else f"[{ci[0]:.2f},{ci[1]:.2f}]%"
        lines.append(f"| {name} | {var} | {h*5}m | {period} | {s[0]} | {s[1]}/{s[2]}/{s[3]} | {wr} | {ci_txt} | {s[6]:+.2f} | {s[7]:.2f} | {raw[(name,h)]} |")
    lines += ["","## Screening notes","",
      "- Candidate priority requires a promising VALIDATION result, adequate sample, positive net under the stated payout, and review of TRAIN/TEST consistency.",
      "- Do not promote a TEST-only result. A weak original is not discarded until its exact-schedule inverse is inspected.",
      "- This wave expands the candidate pool; it does not profile previously registered strategies by market regime.",
      "- Any selected context must be frozen before a genuinely untouched forward sample; no post-hoc threshold fitting.",""]
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text("\n".join(lines),encoding="utf-8")
    print(f"Eighth-wave complete: M1={len(m1):,}; M5={sum(map(len,segments)):,}; families={len(families)}; report={a.out}")

if __name__=="__main__": main()
