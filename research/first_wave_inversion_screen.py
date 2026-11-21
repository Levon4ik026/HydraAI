#!/usr/bin/env python3
"""First-wave exact-event inversion audit. Research only; no production impact."""
from __future__ import annotations
import argparse
from collections import defaultdict
from pathlib import Path
from expanded_strategy_screen import read_m1, make_events, outcome, stats, HORIZONS
from long_history_validation import make_m5

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    m1=read_m1(a.data)
    segments=make_m5(m1)
    dates=sorted({b.timestamp.date() for seg in segments for b in seg})
    d1=dates[int(.60*len(dates))]
    d2=dates[int(.80*len(dates))]
    raw=defaultdict(list)
    excluded_macd=0
    for sid,bars in enumerate(segments):
        events=make_events(bars)
        for name,items in events.items():
            # The expanded screen's MACD signal EMA was seeded with placeholder zeros.
            # Exclude it until that independent indicator implementation is repaired.
            if name.startswith("MACD129_"):
                excluded_macd += len(items)
                continue
            for h in HORIZONS:
                for i,side in items:
                    if i+h>=len(bars):
                        continue
                    start=bars[i].timestamp.date()
                    settle=bars[i+h].timestamp.date()
                    period="TRAIN" if start<d1 else "VALIDATION" if start<d2 else "TEST"
                    if (period=="TRAIN" and settle>=d1) or (period=="VALIDATION" and settle>=d2):
                        continue
                    opposite="PUT" if side=="CALL" else "CALL"
                    original=outcome(bars,i,side,h)
                    inverse=outcome(bars,i,opposite,h)
                    raw[(name,h,period,sid)].append((i,side,original,inverse))
    accepted=defaultdict(list)
    raw_counts=defaultdict(int)
    for (name,h,period,sid),rows in raw.items():
        raw_counts[(name,h,period)] += len(rows)
        nxt=-1
        for i,side,original,inverse in sorted(rows):
            # Same non-overlap decision for both variants; only direction changes.
            if i>=nxt:
                accepted[(name,h,period,"ORIGINAL")].append(original)
                accepted[(name,h,period,"INVERTED")].append(inverse)
                nxt=i+h
    lines=[
      "# First-wave exact-event inversion audit","",
      f"Source: Dukascopy EURUSD M1 BID; {len(m1):,} M1 rows; {sum(map(len,segments)):,} complete M5 bars; {len(segments)} gap-separated segments.",
      f"Coverage: {m1[0].timestamp.isoformat()} — {m1[-1].timestamp.isoformat()}.",
      f"Chronological split: TRAIN < {d1}; VALIDATION {d1}–{d2}; TEST >= {d2}.",
      "Families: RSI(14) extreme reversals; Stochastic(14) extreme exits; Bollinger(20) re-entry; EMA20 pullback aligned with EMA50; inside-bar breakout; ATR(14) expansion.",
      "MACD combinations excluded because the source screen's signal EMA initialization used placeholder zeros before valid MACD values existed.",
      "Closed M5 signal; entry at next M5 open; expiry at close of the Nth subsequent M5 bar. Horizons: 5/10/15/20/30/60m.",
      "Original and inverse outcomes use identical event timestamps, expiry, data split and non-overlap selection. Only CALL ↔ PUT is changed.",
      "Payout assumed 92%: WIN +0.92u, LOSS -1u, DRAW 0u; break-even decisive WR 52.0833%. Dukascopy BID is not Pocket Option executable quotes; spread, latency and variable payout are not modeled.",
      "Exploratory audit only; multiple-testing bias applies; no candidate is confirmed.","",
      "| Strategy | Variant | Expiry | Split | Trades | W/L/D | Decisive WR | Wilson 95% CI | Net u | Max DD u | Max loss streak | Raw signals |",
      "|---|---|---:|---|---:|---|---:|---|---:|---:|---:|---:|"
    ]
    for key in sorted(accepted):
        name,h,period,variant=key
        s=stats(accepted[key]); ci=s[5]
        wr="n/a" if s[4] is None else f"{s[4]:.2f}%"
        ci_txt="n/a" if ci is None else f"[{ci[0]:.2f},{ci[1]:.2f}]%"
        lines.append(f"| {name} | {variant} | {h*5}m | {period} | {s[0]} | {s[1]}/{s[2]}/{s[3]} | {wr} | {ci_txt} | {s[6]:+.2f} | {s[7]:.2f} | {s[8]} | {raw_counts[(name,h,period)]} |")
    lines += ["","## Reading the results","",
      "- Compare ORIGINAL and INVERTED within the same strategy, expiry and split; event cohorts are identical.",
      "- The historical RSI14_70_REV_PUT candidate is included; its inverse is CALL on the exact same RSI>=70 bearish-candle events.",
      "- Weak original signals are retained for inversion analysis; an inverse result does not establish an edge by itself.",
      "- Priority is Validation around 57% or higher, adequate sample, positive payout-adjusted net, and acceptable independent Test behavior. Test is not used to tune.",
      "- Wilson intervals assume independent outcomes and may understate uncertainty under serial dependence. Matched controls and block bootstrap remain outstanding.",
      "- Do not infer market-situation rules from this screen. First complete candidate discovery; profile situations only after the candidate pool is broadened.",""]
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text("\n".join(lines),encoding="utf-8")
    print(f"First-wave inversion audit complete: M1={len(m1):,}; M5={sum(map(len,segments)):,}; groups={len(raw):,}; excluded_MACD_events={excluded_macd:,}; output={a.out}")
if __name__=="__main__":
    main()
