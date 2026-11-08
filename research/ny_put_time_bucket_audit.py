#!/usr/bin/env python3
"""Predeclared NY-local time-of-day robustness audit for the locked PUT state.

No time-window or threshold optimization: six fixed clock buckets are reported
for the same frozen PUT signal and causal state used in the prior NY candidate.
Dukascopy BID, next M5 open, fourth following M5 close (20m).
"""
from __future__ import annotations
import argparse, math
from collections import defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo
from long_history_validation import read_duka, make_events, m5_close_time
from reproduce_m5_bb_williams_adx import make_m5, indicators

NY = ZoneInfo("America/New_York")
WARMUP = 50
HORIZON = 4
PAYOUT = 0.92
BUCKETS = ((0,4,"00-03"),(4,8,"04-07"),(8,13,"08-12"),(13,17,"13-16"),(17,21,"17-20"),(21,24,"21-23"))

def outcome(bars, i):
    delta = bars[i+HORIZON].close - bars[i+1].open
    return "DRAW" if abs(delta)<1e-12 else "WIN" if delta<0 else "LOSS"

def stats(rows):
    w=sum(r["outcome"]=="WIN" for r in rows); l=sum(r["outcome"]=="LOSS" for r in rows)
    d=sum(r["outcome"]=="DRAW" for r in rows); n=w+l+d
    wr=100*w/(w+l) if w+l else float("nan")
    net=w*PAYOUT-l
    pf=w*PAYOUT/l if l else (float("inf") if w else 0.0)
    if w+l:
        p=w/(w+l); z=1.959963984540054; nn=w+l; den=1+z*z/nn
        mid=(p+z*z/(2*nn))/den; half=z*math.sqrt(p*(1-p)/nn+z*z/(4*nn*nn))/den
        ci=f"[{100*(mid-half):.2f},{100*(mid+half):.2f}]"
    else: ci="n/a"
    return n,w,l,d,wr,net,pf,ci

