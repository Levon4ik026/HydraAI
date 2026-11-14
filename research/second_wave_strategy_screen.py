#!/usr/bin/env python3
"""Second-wave predeclared EURUSD M5 candidate discovery. Research only."""
from __future__ import annotations
import argparse
from collections import defaultdict
from pathlib import Path
from expanded_strategy_screen import read_m1, ema, outcome, stats
from long_history_validation import make_m5

HORIZONS=(1,2,3,4,6,12)

def extra_events(bars):
    o=[b.open for b in bars]; c=[b.close for b in bars]
    hi=[b.high for b in bars]; lo=[b.low for b in bars]
    n=len(bars); ev=defaultdict(list)
    e9=ema(c,9); e21=ema(c,21); e50=ema(c,50)
    tr=[hi[0]-lo[0]]
    for i in range(1,n):
        tr.append(max(hi[i]-lo[i],abs(hi[i]-c[i-1]),abs(lo[i]-c[i-1])))
    atr=ema(tr,14)
    wr=[None]*n; cci=[None]*n
    tp=[(hi[i]+lo[i]+c[i])/3 for i in range(n)]
    for i in range(19,n):
        window=tp[i-19:i+1]; mean=sum(window)/20
        md=sum(abs(x-mean) for x in window)/20
        if md>0: cci[i]=(tp[i]-mean)/(0.015*md)
    for i in range(14,n):
        hh=max(hi[i-13:i+1]); ll=min(lo[i-13:i+1])
        wr[i]=-100 if hh==ll else -100*(hh-c[i])/(hh-ll)
    for i in range(51,n-13):
        # CCI(20) exits an extreme zone, confirmed by candle direction.
        if cci[i-1] is not None and cci[i] is not None:
            if cci[i-1] < -100 and cci[i] >= -100 and c[i]>o[i]:
                ev["CCI20_EXIT_M100_CALL"].append((i,"CALL"))
            if cci[i-1] > 100 and cci[i] <= 100 and c[i]<o[i]:
                ev["CCI20_EXIT_P100_PUT"].append((i,"PUT"))
        # Williams %R(14) exits oversold/overbought zones.
        if wr[i-1] is not None and wr[i] is not None:
            if wr[i-1] < -80 and wr[i] >= -80 and c[i]>o[i]:
                ev["WILLR14_EXIT_M80_CALL"].append((i,"CALL"))
            if wr[i-1] > -20 and wr[i] <= -20 and c[i]<o[i]:
                ev["WILLR14_EXIT_M20_PUT"].append((i,"PUT"))
        # Donchian breakout: close beyond the prior 20/50-bar range.
        for length in (20,50):
            top=max(hi[i-length:i]); bottom=min(lo[i-length:i])
            if c[i]>top and c[i]>o[i]:
                ev[f"DONCHIAN{length}_BREAK_CALL"].append((i,"CALL"))
            if c[i]<bottom and c[i]<o[i]:
                ev[f"DONCHIAN{length}_BREAK_PUT"].append((i,"PUT"))
        # EMA9/21 fresh crossover, confirmed by candle body.
        if e9[i-1] is not None and e21[i-1] is not None:
            if e9[i-1] <= e21[i-1] and e9[i] > e21[i] and c[i]>o[i]:
                ev["EMA9_21_CROSS_CALL"].append((i,"CALL"))
            if e9[i-1] >= e21[i-1] and e9[i] < e21[i] and c[i]<o[i]:
                ev["EMA9_21_CROSS_PUT"].append((i,"PUT"))
        # Three-bar directional continuation with total displacement >= 1.2 ATR.
        if atr[i] is not None and atr[i]>0:
            up=all(c[j]>o[j] for j in (i-2,i-1,i))
            down=all(c[j]<o[j] for j in (i-2,i-1,i))
            move_up=c[i]-o[i-2]; move_dn=o[i-2]-c[i]
            if up and move_up >= 1.2*atr[i]:
                ev["THREE_BAR_IMPULSE_CALL"].append((i,"CALL"))
            if down and move_dn >= 1.2*atr[i]:
                ev["THREE_BAR_IMPULSE_PUT"].append((i,"PUT"))
        # Trend-aligned EMA20 continuation: close crosses back through EMA20
        # while EMA20 is on the same side of EMA50.
        if e21[i] is not None and e50[i] is not None and e21[i-1] is not None:
            if e21[i]>e50[i] and c[i-1]<=e21[i-1] and c[i]>e21[i] and c[i]>o[i]:
                ev["EMA21_TREND_RECLAIM_CALL"].append((i,"CALL"))
            if e21[i]<e50[i] and c[i-1]>=e21[i-1] and c[i]<e21[i] and c[i]<o[i]:
                ev["EMA21_TREND_RECLAIM_PUT"].append((i,"PUT"))
    return ev

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    m1=read_m1(a.data); segments=make_m5(m1)
    dates=sorted({b.timestamp.date() for s in segments for b in s})
    d1=dates[int(.60*len(dates))]; d2=dates[int(.80*len(dates))]
    raw=defaultdict(list)
    for sid,bars in enumerate(segments):
        ev=extra_events(bars)
        for name,items in ev.items():
            for h in HORIZONS:
                for i,side in items:
                    if i+h>=len(bars): continue
                    start=bars[i].timestamp.date(); settle=bars[i+h].timestamp.date()
                    period="TRAIN" if start<d1 else "VALIDATION" if start<d2 else "TEST"
                    if (period=="TRAIN" and settle>=d1) or (period=="VALIDATION" and settle>=d2): continue
                    inverse_side = "PUT" if side == "CALL" else "CALL"
                    raw[(name,h,period,sid)].append((i,side,outcome(bars,i,side,h),outcome(bars,i,inverse_side,h)))
    accepted=defaultdict(list); raw_counts=defaultdict(int)
    for (name,h,period,sid),rows in raw.items():
        raw_counts[(name,h,period)]+=len(rows)
        nxt=-1
        for i,side,result,inverse_result in sorted(rows):
            if i>=nxt:
                accepted[(name,h,period,"ORIGINAL")].append((i,side,result))
                inverse_side = "PUT" if side == "CALL" else "CALL"
                accepted[(name,h,period,"INVERTED")].append((i,inverse_side,inverse_result))
                nxt=i+h
    lines=[
      "# Second-wave EURUSD M5 strategy discovery","",
      f"Source: Dukascopy EURUSD M1 BID; {len(m1):,} M1 rows; {sum(map(len,segments)):,} M5 bars; {len(segments)} gap-separated segments.",
      f"Coverage: {m1[0].timestamp.isoformat()} — {m1[-1].timestamp.isoformat()}.",
      f"Chronological split: TRAIN < {d1}; VALIDATION {d1}–{d2}; TEST >= {d2}.",
      "Predeclared additional families: CCI(20) extreme exit; Williams %R(14) extreme exit; Donchian(20/50) breakout; EMA(9/21) crossover; three-bar ATR-normalized impulse; EMA21 reclaim aligned with EMA50.",
      "Signal uses closed M5 bars; entry next M5 open; expiry at close of the Nth subsequent M5 bar. Non-overlap within each strategy/expiry/continuous segment.",
      "Expiries 5/10/15/20/30/60m. Payout assumed 92%: WIN +0.92u, LOSS -1u, DRAW 0u; break-even decisive WR 52.0833%.",
      "No parameter tuning in VALIDATION/TEST. Dukascopy BID differs from Pocket Option executable quotes; no platform spread/latency or variable payout modeled.",
      "This is an exploratory second-wave screen. Multiple-testing bias applies; no row is confirmed by this report.","",
      "| Strategy | Variant | Expiry | Split | Trades | W/L/D | Decisive WR | Wilson 95% CI | Net u | Max DD u | Max loss streak | Raw signals |",
      "|---|---|---:|---|---:|---|---:|---|---:|---:|---:|---:|"
    ]
    for key in sorted(accepted):
        name,h,period,variant=key; rs=accepted[key]; s=stats([r[2] for r in rs]); ci=s[5]
        wr="n/a" if s[4] is None else f"{s[4]:.2f}%"
        ci_txt="n/a" if ci is None else f"[{ci[0]:.2f},{ci[1]:.2f}]%"
        lines.append(f"| {name} | {variant} | {h*5}m | {period} | {s[0]} | {s[1]}/{s[2]}/{s[3]} | {wr} | {ci_txt} | {s[6]:+.2f} | {s[7]:.2f} | {s[8]} | {raw_counts[(name,h,period)]} |")
    lines += ["","## Screening notes","",
      "- Discovery priority: validation decisive WR around 57% or higher, sufficient sample, positive assumed-payout net, and no catastrophic split instability.",
      "- Every original event is evaluated twice on identical timestamps: ORIGINAL uses its defined CALL/PUT side; INVERTED flips only CALL ↔ PUT. Signal conditions, entry time, expiry, and non-overlap event set remain identical.",
      "- The inverted variant is a separate discovery candidate, not proof of edge. Do not tune on TEST; independent validation and subsequent confirmation are required.",
      "- TEST is reported for chronological context only; it is not used to tune rules.",
      "- Wilson intervals assume independent outcomes and may understate uncertainty under serial dependence.",
      "- Candidate rows require later situation profiling, matched controls, analog tests, and prospective quote validation.",""]
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text("\n".join(lines),encoding="utf-8")
    print(f"Second-wave screen complete: M1={len(m1):,}; M5={sum(map(len,segments)):,}; groups={len(raw):,}; output={a.out}")
if __name__=="__main__": main()
