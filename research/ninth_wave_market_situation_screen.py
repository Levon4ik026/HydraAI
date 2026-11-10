#!/usr/bin/env python3
"""Ninth-wave EURUSD M5 discovery: causal moving-average structure and RSI regime transitions.
Research only. Fixed rules, next-bar entry, exact-schedule direction inversion.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from pathlib import Path
from expanded_strategy_screen import read_m1, outcome, stats, ema, rsi
from long_history_validation import make_m5

HORIZONS=(1,2,3,4,6,12)
PAYOUT=0.92

def discover(bars):
    close=[b.close for b in bars]
    e20=ema(close,20); e50=ema(close,50); e100=ema(close,100); rv=rsi(close,14)
    events=defaultdict(list)
    for i in range(101,len(bars)-13):
        b,p=bars[i],bars[i-1]
        if None in (e20[i],e20[i-1],e50[i],e50[i-1],e100[i],rv[i],rv[i-1]): continue
        # Trend-aligned EMA20 pullback rejection: previous bar touches/crosses EMA20,
        # current closed bar reclaims it in the direction of EMA20/EMA50 trend.
        if e20[i]>e50[i]>e100[i] and p.low<=e20[i-1] and b.close>e20[i] and b.close>b.open:
            events["EMA20_BULL_TREND_PULLBACK_REJECTION_CALL"].append((i,"CALL"))
        if e20[i]<e50[i]<e100[i] and p.high>=e20[i-1] and b.close<e20[i] and b.close<b.open:
            events["EMA20_BEAR_TREND_PULLBACK_REJECTION_PUT"].append((i,"PUT"))
        # EMA50 reclaim after price spent the prior bar on the opposite side.
        if e50[i]>e100[i] and p.close<=e50[i-1] and b.close>e50[i] and b.close>b.open:
            events["EMA50_BULL_RECLAIM_CALL"].append((i,"CALL"))
        if e50[i]<e100[i] and p.close>=e50[i-1] and b.close<e50[i] and b.close<b.open:
            events["EMA50_BEAR_RECLAIM_PUT"].append((i,"PUT"))
        # Fresh EMA20/EMA50 cross, only evaluated on the completed signal candle.
        if e20[i-1]<=e50[i-1] and e20[i]>e50[i] and b.close>e20[i]:
            events["EMA20_50_BULL_CROSS_CALL"].append((i,"CALL"))
        if e20[i-1]>=e50[i-1] and e20[i]<e50[i] and b.close<e20[i]:
            events["EMA20_50_BEAR_CROSS_PUT"].append((i,"PUT"))
        # RSI(14) midpoint reclaim/cross, direction gated by EMA50 slope and price location.
        if rv[i-1]<=50<rv[i] and e50[i]>e50[i-3] and b.close>e50[i]:
            events["RSI50_BULL_RECLAIM_TREND_CALL"].append((i,"CALL"))
        if rv[i-1]>=50>rv[i] and e50[i]<e50[i-3] and b.close<e50[i]:
            events["RSI50_BEAR_RECLAIM_TREND_PUT"].append((i,"PUT"))
        # EMA20 slope turns with price confirmation, a distinct early trend-transition event.
        if e20[i-2]>=e20[i-1]<e20[i] and b.close>e20[i] and b.close>b.open:
            events["EMA20_SLOPE_TURN_UP_CALL"].append((i,"CALL"))
        if e20[i-2]<=e20[i-1]>e20[i] and b.close<e20[i] and b.close<b.open:
            events["EMA20_SLOPE_TURN_DOWN_PUT"].append((i,"PUT"))
    return events

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    m1=read_m1(a.data); segments=make_m5(m1)
    days=sorted({b.timestamp.date() for s in segments for b in s})
    if len(days)<30: raise SystemExit("Insufficient history")
    d1=days[int(.60*len(days))]; d2=days[int(.80*len(days))]
    results=defaultdict(list); raw=defaultdict(int); purged=0; family_names=set()
    for sid,bars in enumerate(segments):
        ev=discover(bars); family_names.update(ev)
        for name,items in ev.items():
            for h in HORIZONS:
                by_split={"TRAIN":[],"VALIDATION":[],"TEST":[]}
                for i,side in items:
                    if i+h>=len(bars): continue
                    day=bars[i].timestamp.date()
                    period="TRAIN" if day<d1 else "VALIDATION" if day<d2 else "TEST"
                    settle_day=bars[i+h].timestamp.date()
                    boundary=d1 if period=="TRAIN" else d2 if period=="VALIDATION" else None
                    if boundary and settle_day>=boundary:
                        purged+=1; continue
                    by_split[period].append((i,side))
                for period,rows in by_split.items():
                    raw[(name,h,period)]+=len(rows)
                    next_allowed=-1
                    for i,side in sorted(rows):
                        if i<next_allowed: continue
                        results[(name,h,period,"ORIGINAL")].append(outcome(bars,i,side,h))
                        inv="PUT" if side=="CALL" else "CALL"
                        results[(name,h,period,"INVERTED")].append(outcome(bars,i,inv,h))
                        next_allowed=i+h
    lines=[
      "# Ninth-wave EURUSD M5 discovery — moving-average structure and momentum transitions","",
      f"Source: Dukascopy EUR/USD M1 BID; valid M1 rows={len(m1):,}; M5 bars={sum(map(len,segments)):,}; gap-separated segments={len(segments)}.",
      f"Coverage: {m1[0].timestamp.isoformat()} — {m1[-1].timestamp.isoformat()}.",
      f"Chronological splits: TRAIN < {d1}; VALIDATION {d1}–{d2}; TEST >= {d2}; purged boundary-crossing outcomes={purged:,}.",
      "Predeclared causal families: EMA20 pullback rejection in EMA20/50/100 aligned trend (both directions); EMA50 reclaim with EMA100 trend alignment (both directions); EMA20/50 fresh cross; RSI14 midpoint cross with EMA50 slope/price alignment; EMA20 slope turn with close confirmation.",
      "All indicators use completed M5 candles only. Entry is next M5 open; expiry 5/10/15/20/30/60 minutes. One active position per family/expiry/segment/split. Original and inverse use identical events and schedule; only CALL/PUT flips.",
      "Payout assumption +0.92/-1/0; decisive break-even 52.083%. Dukascopy BID is not Pocket Option executable pricing. TEST has prior exploratory exposure; no result is confirmation. Multiple testing and serial dependence remain.","",
      "| Family | Variant | Expiry | Split | n | W/L/D | Decisive WR | Wilson 95% CI | Net u | Max DD u | Raw events |",
      "|---|---|---:|---|---:|---|---:|---|---:|---:|---:|"
    ]
    for (name,h,period,var),xs in sorted(results.items()):
        s=stats(xs); ci=s[5]
        wr="n/a" if s[4] is None else f"{s[4]:.2f}%"
        ci_txt="n/a" if ci is None else f"[{ci[0]:.2f},{ci[1]:.2f}]%"
        lines.append(f"| {name} | {var} | {h*5}m | {period} | {s[0]} | {s[1]}/{s[2]}/{s[3]} | {wr} | {ci_txt} | {s[6]:+.2f} | {s[7]:.2f} | {raw[(name,h,period)]} |")
    lines += ["","## Screening notes","",
      "- This wave expands the candidate library; it does not profile registered candidates by market regime.",
      "- A TEST-only high win rate is not eligible for promotion. Inspect exact-schedule inverse for weak originals.",
      "- Prefer validation evidence with meaningful sample and positive payout-adjusted net, while checking TRAIN and TEST consistency.",
      "- No threshold tuning is performed in this screen. Any follow-up context hypothesis must be frozen before a genuinely untouched forward sample.",""]
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text("\n".join(lines),encoding="utf-8")
    print(f"Ninth-wave complete: M1={len(m1):,}; M5={sum(map(len,segments)):,}; families={len(family_names)}; rows={len(results)}; report={a.out}")

if __name__=="__main__": main()
