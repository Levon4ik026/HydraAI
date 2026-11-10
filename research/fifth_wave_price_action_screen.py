#!/usr/bin/env python3
"""Fifth-wave predeclared EURUSD M5 price-action discovery. Research only."""
from __future__ import annotations
import argparse
from collections import defaultdict
from pathlib import Path
from expanded_strategy_screen import read_m1, outcome, stats
from long_history_validation import make_m5

HORIZONS=(1,2,3,4,6,12)

def price_action_events(bars):
    ev=defaultdict(list)
    o=[b.open for b in bars]; h=[b.high for b in bars]
    l=[b.low for b in bars]; c=[b.close for b in bars]
    for i in range(60,len(bars)-13):
        body=abs(c[i]-o[i]); rng=h[i]-l[i]
        if rng<=0 or body<=0: continue
        bull=c[i]>o[i]; bear=c[i]<o[i]
        prev_bull=c[i-1]>o[i-1]; prev_bear=c[i-1]<o[i-1]
        # Real-body engulfing after an opposite candle.
        if bull and prev_bear and o[i]<=c[i-1] and c[i]>=o[i-1]:
            ev["BULLISH_BODY_ENGULF_CALL"].append((i,"CALL"))
        if bear and prev_bull and o[i]>=c[i-1] and c[i]<=o[i-1]:
            ev["BEARISH_BODY_ENGULF_PUT"].append((i,"PUT"))
        # Pin bars: dominant rejection wick >=2x body, opposite wick <= body,
        # close in the outer quartile of the candle range.
        upper=h[i]-max(o[i],c[i]); lower=min(o[i],c[i])-l[i]
        if lower>=2*body and upper<=body and (c[i]-l[i])/rng>=0.75:
            ev["BULLISH_LOWER_PIN_CALL"].append((i,"CALL"))
        if upper>=2*body and lower<=body and (h[i]-c[i])/rng>=0.75:
            ev["BEARISH_UPPER_PIN_PUT"].append((i,"PUT"))
        # Outside-bar reversal: takes both prior extremes and closes near its edge.
        if h[i]>h[i-1] and l[i]<l[i-1]:
            if bull and (h[i]-c[i])/rng<=0.25:
                ev["BULLISH_OUTSIDE_REVERSAL_CALL"].append((i,"CALL"))
            if bear and (c[i]-l[i])/rng<=0.25:
                ev["BEARISH_OUTSIDE_REVERSAL_PUT"].append((i,"PUT"))
        # Three-candle directional exhaustion followed by a reversal candle.
        if i>=3:
            if all(c[j]>o[j] for j in (i-3,i-2,i-1)) and bear and c[i]<o[i-1]:
                ev["THREE_UP_EXHAUSTION_PUT"].append((i,"PUT"))
            if all(c[j]<o[j] for j in (i-3,i-2,i-1)) and bull and c[i]>o[i-1]:
                ev["THREE_DOWN_EXHAUSTION_CALL"].append((i,"CALL"))
        # NR7 compression: current range is the narrowest of the last seven;
        # direction is determined by close location in the signal candle.
        if i>=6 and rng<=min(h[j]-l[j] for j in range(i-6,i)):
            if (c[i]-l[i])/rng>=0.75:
                ev["NR7_CLOSE_HIGH_CALL"].append((i,"CALL"))
            elif (c[i]-l[i])/rng<=0.25:
                ev["NR7_CLOSE_LOW_PUT"].append((i,"PUT"))
    return ev

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    m1=read_m1(a.data); segments=make_m5(m1)
    if len(m1)<100000 or len(segments)<2:
        raise SystemExit("Insufficient or unexpectedly fragmented history")
    dates=sorted({b.timestamp.date() for seg in segments for b in seg})
    d1=dates[int(.60*len(dates))]; d2=dates[int(.80*len(dates))]
    raw=defaultdict(list); family_names=set()
    for sid,bars in enumerate(segments):
        events=price_action_events(bars)
        family_names.update(events)
        for name,items in events.items():
            for i,side in items:
                for horizon in HORIZONS:
                    if i+horizon>=len(bars): continue
                    signal_day=bars[i].timestamp.date()
                    settle_day=bars[i+horizon].timestamp.date()
                    period="TRAIN" if signal_day<d1 else "VALIDATION" if signal_day<d2 else "TEST"
                    if (period=="TRAIN" and settle_day>=d1) or (period=="VALIDATION" and settle_day>=d2):
                        continue
                    original=outcome(bars,i,side,horizon)
                    inverse=outcome(bars,i,"PUT" if side=="CALL" else "CALL",horizon)
                    raw[(name,horizon,period,sid)].append((i,original,inverse))
    accepted=defaultdict(list); raw_counts=defaultdict(int)
    for (name,horizon,period,sid),rows in raw.items():
        raw_counts[(name,horizon,period)]+=len(rows)
        next_allowed=-1
        for i,original,inverse in sorted(rows):
            if i<next_allowed: continue
            accepted[(name,horizon,period,"ORIGINAL")].append(original)
            accepted[(name,horizon,period,"INVERTED")].append(inverse)
            next_allowed=i+horizon
    total_m5=sum(map(len,segments))
    lines=[
      "# Fifth-wave EURUSD M5 price-action discovery","",
      f"Source: Dukascopy EURUSD M1 BID; {len(m1):,} M1 rows; {total_m5:,} complete M5 bars; {len(segments)} gap-separated segments.",
      f"Coverage: {m1[0].timestamp.isoformat()} — {m1[-1].timestamp.isoformat()}.",
      f"Chronological split by observed UTC dates: TRAIN < {d1}; VALIDATION {d1}–{d2}; TEST >= {d2}; boundary-crossing outcomes purged.",
      "Predeclared families: bullish/bearish real-body engulfing; bullish lower / bearish upper pin bars; bullish/bearish outside-bar reversal; three-candle directional exhaustion; NR7 compression with close near candle extreme.",
      "All signals use completed M5 candles; entry next M5 open; expiry at close of the Nth subsequent M5 candle. Expiries 5/10/15/20/30/60m.",
      "ORIGINAL and INVERTED use identical signal events, entries, expiry and non-overlap schedule; only CALL/PUT changes.",
      "One position per pattern/expiry/continuous segment. Fixed assumed payout 92%: WIN +0.92u, LOSS -1u, DRAW 0u.",
      "Dukascopy BID is not Pocket Option executable pricing; variable payout, spread and latency are not modeled. Multiple testing and serial dependence remain.",
      "",
      "| Pattern | Variant | Expiry | Split | n | W/L/D | Decisive WR | Wilson 95% CI | Net u | Max DD u | Max loss streak | Raw events |",
      "|---|---|---:|---|---:|---|---:|---|---:|---:|---:|---:|"
    ]
    for key in sorted(accepted):
        name,horizon,period,variant=key; xs=accepted[key]; s=stats(xs); ci=s[5]
        wr="n/a" if s[4] is None else f"{s[4]:.2f}%"
        ci_txt="n/a" if ci is None else f"[{ci[0]:.2f},{ci[1]:.2f}]%"
        lines.append(f"| {name} | {variant} | {horizon*5}m | {period} | {s[0]} | {s[1]}/{s[2]}/{s[3]} | {wr} | {ci_txt} | {s[6]:+.2f} | {s[7]:.2f} | {s[8]} | {raw_counts[(name,horizon,period)]} |")
    lines += ["","## Screening interpretation","",
      "- Priority discovery threshold: VALIDATION decisive WR >=57%, meaningful sample and positive assumed-payout net; 56.0–56.9% is borderline.",
      "- TEST is chronological context only and must not be used to select patterns or tune thresholds.",
      "- Inversion is a separate hypothesis, not independent evidence; same event timestamps and non-overlap are retained.",
      "- Wilson intervals assume independent outcomes and do not correct for serial dependence or multiple testing.",
      "- A promising row remains a candidate until independent analog periods, matched controls, dependence-aware uncertainty and prospective Pocket Option quote validation.",""]
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text("\n".join(lines),encoding="utf-8")
    print(f"Fifth-wave screen complete: M1={len(m1):,}; M5={total_m5:,}; event families={len(family_names):,}; report={a.out}")
if __name__=="__main__": main()
