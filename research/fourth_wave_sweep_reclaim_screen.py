#!/usr/bin/env python3
"""Fourth-wave prior-period liquidity sweep/reclaim discovery. Research only."""
from __future__ import annotations
import argparse
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from expanded_strategy_screen import read_m1, outcome, stats
from long_history_validation import make_m5

HORIZONS=(1,2,3,4,6,12)

def prior_levels(segments):
    """Map each bar to prior observed UTC trading-day and prior completed UTC-week levels."""
    out=[]
    for bars in segments:
        daymap=defaultdict(list); weekmap=defaultdict(list)
        for b in bars:
            daymap[b.timestamp.date()].append(b)
            iso=b.timestamp.isocalendar()
            weekmap[(iso.year,iso.week)].append(b)
        dates=sorted(daymap)
        weeks=sorted(weekmap)
        day_prev={}
        for j,d in enumerate(dates):
            if j:
                prev=daymap[dates[j-1]]
                day_prev[d]=(max(x.high for x in prev),min(x.low for x in prev),dates[j-1])
        week_prev={}
        for j,w in enumerate(weeks):
            if j:
                prev=weekmap[weeks[j-1]]
                week_prev[w]=(max(x.high for x in prev),min(x.low for x in prev),weeks[j-1])
        levels=[]
        for b in bars:
            d=b.timestamp.date(); iso=b.timestamp.isocalendar(); wk=(iso.year,iso.week)
            levels.append((day_prev.get(d),week_prev.get(wk)))
        out.append(levels)
    return out

def events_for(segments):
    ev=defaultdict(list)
    all_levels=prior_levels(segments)
    for sid,bars in enumerate(segments):
        levels=all_levels[sid]
        for i in range(60,len(bars)-13):
            day,week=levels[i]
            if bars[i].close==bars[i].open:
                continue
            for label,lv in (("PREV_DAY",day),("PREV_WEEK",week)):
                if lv is None: continue
                top,bottom,_=lv
                b=bars[i]
                # Sweep above a completed prior-period high and close back below it.
                if b.high>top and b.close<top and b.close<b.open:
                    ev[f"{label}_HIGH_SWEEP_RECLAIM_PUT"].append((sid,i,"PUT"))
                # Sweep below a completed prior-period low and close back above it.
                if b.low<bottom and b.close>bottom and b.close>b.open:
                    ev[f"{label}_LOW_SWEEP_RECLAIM_CALL"].append((sid,i,"CALL"))
    return ev

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    m1=read_m1(a.data); segments=make_m5(m1)
    if len(m1)<100000 or len(segments)<2:
        raise SystemExit("Insufficient or unexpectedly fragmented history")
    observed_days=sorted({b.timestamp.date() for seg in segments for b in seg})
    d1=observed_days[int(.60*len(observed_days))]
    d2=observed_days[int(.80*len(observed_days))]
    events=events_for(segments)
    raw=defaultdict(list)
    for name,items in events.items():
        for sid,i,side in items:
            bars=segments[sid]
            for h in HORIZONS:
                if i+h>=len(bars): continue
                signal_time=bars[i].timestamp
                settle_time=bars[i+h].timestamp+timedelta(minutes=5)
                sd=signal_time.date(); ed=settle_time.date()
                period="TRAIN" if sd<d1 else "VALIDATION" if sd<d2 else "TEST"
                if (period=="TRAIN" and ed>=d1) or (period=="VALIDATION" and ed>=d2):
                    continue
                raw[(name,h,period,sid)].append((i,side,outcome(bars,i,side,h),
                    outcome(bars,i,"PUT" if side=="CALL" else "CALL",h)))
    accepted=defaultdict(list); raw_count=defaultdict(int)
    for (name,h,period,sid),rows in raw.items():
        raw_count[(name,h,period)]+=len(rows)
        next_allowed=-1
        for i,side,orig,inv in sorted(rows):
            if i<next_allowed: continue
            accepted[(name,h,period,"ORIGINAL")].append(orig)
            accepted[(name,h,period,"INVERTED")].append(inv)
            next_allowed=i+h
    total_m5=sum(map(len,segments))
    lines=[
      "# Fourth-wave EURUSD prior-period sweep/reclaim discovery","",
      f"Source: Dukascopy EURUSD M1 BID; {len(m1):,} M1 rows; {total_m5:,} complete M5 bars; {len(segments)} gap-separated segments.",
      f"Coverage: {m1[0].timestamp.isoformat()} — {m1[-1].timestamp.isoformat()}.",
      f"Chronological split by observed UTC dates: TRAIN < {d1}; VALIDATION {d1}–{d2}; TEST >= {d2}; outcomes crossing boundaries purged.",
      "Predeclared event families: sweep-and-close-back-inside of the previous observed UTC trading day's high/low; sweep-and-close-back-inside of the previous completed UTC week's high/low.",
      "High sweep requires high > prior high, close < prior high and bearish candle; low sweep requires low < prior low, close > prior low and bullish candle.",
      "Levels are computed only from completed prior periods; for the daily level, prior observed trading date is used so weekends/holidays do not create false calendar-day levels.",
      "Signal on closed M5 candle; entry next M5 open; expiry at close of Nth subsequent M5 candle. Expiries 5/10/15/20/30/60m.",
      "ORIGINAL and INVERTED are evaluated on identical event timestamps, entries, expiry and non-overlap schedule; only CALL/PUT changes.",
      "One position per family/expiry/continuous segment. Fixed assumed payout 92%: WIN +0.92u, LOSS -1u, DRAW 0u.",
      "Dukascopy BID is not Pocket Option executable pricing; no variable payout, spread or latency model. Multiple testing and serial dependence remain.",
      "",
      "| Pattern | Variant | Expiry | Split | n | W/L/D | Decisive WR | Wilson 95% CI | Net u | Max DD u | Max loss streak | Raw events |",
      "|---|---|---:|---|---:|---|---:|---|---:|---:|---:|---:|"
    ]
    for key in sorted(accepted):
        name,h,period,variant=key; xs=accepted[key]; s=stats(xs); ci=s[5]
        ci_txt="n/a" if ci is None else f"[{ci[0]:.2f},{ci[1]:.2f}]%"
        wr="n/a" if s[4] is None else f"{s[4]:.2f}%"
        lines.append(f"| {name} | {variant} | {h*5}m | {period} | {s[0]} | {s[1]}/{s[2]}/{s[3]} | {wr} | {ci_txt} | {s[6]:+.2f} | {s[7]:.2f} | {s[8]} | {raw_count[(name,h,period)]} |")
    lines += ["","## Screening interpretation","",
      "- Priority: VALIDATION decisive WR >=57%, meaningful sample, positive payout-adjusted net, and no severe TRAIN/TEST contradiction.",
      "- 56.0–56.9% is borderline; below 56% is not prioritized unless inversion produces a notable lead.",
      "- TEST is chronological context only and is not used to tune or select parameters.",
      "- Wilson intervals assume independent outcomes and do not correct for serial dependence or multiple testing.",
      "- Any promising row remains a hypothesis until independent analog periods, matched controls, dependence-aware uncertainty and prospective Pocket Option quote validation.",
      ""]
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text("\n".join(lines),encoding="utf-8")
    print(f"Fourth-wave screen complete: M1={len(m1):,}; M5={total_m5:,}; event families={len(events):,}; report={a.out}")
if __name__=="__main__": main()
