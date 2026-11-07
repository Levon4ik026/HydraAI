#!/usr/bin/env python3
"""Long-horizon audit of the frozen M5 BB/Williams/ADX signal on existing candles.

Entry: next M5 open after the closed signal candle.
Settlement: close of the H-th M5 candle after signal (H=1,2,3,5).
No gap crossing. No parameter optimization. Research only.
"""
from __future__ import annotations
import argparse, random, statistics
from collections import defaultdict
from pathlib import Path
from datetime import timedelta

try:
    from .reproduce_m5_bb_williams_adx import load_m1, make_m5, build_signals, PAYOUT, SPLIT_DATE
except ImportError:
    from reproduce_m5_bb_williams_adx import load_m1, make_m5, build_signals, PAYOUT
    SPLIT_DATE = "2026-10-21T19:05:00+00:00"

HORIZONS = (1, 2, 3, 5)

def wilson(w, n):
    if not n: return (float("nan"), float("nan"))
    z=1.959963984540054; p=w/n; d=1+z*z/n
    c=(p+z*z/(2*n))/d
    m=z*((p*(1-p)/n+z*z/(4*n*n))**0.5)/d
    return c-m,c+m

def stats(items):
    w=sum(x["outcome"]=="WIN" for x in items)
    l=sum(x["outcome"]=="LOSS" for x in items)
    d=sum(x["outcome"]=="DRAW" for x in items)
    n=w+l; net=.92*w-l
    lo,hi=wilson(w,n)
    return f"n={len(items)} W/L/D={w}/{l}/{d} WR={w/n*100:.1f}%" if n else f"n={len(items)} W/L/D={w}/{l}/{d} WR=NA", net, (lo*100,hi*100)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,default=Path("eurusd_history_extended.csv"))
    ap.add_argument("--out",type=Path,default=Path("research/LONG_HORIZON_AUDIT.md"))
    args=ap.parse_args()
    m1=load_m1(args.data); segments=make_m5(m1)
    rows=build_signals(segments)
    alltr=[]
    for i,row in enumerate(rows):
        if not row["signal"] or row["adx"] is None or row["adx"]<15: continue
        for h in HORIZONS:
            j=i+h
            if j>=len(rows): continue
            path=rows[i:j+1]
            if any(x["segment_id"]!=row["segment_id"] for x in path): continue
            if any(path[k+1]["bar"].timestamp-path[k]["bar"].timestamp!=timedelta(minutes=5) for k in range(len(path)-1)): continue
            entry=rows[i+1]["bar"].open
            exitp=rows[j]["bar"].close
            delta=exitp-entry
            outcome="DRAW" if abs(delta)<1e-12 else ("WIN" if (delta>0)==(row["signal"]==1) else "LOSS")
            alltr.append({"h":h,"direction":"CALL" if row["signal"]==1 else "PUT",
                "outcome":outcome,"net":0 if outcome=="DRAW" else (.92 if outcome=="WIN" else -1),
                "time":row["bar"].timestamp,"hour":row["bar"].timestamp.hour,
                "period":"PRE_SPLIT" if row["bar"].timestamp.isoformat()<"2026-10-21T19:05:00+00:00" else "POST_SPLIT"})
    lines=["# HYDRA — Long-horizon audit of frozen M5 signal","",
      "Research only. Frozen BB(20,2) re-entry + Williams %R(14) cross + ADX>=15. ",
      "Entry is next M5 open; settlement is H-th subsequent M5 close. Payout fixed at 92%.",
      "No gap crossing. No thresholds tuned. Historical post-split data has already been inspected; it is not pristine validation.","",
      f"- M1 source rows: {len(m1):,}",
      f"- Complete M5 segments: {len(segments)}",
      f"- Complete M5 bars: {sum(map(len,segments)):,}",
      f"- M1 coverage: {m1[0].timestamp.isoformat()} to {m1[-1].timestamp.isoformat()}",
      f"- Eligible signal/horizon observations: {len(alltr):,} (same signals reused across horizons; not independent samples)",""]
    for h in HORIZONS:
        sub=[x for x in alltr if x["h"]==h]
        lines += [f"## Expiry: {h*5} minutes", "| Side | Sample and decisive WR | Net units | Wilson 95% CI |","|---|---:|---:|---:|"]
        for side in ("CALL","PUT","ALL"):
            s=[x for x in sub if side=="ALL" or x["direction"]==side]
            label,net,ci=stats(s)
            lines.append(f"| {side} | {label} | {net:+.2f} | {ci[0]:.1f}%–{ci[1]:.1f}% |")
        lines.append("")
        for period in ("PRE_SPLIT","POST_SPLIT"):
            for side in ("CALL","PUT"):
                s=[x for x in sub if x["period"]==period and x["direction"]==side]
                label,net,ci=stats(s)
                lines.append(f"- {period} {side}: {label}; net {net:+.2f}u; CI {ci[0]:.1f}–{ci[1]:.1f}%.")
        lines.append("")
    lines += ["## UTC session buckets (all horizons separately)", "These are descriptive only; small buckets and repeated signal events mean they are not independent tests.",""]
    for h in HORIZONS:
        lines.append(f"### {h*5}-minute expiry")
        lines.append("| UTC hour | Side | n | W/L/D | WR | Net |")
        lines.append("|---:|---|---:|---:|---:|---:|")
        for hour in range(24):
            for side in ("CALL","PUT"):
                s=[x for x in alltr if x["h"]==h and x["hour"]==hour and x["direction"]==side]
                if not s: continue
                w=sum(x["outcome"]=="WIN" for x in s); l=sum(x["outcome"]=="LOSS" for x in s); d=len(s)-w-l
                lines.append(f"| {hour:02d} | {side} | {len(s)} | {w}/{l}/{d} | {100*w/(w+l):.1f}% | {sum(x['net'] for x in s):+.2f} |" if w+l else f"| {hour:02d} | {side} | {len(s)} | {w}/{l}/{d} | NA | 0 |")
        lines.append("")
    lines += ["## Interpretation guardrails",
      "- A higher expiry is a different strategy outcome, not a free improvement; compare all horizons on identical eligible signals.",
      "- Repeated horizons share the same underlying signal events. Do not treat them as independent evidence.",
      "- Hour buckets are exploratory and vulnerable to multiple-testing and small-sample noise.",
      "- Net units assume every signal is taken, fixed 92% payout, and no transaction/latency/slippage effects.",
      "- No filter or expiry is promoted by this report. A prospective test on fresh candles is still required."]
    args.out.parent.mkdir(parents=True,exist_ok=True); args.out.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(f"Wrote {args.out}; M1={len(m1)} M5={sum(map(len,segments))} signals={len({(x['time'],x['direction']) for x in alltr})} rows={len(alltr)}")
if __name__=="__main__": main()
