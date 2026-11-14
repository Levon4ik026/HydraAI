#!/usr/bin/env python3
"""Predeclared New York morning mechanism audit for frozen EURUSD M5 signals."""
from __future__ import annotations
import argparse, random
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from long_history_validation import read_duka, make_events, PAYOUT, m5_close_time
from reproduce_m5_bb_williams_adx import make_m5, indicators

WARMUP=50
HORIZON=4
NY=ZoneInfo("America/New_York")

def outcome(bars,i,side):
    delta=(bars[i+HORIZON].close-bars[i+1].open)*(1 if side=="CALL" else -1)
    return "DRAW" if abs(delta)<1e-12 else "WIN" if delta>0 else "LOSS"

def stats(rows):
    w=sum(r["outcome"]=="WIN" for r in rows)
    l=sum(r["outcome"]=="LOSS" for r in rows)
    d=sum(r["outcome"]=="DRAW" for r in rows)
    dec=w+l
    return len(rows),w,l,d,100*w/dec if dec else float("nan"),w*PAYOUT-l,(w*PAYOUT/l if l else (float("inf") if w else 0.0))

def fmt(label,rows):
    n,w,l,d,wr,net,pf=stats(rows)
    return f"| {label} | {n} | {w}/{l}/{d} | {wr:.2f}% | {net:+.2f}u | {pf:.2f} |"

def band(x): return "15-20" if x<20 else "20-25" if x<25 else "25+"
def state(r): return (r["adx_band"],r["di_state"],r["mom12_state"])

