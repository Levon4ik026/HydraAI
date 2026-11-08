#!/usr/bin/env python3
"""Long-history, frozen-parameter validation of the M5 BB/Williams/ADX setup."""
from __future__ import annotations
import argparse, csv, math, statistics
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

from reproduce_m5_bb_williams_adx import Bar, make_m5, indicators, PAYOUT, wilson_interval

def read_duka(path: Path) -> list[Bar]:
    rows={}
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        reader=csv.DictReader(f)
        required={"timestamp","open","high","low","close"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Unexpected Dukascopy CSV header: {reader.fieldnames}")
        for r in reader:
            raw=int(float(r["timestamp"]))
            ts=datetime.fromtimestamp(raw/1000,tz=timezone.utc)
            vals=[float(r[k]) for k in ("open","high","low","close")]
            o,h,l,c=vals
            if not all(math.isfinite(x) and x>0 for x in vals) or h<max(o,l,c) or l>min(o,c):
                continue
            rows[ts]=Bar(ts,o,h,l,c)
    return [rows[t] for t in sorted(rows)]

def make_events(segments, adx_min=15):
    events=[]
    for seg_id,bars in enumerate(segments):
        ind=indicators(bars)
        for i in range(1,len(bars)-5):
            prev,cur=ind[i-1],ind[i]
            keys=("upper","lower","willr")
            if any(prev[k] is None or cur[k] is None for k in keys) or cur["adx"] is None:
                continue
            if cur["adx"]<adx_min: continue
            call=(bars[i-1].close<prev["lower"] and bars[i].close>cur["lower"]
                  and prev["willr"]<=-80 and cur["willr"]>-80)
            put=(bars[i-1].close>prev["upper"] and bars[i].close<cur["upper"]
                 and prev["willr"]>=-20 and cur["willr"]<-20)
            if call or put:
                events.append({"signal_time":bars[i].timestamp,"segment":seg_id,
                               "direction":"CALL" if call else "PUT","bar_index":i})
    return events

def outcome(bars, i, direction, horizon):
    entry=bars[i+1].open
    exitp=bars[i+horizon].close
    delta=(exitp-entry)*(1 if direction=="CALL" else -1)
    return "DRAW" if abs(delta)<1e-12 else "WIN" if delta>0 else "LOSS"

def stats(trades):
    w=sum(t=="WIN" for t in trades); l=sum(t=="LOSS" for t in trades); d=sum(t=="DRAW" for t in trades)
    dec=w+l; wr=100*w/dec if dec else float("nan")
    net=w*PAYOUT-l
    gross_win=w*PAYOUT; gross_loss=l
    pf=gross_win/gross_loss if gross_loss else (float("inf") if gross_win else 0)
    eq=peak=maxdd=0.0; streak=cur=0; maxstreak=0
    for t in trades:
        eq += PAYOUT if t=="WIN" else -1 if t=="LOSS" else 0
        peak=max(peak,eq); maxdd=max(maxdd,peak-eq)
        cur=cur+1 if t=="LOSS" else 0; maxstreak=max(maxstreak,cur)
    ci=wilson_interval(w,dec)
    return w,l,d,wr,net,pf,maxdd,maxstreak,ci

def fmt_stats(trades):
    w,l,d,wr,net,pf,dd,streak,ci=stats(trades)
    ci_txt=f"[{ci[0]:.1f}, {ci[1]:.1f}]" if ci else "n/a"
    return f"{len(trades)} | {w}/{l}/{d} | {wr:.2f}% | {ci_txt} | {net:+.2f}u | {pf:.2f} | {dd:.2f}u | {streak}"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--out",type=Path,default=Path("LONG_HISTORY_VALIDATION.md"))
    ap.add_argument("--adx-min",type=float,default=15)
    a=ap.parse_args()
    m1=read_duka(a.data); segments=make_m5(m1)
    events=make_events(segments,a.adx_min)
    days=sorted({e["signal_time"].date() for e in events})
    if len(days)<30: raise SystemExit("Insufficient history: fewer than 30 signal days.")
    d1=days[int(len(days)*0.60)]; d2=days[int(len(days)*0.80)]
    splits={"TRAIN":lambda d:d<d1,"VALIDATION":lambda d:d>=d1 and d<d2,"TEST":lambda d:d>=d2,"ALL":lambda d:True}
    by_h={}
    for h in (1,2,3,4,5):
        records=[]
        for e in events:
            seg=segments[e["segment"]]; i=e["bar_index"]
            if i+h>=len(seg): continue
            records.append({**e,"horizon":h,"outcome":outcome(seg,i,e["direction"],h)})
        by_h[h]=records
    lines=[
      "# HYDRA — long-history frozen strategy validation","",
      f"Source: Dukascopy EURUSD M1 BID; raw M1 rows={len(m1):,}; complete UTC M5 bars={sum(map(len,segments)):,}; continuous segments={len(segments)}.",
      f"Coverage: {m1[0].timestamp.isoformat()} — {m1[-1].timestamp.isoformat()}.",
      f"Frozen setup: Bollinger Bands(20,2) re-entry + Williams %R(14) cross; ADX(14) >= {a.adx_min:g}. Signal on closed M5; entry next M5 open.",
      "Expiries: 5/10/15/20/25 minutes; settlement at close of the 1st/2nd/3rd/4th/5th M5 candle after the signal, respectively (entry candle counts as candle 1).",
      "Payout accounting: WIN +0.92u, LOSS -1u, DRAW 0u. No parameter tuning or filters.",
      f"Chronological split by signal days: TRAIN before {d1}, VALIDATION {d1} through {d2-timedelta(days=1)}, TEST from {d2}.",
      "IMPORTANT: this is an external Dukascopy BID feed, not Pocket Option's exact quote stream; spread/platform quote differences are not modeled. Historical test is exploratory, not a live guarantee.","",
      "## Results by expiry and period","",
      "| Expiry | Period | n | W/L/D | Decisive WR | Wilson 95% CI | Net | PF | Max DD | Max loss streak |",
      "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for h,recs in by_h.items():
      for period,pred in splits.items():
        chosen=[r for r in recs if pred(r["signal_time"].date())]
        w,l,d,wr,net,pf,dd,streak,ci=stats([r["outcome"] for r in chosen])
        ci_txt=f"[{ci[0]:.1f}, {ci[1]:.1f}]" if ci else "n/a"
        lines.append(f"| {h*5}m | {period} | {len(chosen)} | {w}/{l}/{d} | {wr:.2f}% | {ci_txt} | {net:+.2f}u | {pf:.2f} | {dd:.2f}u | {streak} |")
    lines += ["","## Direction-separated TEST set","",
              "| Expiry | Direction | n | W/L/D | Decisive WR | Net |",
              "|---:|---|---:|---:|---:|---:|"]
    for h,recs in by_h.items():
      for side in ("CALL","PUT"):
        chosen=[r["outcome"] for r in recs if r["direction"]==side and splits["TEST"](r["signal_time"].date())]
        w,l,d,wr,net,*_=stats(chosen)
        lines.append(f"| {h*5}m | {side} | {len(chosen)} | {w}/{l}/{d} | {wr:.2f}% | {net:+.2f}u |")
    lines += ["","## Monthly 20-minute breakdown","",
              "| Month UTC | CALL W/L/D | CALL WR | PUT W/L/D | PUT WR | Combined net |",
              "|---|---:|---:|---:|---:|---:|"]
    recs=by_h[4]; months=sorted({r["signal_time"].strftime("%Y-%m") for r in recs})
    for month in months:
      monthrows=[r for r in recs if r["signal_time"].strftime("%Y-%m")==month]
      cells=[]
      for side in ("CALL","PUT"):
        x=[r["outcome"] for r in monthrows if r["direction"]==side]
        w,l,d,wr,net,*_=stats(x); cells.append((f"{w}/{l}/{d}",f"{wr:.1f}%"))
      net=sum(PAYOUT if r["outcome"]=="WIN" else -1 if r["outcome"]=="LOSS" else 0 for r in monthrows)
      lines.append(f"| {month} | {cells[0][0]} | {cells[0][1]} | {cells[1][0]} | {cells[1][1]} | {net:+.2f}u |")
    lines += ["","## Interpretation rules","",
      "- 92% payout requires 52.08% decisive win rate to break even; do not judge only by WR, also check net units and confidence intervals.",
      "- Treat TEST as the primary untouched chronological period; TRAIN/VALIDATION are diagnostic.",
      "- Expiry comparison reuses the same signal events, so differences are paired and should not be interpreted as independent samples.",
      "- No filter or parameter may be promoted based on this report alone; confirm on fresh Pocket Option candles.",""]
    a.out.parent.mkdir(parents=True,exist_ok=True); report="\n".join(lines); a.out.write_text(report+"\n",encoding="utf-8"); print(report)

if __name__=="__main__": main()
