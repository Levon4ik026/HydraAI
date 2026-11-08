#!/usr/bin/env python3
"""Causal time-of-day and round-number context audit for frozen HYDRA signals.

All context variables are known at signal close. Fixed bins are predeclared;
this script is descriptive and does not select or optimize a trading filter.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from long_history_validation import read_duka, make_events, PAYOUT, m5_close_time
from reproduce_m5_bb_williams_adx import make_m5

WARMUP = 50
HORIZON = 4
PIP = 0.0001
BIG_FIGURE = 0.0050
WHOLE_FIGURE = 0.0100

def result_stats(rows):
    w=sum(r["outcome"]=="WIN" for r in rows)
    l=sum(r["outcome"]=="LOSS" for r in rows)
    d=sum(r["outcome"]=="DRAW" for r in rows)
    dec=w+l
    wr=100*w/dec if dec else float("nan")
    net=w*PAYOUT-l
    pf=(w*PAYOUT/l) if l else (float("inf") if w else 0.0)
    return len(rows),w,l,d,wr,net,pf

def rowline(label, rows):
    n,w,l,d,wr,net,pf=result_stats(rows)
    return f"| {label} | {n} | {w}/{l}/{d} | {wr:.2f}% | {net:+.2f}u | {pf:.2f} |"

def group_table(lines, title, rows, key):
    lines += [f"## {title}", "", "| Group | n | W/L/D | Decisive WR | Net | PF |", "|---|---:|---:|---:|---:|---:|"]
    for label in key:
        subset=[r for r in rows if r[key_name]==label] if False else []
    return lines

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--out",type=Path,default=Path("research/TIME_ROUND_LEVEL_AUDIT.md"))
    args=ap.parse_args()

    m1=read_duka(args.data)
    segments=make_m5(m1)
    events=make_events(segments,15)
    days=sorted({e["signal_time"].date() for e in events})
    if len(days)<30:
        raise SystemExit("Insufficient history")
    d1,d2=days[int(len(days)*.60)],days[int(len(days)*.80)]
    rows=[]
    excluded=0
    for e in events:
        bars=segments[e["segment"]]
        i=e["bar_index"]
        if i<WARMUP or i+HORIZON>=len(bars):
            excluded+=1
            continue
        sig=bars[i]
        entry=bars[i+1].open
        exitp=bars[i+HORIZON].close
        signed=1 if e["direction"]=="CALL" else -1
        delta=signed*(exitp-entry)
        outcome="DRAW" if abs(delta)<1e-12 else "WIN" if delta>0 else "LOSS"
        ts=sig.timestamp
        london=ts.astimezone(ZoneInfo("Europe/London"))
                tokyo=ts.astimezone(ZoneInfo("Asia/Tokyo"))
        utc_hour=ts.hour
        session=("Asia" if 0<=utc_hour<7 else "London" if 7<=utc_hour<13 else "New York" if 13<=utc_hour<18 else "Late")
        big_dist=abs(sig.close-round(sig.close/BIG_FIGURE)*BIG_FIGURE)/PIP
        whole_dist=abs(sig.close-round(sig.close/WHOLE_FIGURE)*WHOLE_FIGURE)/PIP
        def dist_bin(d):
            return "<=2p" if d<=2 else "2-5p" if d<=5 else "5-10p" if d<=10 else ">10p"
        # Local-clock windows are DST-aware; these are descriptive windows around
        # commonly watched fixing times, not claims about exact order-flow timing.
        fix_tokyo=9*60+55
        fix_frankfurt=14*60+15
        fix_london=16*60
        mins_tokyo=tokyo.hour*60+tokyo.minute
        mins_frankfurt=ts.astimezone(ZoneInfo("Europe/Berlin")).hour*60+ts.astimezone(ZoneInfo("Europe/Frankfurt")).minute
        mins_london=london.hour*60+london.minute
        def near(a,b): return abs(a-b)<=10
        period="TRAIN" if ts.date()<d1 else "VALIDATION" if ts.date()<d2 else "TEST"
        rows.append({
            "period":period,"side":e["direction"],"outcome":outcome,
            "utc_hour":f"{utc_hour:02d}:00-{utc_hour:02d}:59",
            "session":session,
            "big_bin":dist_bin(big_dist),"whole_bin":dist_bin(whole_dist),
            "near_big_2p":big_dist<=2,
            "near_tokyo_fix":near(mins_tokyo,fix_tokyo),
            "near_frankfurt_fix":near(mins_frankfurt,fix_frankfurt),
            "near_london_fix":near(mins_london,fix_london),
        })

    lines=[
      "# HYDRA — time-of-day and round-number context audit","",
      f"Source: Dukascopy EURUSD M1 BID; M1 rows={len(m1):,}; complete M5={sum(map(len,segments)):,}; segments={len(segments)}.",
      f"Coverage: {m1[0].timestamp.isoformat()} — {m1[-1].timestamp.isoformat()}.",
      f"Events from frozen BB(20,2) re-entry + Williams %R(14) cross + ADX>=15; eligible rows={len(rows):,}; excluded warmup/path rows={excluded:,}.",
      f"Entry next M5 open; settlement fourth M5 close (20m); payout +{PAYOUT:.2f}/-1/0.",
      f"Chronological signal-day boundaries: TRAIN < {d1}; VALIDATION < {d2}; TEST >= {d2}.",
      "All context is computed at signal close or earlier. Bins are fixed in advance, no threshold optimization. Results are exploratory; multiple comparisons, overlapping trades, serial dependence, and external BID-vs-platform differences remain.",
      "UTC session labels are coarse: Asia 00-06, London 07-12, New York 13-17, Late 18-23. Local fixing windows use DST-aware Tokyo 09:55, Frankfurt/ECB 14:15, London 16:00, +/-10 minutes; these are context windows, not proof of fixing-driven flow.","",
      "## Overall baseline by period","",
      "| Period | n | W/L/D | Decisive WR | Net | PF |","|---|---:|---:|---:|---:|---:|"
    ]
    for p in ("TRAIN","VALIDATION","TEST"):
        lines.append(rowline(p,[r for r in rows if r["period"]==p]))
    for dimension, labels in [
        ("session",["Asia","London","New York","Late"]),
        ("utc_hour",[f"{h:02d}:00-{h:02d}:59" for h in range(24)]),
        ("big_bin",["<=2p","2-5p","5-10p",">10p"]),
        ("whole_bin",["<=2p","2-5p","5-10p",">10p"]),
        ("near_tokyo_fix",[True,False]),
        ("near_frankfurt_fix",[True,False]),
        ("near_london_fix",[True,False]),
        ("near_big_2p",[True,False]),
    ]:
        lines += ["",f"## {dimension.replace('_',' ').title()} — all periods","",
          "| Group | n | W/L/D | Decisive WR | Net | PF |","|---|---:|---:|---:|---:|---:|"]
        for label in labels:
            subset=[r for r in rows if r[dimension]==label]
            lines.append(rowline(str(label),subset))
    for period in ("TRAIN","VALIDATION","TEST"):
        lines += ["",f"## Side and context by {period}","",
          "| Context | Side | n | W/L/D | Decisive WR | Net | PF |","|---|---|---:|---:|---:|---:|---:|"]
        sub=[r for r in rows if r["period"]==period]
        for dim,labels in [("session",["Asia","London","New York","Late"]),
                           ("big_bin",["<=2p","2-5p","5-10p",">10p"]),
                           ("near_tokyo_fix",[True,False]),
                           ("near_frankfurt_fix",[True,False]),
                           ("near_london_fix",[True,False])]:
            for label in labels:
                for side in ("CALL","PUT"):
                    grp=[r for r in sub if r[dim]==label and r["side"]==side]
                    n,w,l,d,wr,net,pf=result_stats(grp)
                    lines.append(f"| {dim}={label} | {side} | {n} | {w}/{l}/{d} | {wr:.2f}% | {net:+.2f}u | {pf:.2f} |")
    lines += ["","## Interpretation rules","",
      "- Do not select the best-looking hour, session, fixing window, or round-level distance from this report and deploy it. That would be multiple-testing/data-mining.",
      "- A context hypothesis is interesting only if the direction and economically meaningful lift are present in TRAIN and VALIDATION, with adequate counts, and then survives a newly collected untouched forward sample.",
      "- Time-of-day may proxy volatility, liquidity, scheduled news, and session overlap; this audit does not isolate causal mechanisms.",
      "- Round-number proximity uses signal close to nearest 0.0050 (50-pip big figure) and 0.0100 (100-pip whole figure). It does not observe actual order books or stop orders.",
      "- No local desktop files changed; no filter integrated; no trades executed.",""]
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text("\n".join(lines),encoding="utf-8")
    print(f"Wrote {args.out}; eligible={len(rows)}; excluded={excluded}; split={d1}/{d2}")

if __name__=="__main__":
    main()