def block_bootstrap(values,reps=5000,block=5,seed=20261108):
    if not values: return (float("nan"),float("nan"),float("nan"))
    rng=random.Random(seed); n=len(values); means=[]
    for _ in range(reps):
        sample=[]
        while len(sample)<n:
            start=rng.randrange(n)
            sample.extend(values[(start+j)%n] for j in range(block))
        means.append(sum(sample[:n])/n)
    means.sort()
    return sum(values)/n,means[int(.025*reps)],means[int(.975*reps)]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--out",type=Path,default=Path("research/NY_SESSION_MECHANISM_AUDIT.md"))
    a=ap.parse_args()
    m1=read_duka(a.data); segments=make_m5(m1); events=make_events(segments,15)
    event_map={(e["segment"],e["bar_index"]):e for e in events}
    days=sorted({e["signal_time"].date() for e in events})
    d1,d2=days[int(len(days)*.60)],days[int(len(days)*.80)]
    trades=[]; background=[]; daily_net=defaultdict(float); eligible_days=defaultdict(set)
    for sid,bars in enumerate(segments):
        ind=indicators(bars)
        for i in range(WARMUP,len(bars)-HORIZON):
            ts=bars[i].timestamp; local=ts.astimezone(NY)
            if not 8<=local.hour<13: continue
            cur=ind[i]
            if cur["adx"] is None or cur["plus_di"] is None or cur["minus_di"] is None: continue
            settle=m5_close_time(bars[i+HORIZON].timestamp)
            if ts.date()<d1:
                if settle.date()>=d1: continue
                period="TRAIN"
            elif ts.date()<d2:
                if settle.date()>=d2: continue
                period="VALIDATION"
            else: period="TEST"
            di="PLUS" if cur["plus_di"]>cur["minus_di"] else "MINUS"
            mom=bars[i].close-bars[i-12].close
            mom_state="UP" if mom>0 else "DOWN" if mom<0 else "FLAT"
            slot="08-09:59" if local.hour<10 else "10-11:59" if local.hour<12 else "12-12:59"
            base={"period":period,"date":ts.date(),"slot":slot,"adx_band":band(cur["adx"]),
                  "di_state":di,"mom12_state":mom_state}
            background.append({**base,"outcome":outcome(bars,i,"CALL")})
            eligible_days[period].add(ts.date())
            e=event_map.get((sid,i))
            if e:
                side=e["direction"]; result=outcome(bars,i,side)
                row={**base,"side":side,"outcome":result}
                trades.append(row)
                daily_net[(period,ts.date())]+=PAYOUT if result=="WIN" else -1 if result=="LOSS" else 0

    lines=["# HYDRA — New York morning mechanism audit","",
      f"Source: Dukascopy EURUSD M1 BID; M1 rows={len(m1):,}; complete M5={sum(map(len,segments)):,}; segments={len(segments):,}.",
      f"Coverage: {m1[0].timestamp.isoformat()} — {m1[-1].timestamp.isoformat()}.",
      f"NY morning frozen-strategy events={len(trades):,}; eligible background bars={len(background):,}.",
      f"NY morning fixed at 08:00-12:59 America/New_York, DST-aware. Entry next M5 open; exit fourth M5 close (20m); payout +{PAYOUT:.2f}/-1/0.",
      f"Chronological split: TRAIN < {d1}; VALIDATION < {d2}; TEST >= {d2}. Settlement-crossing rows purged.",
      "Causal state features: ADX bands 15-20/20-25/25+, DI dominance, and 12-bar momentum sign. Background contains all eligible M5 bars in the same local-time window and same 20m convention.",
      "Exploratory only; the coarse UTC session result motivated this predeclared DST-aware audit. TEST has already been exposed to prior exploration. No filters promoted.","",
      "## Strategy results by period and direction","",
      "| Period / side | n | W/L/D | Decisive WR | Net | PF |","|---|---:|---:|---:|---:|---:|"]
    for p in ("TRAIN","VALIDATION","TEST"):
        for side in ("CALL","PUT"):
            lines.append(fmt(f"{p}/{side}",[r for r in trades if r["period"]==p and r["side"]==side]))
        lines.append(fmt(f"{p}/ALL",[r for r in trades if r["period"]==p]))
    lines += ["","## Fixed local-time subwindows","",
      "| Period / local time / side | n | W/L/D | Decisive WR | Net | PF |","|---|---:|---:|---:|---:|---:|"]
    for p in ("TRAIN","VALIDATION","TEST"):
        for slot in ("08-09:59","10-11:59","12-12:59"):
            for side in ("CALL","PUT"):
                lines.append(fmt(f"{p}/{slot}/{side}",[r for r in trades if r["period"]==p and r["slot"]==slot and r["side"]==side]))
    lines += ["","## Causal state breakdown (cells with n >= 8)","",
      "| Period/side/ADX/DI/momentum | n | W/L/D | Decisive WR | Net | PF |","|---|---:|---:|---:|---:|---:|"]
    for p in ("TRAIN","VALIDATION","TEST"):
        for side in ("CALL","PUT"):
            for ab in ("15-20","20-25","25+"):
                for di in ("PLUS","MINUS"):
                    for mom in ("UP","DOWN","FLAT"):
                        sub=[r for r in trades if r["period"]==p and r["side"]==side and r["adx_band"]==ab and r["di_state"]==di and r["mom12_state"]==mom]
                        if len(sub)>=8: lines.append(fmt(f"{p}/{side}/{ab}/{di}/{mom}",sub))
    bg=defaultdict(lambda:[0,0,0])
    for r in background:
        c=bg[(r["period"],state(r))]
        c[0 if r["outcome"]=="WIN" else 1 if r["outcome"]=="LOSS" else 2]+=1
    lines += ["","## Strategy versus matched background","",
      "| Period/side | Strategy n | Strategy WR | Matched background WR | Lift | Matched n |","|---|---:|---:|---:|---:|---:|"]
    for p in ("TRAIN","VALIDATION","TEST"):
        for side in ("CALL","PUT"):
            sub=[r for r in trades if r["period"]==p and r["side"]==side]
            actual=stats(sub)[4]; expected=used=0.0
            for r in sub:
                c=bg[(p,state(r))]; den=c[0]+c[1]
                if den:
                    expected+=(c[0] if side=="CALL" else c[1])/den; used+=1
            exp=100*expected/used if used else float("nan")
            lines.append(f"| {p}/{side} | {len(sub)} | {actual:.2f}% | {exp:.2f}% | {actual-exp:+.2f} pp | {int(used)} |")
    lines += ["","## Daily net stability — 5-day circular block bootstrap","",
      "| Period | Eligible NY days | Mean net/day | Bootstrap 95% CI | Positive-day share |","|---|---:|---:|---:|---:|"]
    for p in ("TRAIN","VALIDATION","TEST"):
        dates=sorted(eligible_days[p]); vals=[daily_net[(p,d)] for d in dates]
        mean,lo,hi=block_bootstrap(vals,seed=20261108+len(vals))
        pos=100*sum(x>0 for x in vals)/len(vals) if vals else float("nan")
        lines.append(f"| {p} | {len(vals)} | {mean:+.4f}u | [{lo:+.4f}, {hi:+.4f}] | {pos:.1f}% |")
    lines += ["","## Guardrails","",
      "- A credible session effect should be positive in TRAIN, VALIDATION and TEST, with adequate sample size.",
      "- A plausible mechanism should beat the matched background after conditioning on ADX, DI dominance and prior 12-bar momentum.",
      "- The daily moving-block bootstrap is descriptive; five-day blocks may not capture longer regime persistence.",
      "- External BID quotes are not Pocket Option quotes; spread, payout changes and execution are not modeled.",
      "- No local files changed; no math core changed; no filter integrated; no trades executed.",""]
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text("\n".join(lines),encoding="utf-8")
    print(f"Wrote {a.out}; NY trades={len(trades)}; background={len(background)}; splits={d1}/{d2}")

if __name__=="__main__": main()