def row(label, rows):
    n,w,l,d,wr,net,pf,ci=stats(rows)
    return f"| {label} | {n} | {w}/{l}/{d} | {wr:.2f}% | {ci} | {net:+.2f}u | {pf:.2f} |"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--out",type=Path,default=Path("research/NY_PUT_TIME_BUCKET_AUDIT.md"))
    a=ap.parse_args()
    m1=read_duka(a.data); segments=make_m5(m1); events=make_events(segments,15)
    ev={(e["segment"],e["bar_index"]):e for e in events}
    days=sorted({e["signal_time"].date() for e in events})
    d1,d2=days[int(.60*len(days))],days[int(.80*len(days))]
    def period(ts,end):
        if ts.date()<d1: return None if end.date()>=d1 else "TRAIN"
        if ts.date()<d2: return None if end.date()>=d2 else "VALIDATION"
        return "TEST"
    cand=defaultdict(list); bg=defaultdict(list); ordinary=defaultdict(list)
    cand_month=defaultdict(list); cand_year=defaultdict(list)
    for sid,bars in enumerate(segments):
        ind=indicators(bars)
        for i in range(WARMUP,len(bars)-HORIZON):
            ts=bars[i].timestamp; local=ts.astimezone(NY)
            bucket=next((name for lo,hi,name in BUCKETS if lo<=local.hour<hi),None)
            x=ind[i]
            if x["adx"] is None or x["plus_di"] is None or x["minus_di"] is None: continue
            end=m5_close_time(bars[i+HORIZON].timestamp); p=period(ts,end)
            if p is None: continue
            key=(p,bucket)
            qualifies=(x["adx"]>=25 and x["plus_di"]>x["minus_di"] and bars[i].close>bars[i-12].close)
            if qualifies:
                bg[key].append({"outcome":outcome(bars,i)})
            e=ev.get((sid,i))
            if e and e["direction"]=="PUT":
                r={"outcome":outcome(bars,i),"segment":sid,"i":i,"period":p,"bucket":bucket,"month":ts.strftime("%Y-%m"),"year":str(ts.year)}
                ordinary[key].append(r)
                if qualifies:
                    cand[key].append(r); cand_month[(p,r["month"])].append(r); cand_year[(p,r["year"])].append(r)
    nonoverlap=defaultdict(list)
    for p in ("TRAIN","VALIDATION","TEST"):
        for _,_,b in BUCKETS:
            byseg=defaultdict(list)
            for r in cand[(p,b)]: byseg[r["segment"]].append(r)
            for sid,rows in byseg.items():
                allowed=-1
                for r in sorted(rows,key=lambda z:z["i"]):
                    if r["i"]>=allowed:
                        nonoverlap[(p,b)].append(r); allowed=r["i"]+HORIZON
    lines=[
      "# HYDRA — locked New York PUT time-of-day robustness audit","",
      f"Data: Dukascopy EURUSD M1 BID; M1 rows={len(m1):,}; M5 bars={sum(map(len,segments)):,}; segments={len(segments):,}.",
      f"Coverage: {m1[0].timestamp.isoformat()} — {m1[-1].timestamp.isoformat()}.",
      f"Split boundaries: TRAIN < {d1}; VALIDATION < {d2}; TEST >= {d2}. All hours use America/New_York local clock with DST.",
      "Frozen state: BB(20,2)/Williams %R(14)/ADX(14) PUT signal; ADX >=25; +DI > -DI; close[i] > close[i-12]. No parameter tuning.",
      "Entry next M5 open; settlement at fourth following M5 close (20m). Hypothetical PUT result from BID candles; payout 92%.",
      "The six clock buckets were fixed before this run. The 08-12 bucket is the previously observed candidate window; other buckets are controls, not a search for a new best window.",
      "Matched background includes every eligible M5 bar with the same time bucket and causal state, irrespective of whether the frozen strategy emitted a PUT signal. These hypothetical outcomes overlap and are descriptive.","",
      "## Candidate PUT signals by New York clock bucket","",
      "| Period / bucket | n | W/L/D | WR | Wilson 95% CI | Net @92% | PF |","|---|---:|---:|---:|---:|---:|---:|"]
    for p in ("TRAIN","VALIDATION","TEST"):
        for _,_,b in BUCKETS:
            lines.append(row(f"{p} {b}",cand[(p,b)]))
        rows=[r for _,_,b in BUCKETS for r in cand[(p,b)]]
        lines.append(row(f"{p} ALL HOURS",rows))
    for p in ("TRAIN","VALIDATION","TEST"):
        for label,bs in (("08-12",["08-12"]),("OUTSIDE 08-12",[b for _,_,b in BUCKETS if b!="08-12"])):
            rows=[r for b in bs for r in cand[(p,b)]]
            lines.append(row(f"{p} {label}",rows))
    lines += ["","## Same-state matched background by clock bucket","",
      "| Period / bucket | n | W/L/D | WR | Wilson 95% CI | Net @92% | PF |","|---|---:|---:|---:|---:|---:|---:|"]
    for p in ("TRAIN","VALIDATION","TEST"):
        for _,_,b in BUCKETS: lines.append(row(f"{p} {b}",bg[(p,b)]))
    lines += ["","## Candidate with one-position schedule (no overlapping expiries)","",
      "| Period / bucket | n | W/L/D | WR | Net @92% | PF |","|---|---:|---:|---:|---:|---:|"]
    for p in ("TRAIN","VALIDATION","TEST"):
        for _,_,b in BUCKETS:
            n,w,l,d,wr,net,pf,ci=stats(nonoverlap[(p,b)])
            lines.append(f"| {p} {b} | {n} | {w}/{l}/{d} | {wr:.2f}% | {net:+.2f}u | {pf:.2f} |")
    lines += ["","## Ordinary frozen-strategy PUT signals by bucket (without extra state filter)","",
      "| Period / bucket | n | W/L/D | WR | Net @92% | PF |","|---|---:|---:|---:|---:|---:|"]
    for p in ("TRAIN","VALIDATION","TEST"):
        for _,_,b in BUCKETS:
            n,w,l,d,wr,net,pf,ci=stats(ordinary[(p,b)])
            lines.append(f"| {p} {b} | {n} | {w}/{l}/{d} | {wr:.2f}% | {net:+.2f}u | {pf:.2f} |")
    lines += ["","## Candidate month-by-month","",
      "| Period | Month | n | W/L/D | WR | Net @92% |","|---|---|---:|---:|---:|---:|"]
    for (p,m),rows in sorted(cand_month.items()):
        n,w,l,d,wr,net,pf,ci=stats(rows); lines.append(f"| {p} | {m} | {n} | {w}/{l}/{d} | {wr:.2f}% | {net:+.2f}u |")
    lines += ["","## Candidate by calendar year","",
      "| Period | Year | n | W/L/D | WR | Net @92% |","|---|---|---:|---:|---:|---:|"]
    for (p,y),rows in sorted(cand_year.items()):
        n,w,l,d,wr,net,pf,ci=stats(rows); lines.append(f"| {p} | {y} | {n} | {w}/{l}/{d} | {wr:.2f}% | {net:+.2f}u |")
    lines += ["","## Interpretation guardrails","",
      "- Do not select a new time bucket from these results and call it validated; the six-bucket comparison is diagnostic and multiple comparisons inflate false-discovery risk.",
      "- Evidence for a true NY 08-12 effect requires it to outperform the same locked state outside the window across chronological splits, not merely show positive net.",
      "- Counts and confidence intervals matter; small buckets are inconclusive even with high WR.",
      "- The candidate was discovered in prior exploratory analysis, so this audit is not pristine confirmatory evidence.",
      "- Dukascopy BID differs from Pocket Option quotes; payout, spreads, and execution may differ. No trades were executed and no production files changed.",""]
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text("\n".join(lines),encoding="utf-8")
    print(f"rows={len(m1)}; events={len(events)}; candidate={sum(map(len,cand.values()))}; wrote {a.out}")
if __name__=="__main__": main()
