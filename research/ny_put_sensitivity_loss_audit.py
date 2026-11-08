#!/usr/bin/env python3
"""Predeclared one-at-a-time sensitivity and loss anatomy for locked NY PUT candidate.
No parameter selection or production changes. Dukascopy BID proxy only.
"""
from __future__ import annotations
import argparse, math
from collections import defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo
from long_history_validation import read_duka, make_events, m5_close_time
from reproduce_m5_bb_williams_adx import make_m5, indicators

NY = ZoneInfo("America/New_York")
H = 4
PAY = .92

def outcome(bars, i):
    d = bars[i+H].close - bars[i+1].open
    return "DRAW" if abs(d) < 1e-12 else ("WIN" if d < 0 else "LOSS")

def period(ts, end, d1, d2):
    if ts.date() < d1: return None if end.date() >= d1 else "TRAIN"
    if ts.date() < d2: return None if end.date() >= d2 else "VALIDATION"
    return "TEST"

def stats(rows):
    w=sum(r["outcome"]=="WIN" for r in rows); l=sum(r["outcome"]=="LOSS" for r in rows)
    d=sum(r["outcome"]=="DRAW" for r in rows); n=w+l+d
    return n,w,l,d,(100*w/(w+l) if w+l else float("nan")),w*PAY-l

def nonoverlap(rows):
    out=[]
    by=defaultdict(list)
    for r in rows: by[r["sid"]].append(r)
    for sid,rs in by.items():
        allowed=-1
        for r in sorted(rs,key=lambda x:x["i"]):
            if r["i"]>=allowed:
                out.append(r); allowed=r["i"]+H
    return out

