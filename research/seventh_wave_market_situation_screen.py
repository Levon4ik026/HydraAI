#!/usr/bin/env python3
"""Seventh-wave EURUSD M5 market-situation discovery. Research only."""
from __future__ import annotations
import argparse, statistics
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from expanded_strategy_screen import read_m1, outcome, stats
from long_history_validation import make_m5

HORIZONS=(1,2,3,4,6,12)  # 5–60 minutes
SESSION_HOURS=(0,6,12,18)

def session_key(ts):
    return (ts.date(), ts.hour//6)

def events_for_segment(bars):
    ev=defaultdict(list)
    # Opening range: first six completed M5 bars in each fixed UTC six-hour block.
    groups=defaultdict(list)
    for i,b in enumerate(bars):
        groups[session_key(b.timestamp)].append(i)
    for _,idx in groups.items():
        if len(idx)<8: continue
        opening=idx[:6]
        rh=max(bars[j].high for j in opening)
        rl=min(bars[j].low for j in opening)
        for i in idx[6:]:
            b=bars[i]; p=bars[i-1]
            if p.close<=rh and b.close>rh:
                ev["OPENING_RANGE_BREAKOUT_CALL"].append((i,"CALL"))
            if p.close>=rl and b.close<rl:
                ev["OPENING_RANGE_BREAKOUT_PUT"].append((i,"PUT"))
            # Wick breaches opening range but closes back inside it.
            if b.high>rh and b.close<rh and b.close<b.open:
                ev["OPENING_RANGE_FALSE_BREAK_PUT"].append((i,"PUT"))
            if b.low<rl and b.close>rl and b.close>b.open:
                ev["OPENING_RANGE_FALSE_BREAK_CALL"].append((i,"CALL"))
    ranges=[b.high-b.low for b in bars]
    tr=[]
    for i,b in enumerate(bars):
        tr.append(b.high-b.low if i==0 else max(b.high-b.low,abs(b.high-bars[i-1].close),abs(b.low-bars[i-1].close)))
    # Causal volatility shock and compression-breakout definitions.
    for i in range(30,len(bars)-13):
        b=bars[i]; p=bars[i-1]
        prior=tr[i-20:i]
        med=statistics.median(prior) if prior else 0
        if med>0 and tr[i]>=2.0*med:
            if b.close>b.open and (b.high-b.close)<=0.25*max(b.high-b.low,1e-12):
                ev["VOL_SHOCK_UP_CLOSE_HIGH_CALL"].append((i,"CALL"))
            if b.close<b.open and (b.close-b.low)<=0.25*max(b.high-b.low,1e-12):
                ev["VOL_SHOCK_DOWN_CLOSE_LOW_PUT"].append((i,"PUT"))
        # Six-bar compression compared with median range of preceding 24 bars.
        comp=max(bars[j].high for j in range(i-6,i))-min(bars[j].low for j in range(i-6,i))
        base=statistics.median(ranges[i-30:i-6])
        if base>0 and comp<=6.0*base:
            ch=max(bars[j].high for j in range(i-6,i))
            cl=min(bars[j].low for j in range(i-6,i))
            if p.close<=ch and b.close>ch:
                ev["SIX_BAR_COMPRESSION_BREAK_CALL"].append((i,"CALL"))
            if p.close>=cl and b.close<cl:
                ev["SIX_BAR_COMPRESSION_BREAK_PUT"].append((i,"PUT"))
        # Four consecutive directional closes, then either fifth-bar reversal or continuation.
        last4=bars[i-4:i]
        up=all(x.close>x.open for x in last4)
        down=all(x.close<x.open for x in last4)
        if up and b.close<b.open:
            ev["FOUR_UP_THEN_REVERSAL_PUT"].append((i,"PUT"))
        if down and b.close>b.open:
            ev["FOUR_DOWN_THEN_REVERSAL_CALL"].append((i,"CALL"))
        if up and b.close>b.open:
            ev["FOUR_UP_THEN_CONTINUATION_CALL"].append((i,"CALL"))
        if down and b.close<b.open:
            ev["FOUR_DOWN_THEN_CONTINUATION_PUT"].append((i,"PUT"))
    return ev

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True); ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    m1=read_m1(a.data); segments=make_m5(m1)
    if len(m1)<100000 or len(segments)<2: raise SystemExit("Insufficient/fragmented history")
    days=sorted({b.timestamp.date() for seg in segments for b in seg})
    d1=days[int(.60*len(days))]; d2=days[int(.80*len(days))]
    accepted=defaultdict(list); raw=defaultdict(int); families=set()
    for sid,bars in enumerate(segments):
        ev=events_for_segment(bars); families.update(ev)
        for name,items in ev.items():
            for h in HORIZONS:
                rows=[]
                for i,side in items:
                    if i+h>=len(bars): continue
                    day=bars[i].timestamp.date(); settle=bars[i+h].timestamp.date()
                    period="TRAIN" if day<d1 else "VALIDATION" if day<d2 else "TEST"
                    if (period=="TRAIN" and settle>=d1) or (period=="VALIDATION" and settle>=d2): continue
                    rows.append((i,side,period))
                raw[(name,h)]+=len(rows)
                for period in ("TRAIN","VALIDATION","TEST"):
                    nxt=-1
                    for i,side,p in sorted((r for r in rows if r[2]==period),key=lambda z:z[0]):
                        if i<nxt: continue
                        accepted[(name,h,period,"ORIGINAL")].append(outcome(bars,i,side,h))
                        accepted[(name,h,period,"INVERTED")].append(outcome(bars,i,"PUT" if side=="CALL" else "CALL",h))
                        nxt=i+h
    lines=[
      "# Seventh-wave EURUSD M5 market-situation discovery","",
      f"Source: Dukascopy EURUSD M1 BID; M1 rows={len(m1):,}; M5 bars={sum(map(len,segments)):,}; gap-separated segments={len(segments)}.",
      f"Coverage: {m1[0].timestamp.isoformat()} — {m1[-1].timestamp.isoformat()}.",
      f"Chronological UTC-date split: TRAIN < {d1}; VALIDATION {d1}–{d2}; TEST >= {d2}; boundary-crossing outcomes purged.",
      "Predeclared event families: six-bar UTC session opening-range breakout and false-break reclaim; causal 2x-median true-range shock with close near candle extreme; six-bar compression breakout; four-candle directional run followed by reversal or continuation.",
      "Opening range uses only the first six completed M5 candles of each fixed UTC six-hour block. Compression and shock thresholds are fixed and use only prior completed bars. No session filter is selected from TEST.",
      "Entry next M5 open; expiry close of Nth subsequent M5 candle; horizons 5/10/15/20/30/60m. One active event per family/expiry/segment/split.",
      "Original and inverse share exact event timestamps, entries, expiry and non-overlap schedule; only CALL/PUT flips. Assumed payout 92% (+0.92/-1/0); break-even decisive WR 52.083%.",
      "Dukascopy BID is not Pocket Option executable pricing. No spread, latency, variable payout or platform quote is modeled. Broad discovery is exploratory; Wilson intervals do not correct serial dependence or multiple testing.","",
      "| Family | Variant | Expiry | Split | n | W/L/D | Decisive WR | Wilson 95% CI | Net u | Max DD u | Max loss streak | Raw events |",
      "|---|---|---:|---|---:|---|---:|---|---:|---:|---:|---:|"
    ]
    for (name,h,period,variant),xs in sorted(accepted.items()):
        s=stats(xs); ci=s[5]
        wr="n/a" if s[4] is None else f"{s[4]:.2f}%"
        ci_txt="n/a" if ci is None else f"[{ci[0]:.2f},{ci[1]:.2f}]%"
        lines.append(f"| {name} | {variant} | {h*5}m | {period} | {s[0]} | {s[1]}/{s[2]}/{s[3]} | {wr} | {ci_txt} | {s[6]:+.2f} | {s[7]:.2f} | {s[8]} | {raw[(name,h)]} |")
    lines += ["","## Screen interpretation","",
      "- Discovery priority: VALIDATION decisive WR >=57%, adequate sample, positive assumed-payout net; 56.0–56.9% is borderline.",
      "- A strong TEST-only result is not a candidate promotion. Inversion is a separate hypothesis on the exact same event set.",
      "- No strategy is confirmed by this screen. Do not tune against VALIDATION/TEST after inspecting this report.",
      "- Candidate discovery remains the priority; detailed market-state profiling comes only after a broader candidate pool is assembled.",
      "- Independent/prospective quote-level validation is still required.",""]
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text("\n".join(lines),encoding="utf-8")
    print(f"Seventh-wave complete: M1={len(m1):,}; M5={sum(map(len,segments)):,}; families={len(families)}; report={a.out}")

if __name__=="__main__": main()
