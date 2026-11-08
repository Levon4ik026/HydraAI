#!/usr/bin/env python3
"""Locked follow-up audit of one previously observed NY-session PUT interaction.

No threshold search: candidate is fixed at NY 08:00-12:59, PUT signal,
ADX >= 25, +DI > -DI, and positive 12-bar close momentum.
Compares the signal to all eligible M5 bars in the exact same causal state.
"""
from __future__ import annotations
import argparse, math, random
from collections import defaultdict
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo
from long_history_validation import read_duka, make_events, m5_close_time
from reproduce_m5_bb_williams_adx import make_m5, indicators

NY=ZoneInfo("America/New_York")
WARMUP=50
HORIZON=4
PAYOUTS=(0.85,0.90,0.92)

def settle(bars,i,side):
    delta=(bars[i+HORIZON].close-bars[i+1].open)*(1 if side=="CALL" else -1)
    return "DRAW" if abs(delta)<1e-12 else "WIN" if delta>0 else "LOSS"

def metrics(rows,payout):
    w=sum(x["outcome"]=="WIN" for x in rows); l=sum(x["outcome"]=="LOSS" for x in rows)
    d=sum(x["outcome"]=="DRAW" for x in rows); n=w+l+d
    return {"n":n,"w":w,"l":l,"d":d,"wr":100*w/(w+l) if w+l else float("nan"),
            "net":w*payout-l,"pf":w*payout/l if l else (float("inf") if w else 0.0)}

def wilson(w,n,z=1.959963984540054):
    if not n:return (float("nan"),float("nan"))
    p=w/n; den=1+z*z/n
    mid=(p+z*z/(2*n))/den
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return 100*(mid-half),100*(mid+half)

def boot(values,reps=10000,block=5,seed=84119):
    if not values:return (float("nan"),float("nan"),float("nan"))
    rng=random.Random(seed); n=len(values); out=[]
    for _ in range(reps):
        s=[]
        while len(s)<n:
            k=rng.randrange(n)
            s.extend(values[(k+j)%n] for j in range(block))
        out.append(sum(s[:n])/n)
    out.sort()
    return sum(values)/n,out[int(.025*reps)],out[int(.975*reps)]