def fmt(label, rows):
    n,w,l,d,wr,net=stats(rows)
    return f"| {label} | {n} | {w}/{l}/{d} | {wr:.2f}% | {net:+.2f}u |"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--out",type=Path,default=Path("research/NY_PUT_SENSITIVITY_LOSS_AUDIT.md"))
    a=ap.parse_args()
    m1=read_duka(a.data); segs=make_m5(m1); ev=make_events(segs,15)
    em={(e["segment"],e["bar_index"]):e for e in ev}
    days=sorted({e["signal_time"].date() for e in ev})
    d1,d2=days[int(.60*len(days))],days[int(.80*len(days))]
    rows=[]
    for sid,bars in enumerate(segs):
        ind=indicators(bars)
        for i in range(50,len(bars)-H):
            ts=bars[i].timestamp; loc=ts.astimezone(NY)
            if not 8<=loc.hour<13: continue
            e=em.get((sid,i))
            if not e or e["direction"]!="PUT": continue
            end=m5_close_time(bars[i+H].timestamp); sp=period(ts,end,d1,d2)
            if sp is None: continue
            x=ind[i]
            if x["adx"] is None or x["plus_di"] is None or x["minus_di"] is None: continue
            mom12=bars[i].close-bars[i-12].close
            mom6=bars[i].close-bars[i-6].close
            mom18=bars[i].close-bars[i-18].close
            rows.append({"sid":sid,"i":i,"period":sp,"outcome":outcome(bars,i),
              "adx":x["adx"],"di":x["plus_di"]-x["minus_di"],
              "mom6":mom6,"mom12":mom12,"mom18":mom18,
              "body":abs(bars[i].close-bars[i].open),
              "range":max(1e-12,bars[i].high-bars[i].low),
              "close_pos":(bars[i].close-bars[i].low)/max(1e-12,bars[i].high-bars[i].low)})
    base=[r for r in rows if r["adx"]>=25 and r["di"]>0 and r["mom12"]>0]
    base=nonoverlap(base)
    variants=[
      ("ADX >=20",lambda r:r["adx"]>=20 and r["di"]>0 and r["mom12"]>0),
      ("ADX >=25 (locked)",lambda r:r["adx"]>=25 and r["di"]>0 and r["mom12"]>0),
      ("ADX >=30",lambda r:r["adx"]>=30 and r["di"]>0 and r["mom12"]>0),
      ("Momentum 6 bars >0",lambda r:r["adx"]>=25 and r["di"]>0 and r["mom6"]>0),
      ("Momentum 12 bars >0 (locked)",lambda r:r["adx"]>=25 and r["di"]>0 and r["mom12"]>0),
      ("Momentum 18 bars >0",lambda r:r["adx"]>=25 and r["di"]>0 and r["mom18"]>0),
      ("DI spread >0 (locked)",lambda r:r["adx"]>=25 and r["di"]>0 and r["mom12"]>0),
      ("DI spread >2",lambda r:r["adx"]>=25 and r["di"]>2 and r["mom12"]>0),
    ]
    lines=["# HYDRA — NY PUT one-at-a-time sensitivity & loss anatomy","",
      f"Data: Dukascopy EURUSD M1 BID; rows={len(m1):,}; M5 bars={sum(map(len,segs)):,}; segments={len(segs):,}.",
      f"Coverage: {m1[0].timestamp.isoformat()} — {m1[-1].timestamp.isoformat()}.",
      f"Split: TRAIN < {d1}; VALIDATION < {d2}; TEST >= {d2}.",
      "Base event: frozen strategy PUT signal, New York 08:00–12:59 local, ADX>=25, +DI>-DI, positive 12-bar close momentum. Entry next M5 open; exit fourth following M5 close; payout 92%.",
      "All variants are one-at-a-time diagnostics; no thresholds are selected from TEST. Candidate signals are non-overlapping. This is retrospective and not independent confirmation.","",
      "## Fixed sensitivity grid (one change at a time)","","| Variant | n | W/L/D | WR | Net @92% |","|---|---:|---:|---:|---:|"]
    for name,fn in variants:
        for split in ("TRAIN","VALIDATION","TEST","ALL"):
            rs=nonoverlap([r for r in rows if fn(r) and (split=="ALL" or r["period"]==split)])
            lines.append(fmt(f"{name} — {split}",rs))
    lines += ["","## Locked candidate loss anatomy (non-overlapping signals)","","| Period | n | W/L/D | WR | Net @92% |","|---|---:|---:|---:|---:|"]
    for p in ("TRAIN","VALIDATION","TEST","ALL"):
        rs=[r for r in base if p=="ALL" or r["period"]==p]
        lines.append(fmt(p,rs))
    lines += ["","### ADX at signal (descriptive bins)","","| Period / ADX | n | W/L/D | WR | Net @92% |","|---|---:|---:|---:|---:|"]
    for p in ("TRAIN","VALIDATION","TEST","ALL"):
      for label,lo,hi in (("25–30",25,30),("30–35",30,35),("35+",35,float("inf"))):
        rs=[r for r in base if (p=="ALL" or r["period"]==p) and lo<=r["adx"]<hi]
        lines.append(fmt(f"{p} / {label}",rs))
    lines += ["","### DI spread at signal (descriptive bins)","","| Period / +DI−−DI | n | W/L/D | WR | Net @92% |","|---|---:|---:|---:|---:|"]
    for p in ("TRAIN","VALIDATION","TEST","ALL"):
      for label,lo,hi in (("0–5",0,5),("5–10",5,10),("10+",10,float("inf"))):
        rs=[r for r in base if (p=="ALL" or r["period"]==p) and lo<=r["di"]<hi]
        lines.append(fmt(f"{p} / {label}",rs))
    lines += ["","### Signal candle close location (descriptive bins)","","| Period / close location | n | W/L/D | WR | Net @92% |","|---|---:|---:|---:|---:|"]
    for p in ("TRAIN","VALIDATION","TEST","ALL"):
      for label,lo,hi in (("lower third",0,1/3),("middle third",1/3,2/3),("upper third",2/3,1.000001)):
        rs=[r for r in base if (p=="ALL" or r["period"]==p) and lo<=r["close_pos"]<hi]
        lines.append(fmt(f"{p} / {label}",rs))
    lines += ["","## Guardrails","","- Small bins are descriptive only; do not use them as new filters.",
      "- The candidate was discovered in prior exploratory analysis; this is not a pristine holdout.",
      "- Multiple variants are reported without selecting a winner. TEST must not be used to retune thresholds.",
      "- Dukascopy BID differs from Pocket Option quotes; no orders were executed and no production/local files were changed.",""]
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text("\n".join(lines),encoding="utf-8")
    print(f"base_nonoverlap={len(base)}; all_candidate_rows={len(rows)}; wrote {a.out}")

if __name__=="__main__": main()
