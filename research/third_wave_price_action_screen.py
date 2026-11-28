#!/usr/bin/env python3
"""Third-wave, predeclared EURUSD M5 price-action discovery. Research only."""
from __future__ import annotations
import argparse
from collections import defaultdict
from pathlib import Path
from expanded_strategy_screen import read_m1, outcome, stats
from long_history_validation import make_m5

HORIZONS=(1,2,3,4,6,12)

def events_for(bars):
    o=[b.open for b in bars]; h=[b.high for b in bars]
    l=[b.low for b in bars]; c=[b.close for b in bars]
    ev=defaultdict(list)
    for i in range(52,len(bars)-13):
        body=abs(c[i]-o[i]); rng=h[i]-l[i]
        if rng<=0: continue
        prev_body=abs(c[i-1]-o[i-1])
        # Strict body engulfing reversal.
        if c[i]>o[i] and c[i-1]<o[i-1] and o[i]<=c[i-1] and c[i]>=o[i-1]:
            ev["ENGULF_BULL_CALL"].append((i,"CALL"))
        if c[i]<o[i] and c[i-1]>o[i-1] and o[i]>=c[i-1] and c[i]<=o[i-1]:
            ev["ENGULF_BEAR_PUT"].append((i,"PUT"))
        # Long-wick rejection: rejection wick >= 2x body; opposite wick <= body.
        lower=min(o[i],c[i])-l[i]; upper=h[i]-max(o[i],c[i])
        if body>0 and lower>=2*body and upper<=body and c[i]>=l[i]+0.70*rng:
            ev["PINBAR_BULL_CALL"].append((i,"CALL"))
        if body>0 and upper>=2*body and lower<=body and c[i]<=l[i]+0.30*rng:
            ev["PINBAR_BEAR_PUT"].append((i,"PUT"))
        # Outside-bar reversal with close in outer 25% of range.
        if h[i]>h[i-1] and l[i]<l[i-1]:
            if c[i]<o[i] and c[i]<=l[i]+0.25*rng:
                ev["OUTSIDE_BEAR_PUT"].append((i,"PUT"))
            if c[i]>o[i] and c[i]>=l[i]+0.75*rng:
                ev["OUTSIDE_BULL_CALL"].append((i,"CALL"))
        # Three-candle exhaustion: two same-direction bars, then opposite close
        # through the first candle's midpoint.
        mid=(o[i-2]+c[i-2])/2
        if c[i-2]>o[i-2] and c[i-1]>o[i-1] and c[i]<o[i] and c[i]<mid:
            ev["THREE_UP_EXHAUST_PUT"].append((i,"PUT"))
        mid=(o[i-2]+c[i-2])/2
        if c[i-2]<o[i-2] and c[i-1]<o[i-1] and c[i]>o[i] and c[i]>mid:
            ev["THREE_DOWN_EXHAUST_CALL"].append((i,"CALL"))
        # Failed 20/50-bar close breakout: prior bar breaks, current closes back inside.
        for n in (20,50):
            top=max(h[i-n-1:i-1]); bottom=min(l[i-n-1:i-1])
            if c[i-1]>top and c[i]<top and c[i]<o[i]:
                ev[f"FAILED_DONCHIAN{n}_UP_PUT"].append((i,"PUT"))
            if c[i-1]<bottom and c[i]>bottom and c[i]>o[i]:
                ev[f"FAILED_DONCHIAN{n}_DOWN_CALL"].append((i,"CALL"))
    return ev

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    m1=read_m1(a.data); segments=make_m5(m1)
    days=sorted({b.timestamp.date() for s in segments for b in s})
    if len(days)<100: raise SystemExit("Insufficient date coverage")
    d1=days[int(.60*len(days))]; d2=days[int(.80*len(days))]
    raw=defaultdict(list)
    for sid,bars in enumerate(segments):
        ev=events_for(bars)
        for name,items in ev.items():
            for i,side in items:
                for horizon in HORIZONS:
                    if i+horizon>=len(bars): continue
                    signal_day=bars[i].timestamp.date()
                    settle_day=bars[i+horizon].timestamp.date()
                    period="TRAIN" if signal_day<d1 else "VALIDATION" if signal_day<d2 else "TEST"
                    if (period=="TRAIN" and settle_day>=d1) or (period=="VALIDATION" and settle_day>=d2):
                        continue
                    raw[(name,horizon,period,sid)].append((i,side,
                        outcome(bars,i,side,horizon),
                        outcome(bars,i,"PUT" if side=="CALL" else "CALL",horizon)))
    accepted=defaultdict(list); raw_counts=defaultdict(int)
    for (name,horizon,period,sid),rows in raw.items():
        raw_counts[(name,horizon,period)]+=len(rows)
        next_allowed=-1
        for i,side,original,inverse in sorted(rows):
            if i<next_allowed: continue
            accepted[(name,horizon,period,"ORIGINAL")].append(original)
            accepted[(name,horizon,period,"INVERTED")].append(inverse)
            next_allowed=i+horizon
    lines=[
      "# Third-wave EURUSD M5 price-action discovery","",
      f"Source: Dukascopy EURUSD M1 BID; {len(m1):,} M1 rows; {sum(map(len,segments)):,} complete M5 bars; {len(segments)} gap-separated segments.",
      f"Coverage: {m1[0].timestamp.isoformat()} — {m1[-1].timestamp.isoformat()}.",
      f"Chronological split by observed calendar dates: TRAIN < {d1}; VALIDATION {d1}–{d2}; TEST >= {d2}.",
      "Predeclared families: strict bullish/bearish body engulfing; long-wick pinbar rejection; outside-bar reversal; three-candle exhaustion; failed Donchian(20/50) close breakout.",
      "Signal on closed M5 candle; entry at next M5 open; expiry at close of Nth subsequent M5 bar. Expiries 5/10/15/20/30/60m.",
      "Both ORIGINAL and INVERTED are scored on identical signal events, entry timestamps, expiry and non-overlap schedule. Only CALL/PUT changes.",
      "One position per family/expiry/continuous segment; split-boundary outcomes purged. Fixed assumed payout 92%: WIN +0.92u, LOSS -1u, DRAW 0u.",
      "External Dukascopy BID feed, not Pocket Option executable quotes. No variable payout, spread or latency model. Multi-family screening creates multiple-testing risk.","",
      "| Pattern | Variant | Expiry | Split | n | W/L/D | Decisive WR | Wilson 95% CI | Net u | Max DD u | Max loss streak | Raw events |",
      "|---|---|---:|---|---:|---|---:|---|---:|---:|---:|---:|"
    ]
    for key in sorted(accepted):
        name,horizon,period,variant=key
        xs=accepted[key]; s=stats(xs); ci=s[5]
        ci_txt="n/a" if ci is None else f"[{ci[0]:.2f},{ci[1]:.2f}]%"
        wr="n/a" if s[4] is None else f"{s[4]:.2f}%"
        lines.append(f"| {name} | {variant} | {horizon*5}m | {period} | {s[0]} | {s[1]}/{s[2]}/{s[3]} | {wr} | {ci_txt} | {s[6]:+.2f} | {s[7]:.2f} | {s[8]} | {raw_counts[(name,horizon,period)]} |")
    lines += ["","## Screening interpretation","",
      "- Discovery priority: VALIDATION decisive WR >=57%, meaningful sample, positive payout-adjusted net, and no severe TRAIN/TEST contradiction.",
      "- 56.0–56.9% is borderline; under 56% is not prioritized unless inversion or an unusual repeatable pattern merits follow-up.",
      "- TEST is reported for chronological context only; do not tune thresholds or choose variants from TEST.",
      "- Wilson intervals assume independent outcomes and do not correct for serial dependence or multiple testing.",
      "- Strong rows remain hypotheses until independent analog periods, matched controls, dependence-aware uncertainty and prospective platform quotes are tested.",""]
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(f"Third-wave screen complete: M1={len(m1):,}; M5={sum(map(len,segments)):,}; raw groups={len(raw):,}; report={a.out}")
if __name__=="__main__": main()