def line(label,rows,payout):
    m=metrics(rows,payout); lo,hi=wilson(m["w"],m["w"]+m["l"])
    return f"| {label} | {m['n']} | {m['w']}/{m['l']}/{m['d']} | {m['wr']:.2f}% | [{lo:.2f},{hi:.2f}] | {m['net']:+.2f}u | {m['pf']:.2f} |"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--out",type=Path,default=Path("research/NY_PUT_LOCKED_CANDIDATE_AUDIT.md"))
    args=ap.parse_args()
    m1=read_duka(args.data); segments=make_m5(m1); events=make_events(segments,15)
    ev={(e["segment"],e["bar_index"]):e for e in events}
    days=sorted({e["signal_time"].date() for e in events})
    d1,d2=days[int(.60*len(days))],days[int(.80*len(days))]
    def period(ts,settle_ts):
        if ts.date()<d1:
            return None if settle_ts.date()>=d1 else "TRAIN"
        if ts.date()<d2:
            return None if settle_ts.date()>=d2 else "VALIDATION"
        return "TEST"
    candidate=[]; candidate_nonoverlap=[]; background=[]; baseline_put=[]; monthly=defaultdict(list); monthly_period=defaultdict(list); daily=defaultdict(list)
    for sid,bars in enumerate(segments):
        ind=indicators(bars)
        for i in range(WARMUP,len(bars)-HORIZON):
            ts=bars[i].timestamp; local=ts.astimezone(NY)
            if not 8<=local.hour<13: continue
            x=ind[i]
            if x["adx"] is None or x["plus_di"] is None or x["minus_di"] is None: continue
            end=m5_close_time(bars[i+HORIZON].timestamp)
            p=period(ts,end)
            if p is None: continue
            mom=bars[i].close-bars[i-12].close
            qualifies=x["adx"]>=25 and x["plus_di"]>x["minus_di"] and mom>0
            rowbase={"period":p,"date":ts.date(),"month":ts.strftime("%Y-%m")}
            if qualifies:
                rbg={**rowbase,"segment":sid,"bar_index":i,"outcome":settle(bars,i,"PUT")}
                background.append(rbg)
            e=ev.get((sid,i))
            if e and e["direction"]=="PUT":
                r={**rowbase,"segment":sid,"bar_index":i,"outcome":settle(bars,i,"PUT")}
                baseline_put.append(r)
                if qualifies:
                    candidate.append(r); monthly[r["month"]].append(r); monthly_period[(p,r["month"])].append(r)
                    daily[(p,ts.date())].append(r)
    # One-position schedule; a new signal at the expiry candle close is eligible.
    by_segment=defaultdict(list)
    for r in candidate: by_segment[r["segment"]].append(r)
    for sid,rows in by_segment.items():
        next_allowed=-1
        for r in sorted(rows,key=lambda x:x["bar_index"]):
            if r["bar_index"]>=next_allowed:
                candidate_nonoverlap.append(r)
                next_allowed=r["bar_index"]+HORIZON

    lines=["# HYDRA — locked New York PUT candidate audit","",
      f"Data: Dukascopy EURUSD M1 BID; rows={len(m1):,}; M5 bars={sum(map(len,segments)):,}; segments={len(segments):,}.",
      f"Coverage: {m1[0].timestamp.isoformat()} — {m1[-1].timestamp.isoformat()}.",
      f"Fixed candidate: New York 08:00–12:59 local (DST-aware), frozen BB/Williams/ADX PUT signal, ADX >=25, +DI > -DI, close[i] > close[i-12].",
      f"Entry next M5 open; exit fourth M5 close; 20 minutes. Split boundaries: TRAIN < {d1}; VALIDATION < {d2}; TEST >= {d2}.",
      "No threshold tuning in this audit. The candidate was identified in prior exploratory analysis; this is a follow-up robustness check, not a pristine confirmatory holdout.",
      "The matched background is every eligible M5 bar satisfying the same time and state conditions, entered PUT at next open with the same 20-minute settlement. Signal and background bars can overlap in time; uncertainty intervals are descriptive.","",
      "## Candidate versus matched background by chronological period","",
      "| Period / sample | n | W/L/D | WR | Wilson 95% CI | Net @92% | PF @92% |",
      "|---|---:|---:|---:|---:|---:|---:|"]
    for p in ("TRAIN","VALIDATION","TEST","ALL"):
        c=[r for r in candidate if p=="ALL" or r["period"]==p]
        b=[r for r in background if p=="ALL" or r["period"]==p]
        lines.append(line(f"{p} candidate",c,.92))
        lines.append(line(f"{p} background",b,.92))
    lines += ["","## Candidate one-position schedule (overlap suppressed)","",
      "| Period | n | W/L/D | WR | Net @92% | PF @92% |","|---|---:|---:|---:|---:|---:|"]
    for p in ("TRAIN","VALIDATION","TEST","ALL"):
        rows=[r for r in candidate_nonoverlap if p=="ALL" or r["period"]==p]
        m=metrics(rows,.92)
        lines.append(f"| {p} | {m['n']} | {m['w']}/{m['l']}/{m['d']} | {m['wr']:.2f}% | {m['net']:+.2f}u | {m['pf']:.2f} |")
    lines += ["","## Monthly results by chronological split","",
      "| Period | Month | n | W/L/D | WR | Net @92% |","|---|---|---:|---:|---:|---:|"]
    for p in ("TRAIN","VALIDATION","TEST"):
        for (pp,mon),rows in sorted(monthly_period.items()):
            if pp!=p: continue
            m=metrics(rows,.92)
            lines.append(f"| {p} | {mon} | {m['n']} | {m['w']}/{m['l']}/{m['d']} | {m['wr']:.2f}% | {m['net']:+.2f}u |")
    lines += ["","## Candidate versus ordinary New York PUT signals","",
      "| Period | n | W/L/D | WR | Wilson 95% CI | Net @92% | PF @92% |",
      "|---|---:|---:|---:|---:|---:|---:|"]
    for p in ("TRAIN","VALIDATION","TEST","ALL"):
        lines.append(line(p,[r for r in baseline_put if p=="ALL" or r["period"]==p],.92))
    lines += ["","## Payout sensitivity — candidate only","",
      "| Period | Payout | Net units | PF | Break-even WR | Actual WR |",
      "|---|---:|---:|---:|---:|---:|"]
    for p in ("TRAIN","VALIDATION","TEST","ALL"):
        rows=[r for r in candidate if p=="ALL" or r["period"]==p]
        for pay in PAYOUTS:
            m=metrics(rows,pay)
            lines.append(f"| {p} | {pay:.0%} | {m['net']:+.2f} | {m['pf']:.3f} | {100/(1+pay):.2f}% | {m['wr']:.2f}% |")
    lines += ["","## Monthly candidate results (all periods)","",
      "| Month | n | W/L/D | WR | Net @92% |","|---|---:|---:|---:|---:|"]
    for mon,rows in sorted(monthly.items()):
        m=metrics(rows,.92)
        lines.append(f"| {mon} | {m['n']} | {m['w']}/{m['l']}/{m['d']} | {m['wr']:.2f}% | {m['net']:+.2f}u |")
    lines += ["","## Candidate daily net — 5-day block bootstrap","",
      "| Period | Active signal days | Mean net/active day | 95% block CI | Positive-day share |","|---|---:|---:|---:|---:|"]
    for p in ("TRAIN","VALIDATION","TEST","ALL"):
        dates=sorted({r["date"] for r in candidate if p=="ALL" or r["period"]==p})
        vals=[]
        for d in dates:
            rows=daily[(next((r["period"] for r in candidate if r["date"]==d),p),d)]
            vals.append(sum(.92 if r["outcome"]=="WIN" else -1 if r["outcome"]=="LOSS" else 0 for r in rows))
        mean,lo,hi=boot(vals,seed=84119+len(vals))
        pos=100*sum(v>0 for v in vals)/len(vals) if vals else float("nan")
        lines.append(f"| {p} | {len(dates)} | {mean:+.3f}u | [{lo:+.3f},{hi:+.3f}] | {pos:.1f}% |")
    lines += ["","## Decision rules and limitations","",
      "- Do not promote unless candidate beats matched background, has adequate counts, and remains positive across TRAIN, VALIDATION and TEST.",
      "- Positive net at 92% is not sufficient if payout sensitivity or monthly stability is poor.",
      "- Wilson intervals treat trades as independent; block bootstrap partially addresses serial clustering but not all overlapping-trade dependence.",
      "- Dukascopy BID prices differ from Pocket Option quotes; actual payout, spread, and execution may differ.",
      "- No live or demo trades were executed; no local files or production math were changed.",""]
    args.out.parent.mkdir(parents=True,exist_ok=True); args.out.write_text("\n".join(lines),encoding="utf-8")
    print(f"Candidate={len(candidate)}; matched background={len(background)}; ordinary NY PUT={len(baseline_put)}; splits={d1}/{d2}; wrote {args.out}")

if __name__=="__main__": main()
