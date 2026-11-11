#!/usr/bin/env python3
"""Eleventh-wave EURUSD M5 abnormal-impulse continuation/reversal screen.

Research only. Completed-bar signal, next M5 open entry, fixed expiries,
paired original/inverse directions, chronological split and boundary purge.
"""
from __future__ import annotations
import argparse
from collections import defaultdict, deque
from datetime import timedelta
from pathlib import Path

from expanded_strategy_screen import read_m1, outcome, stats
from long_history_validation import make_m5

HORIZONS = (1, 2, 3, 4, 6, 12)
ATR_LOOKBACK = 20
IMPULSE_THRESHOLDS = (1.5, 2.0, 2.5)
CLOSE_EXTREMES = (0.75, 0.85)

def build_events(bars):
    events = defaultdict(list)
    tr_hist = deque(maxlen=ATR_LOOKBACK)
    for i, b in enumerate(bars):
        if i == 0:
            tr = b.high - b.low
        else:
            prev = bars[i-1].close
            tr = max(b.high-b.low, abs(b.high-prev), abs(b.low-prev))
        # Signal is evaluated against ATR known before this bar.
        if len(tr_hist) == ATR_LOOKBACK:
            atr = sum(tr_hist) / len(tr_hist)
            rng = b.high - b.low
            body = abs(b.close-b.open)
            if atr > 0 and rng > 0:
                expansion = rng / atr
                body_frac = body / rng
                close_loc = (b.close-b.low)/rng
                upper = b.high-max(b.open,b.close)
                lower = min(b.open,b.close)-b.low
                for mult in IMPULSE_THRESHOLDS:
                    if expansion < mult:
                        continue
                    for edge in CLOSE_EXTREMES:
                        suffix = f"R{mult:.1f}_C{edge:.2f}"
                        if body_frac >= 0.60 and close_loc >= edge and b.close > b.open:
                            events[f"BULL_IMPULSE_CONT_{suffix}"].append((i,"CALL"))
                        if body_frac >= 0.60 and close_loc <= 1-edge and b.close < b.open:
                            events[f"BEAR_IMPULSE_CONT_{suffix}"].append((i,"PUT"))
                        # Exhaustion: expanded range, long rejection wick, close away from extreme.
                        if body_frac >= 0.25 and lower >= body*1.5 and close_loc >= 0.55 and b.close > b.open:
                            events[f"LOWER_WICK_EXHAUST_{suffix}"].append((i,"CALL"))
                        if body_frac >= 0.25 and upper >= body*1.5 and close_loc <= 0.45 and b.close < b.open:
                            events[f"UPPER_WICK_EXHAUST_{suffix}"].append((i,"PUT"))
        tr_hist.append(tr)
    return events

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    m1=read_m1(a.data)
    segments=make_m5(m1)
    if len(m1)<100000 or len(segments)<2:
        raise SystemExit("Insufficient or unexpectedly fragmented history")
    dates=sorted({b.timestamp.date() for seg in segments for b in seg})
    d1=dates[int(.60*len(dates))]
    d2=dates[int(.80*len(dates))]
    raw=defaultdict(list)
    families=set()
    for sid,bars in enumerate(segments):
        ev=build_events(bars)
        families.update(ev)
        for name,items in ev.items():
            for i,side in items:
                for h in HORIZONS:
                    if i+h>=len(bars): continue
                    signal_day=bars[i].timestamp.date()
                    settle_day=(bars[i+h].timestamp+timedelta(minutes=5)).date()
                    period="TRAIN" if signal_day<d1 else "VALIDATION" if signal_day<d2 else "TEST"
                    if (period=="TRAIN" and settle_day>=d1) or (period=="VALIDATION" and settle_day>=d2):
                        continue
                    orig=outcome(bars,i,side,h)
                    inv=outcome(bars,i,"PUT" if side=="CALL" else "CALL",h)
                    raw[(name,h,period,sid)].append((i,orig,inv))
    accepted=defaultdict(list)
    raw_counts=defaultdict(int)
    for (name,h,period,sid),rows in raw.items():
        raw_counts[(name,h,period)]+=len(rows)
        next_allowed=-1
        for i,orig,inv in sorted(rows):
            if i<next_allowed: continue
            accepted[(name,h,period,"ORIGINAL")].append(orig)
            accepted[(name,h,period,"INVERTED")].append(inv)
            next_allowed=i+h
    lines=[
      "# Eleventh-wave EURUSD M5 abnormal-impulse discovery","",
      f"Source: Dukascopy EURUSD M1 BID; M1 rows={len(m1):,}; complete M5={sum(map(len,segments)):,}; segments={len(segments)}.",
      f"Coverage: {m1[0].timestamp.isoformat()} — {m1[-1].timestamp.isoformat()}.",
      f"Chronological split by observed UTC dates: TRAIN < {d1}; VALIDATION {d1}–{d2}; TEST >= {d2}; crossing outcomes purged.",
      "Signal is a completed M5 candle whose range is at least 1.5/2.0/2.5 times the mean true range of the preceding 20 completed M5 candles. ATR excludes the signal candle.",
      "Continuation: body/range >=0.60 and close in outer 25%/15% of candle in impulse direction. Exhaustion: expanded range, rejection wick >=1.5x body and close away from rejected extreme.",
      "Entry next M5 open; expiry at close of 1/2/3/4/6/12 subsequent M5 bars (5/10/15/20/30/60m).",
      "ORIGINAL and INVERTED use identical signal timestamps, entry, expiry and non-overlap schedule; only CALL/PUT changes.",
      "One position per family/threshold/expiry/segment. Assumed payout +0.92u/-1u/0u; break-even decisive WR 52.08%.",
      "BID-only historical proxy, not Pocket Option executable quotes. No spread, payout variation or latency model. Multiple testing and serial dependence remain.",
      "",
      "| Pattern | Variant | Expiry | Split | n | W/L/D | Decisive WR | Wilson 95% CI | Net u | Max DD u | Max loss streak | Raw events |",
      "|---|---|---:|---|---:|---|---:|---|---:|---:|---:|---:|"
    ]
    for key in sorted(accepted):
        name,h,period,variant=key
        s=stats(accepted[key]); ci=s[5]
        ci_txt="n/a" if ci is None else f"[{ci[0]:.2f},{ci[1]:.2f}]%"
        wr="n/a" if s[4] is None else f"{s[4]:.2f}%"
        lines.append(f"| {name} | {variant} | {h*5}m | {period} | {s[0]} | {s[1]}/{s[2]}/{s[3]} | {wr} | {ci_txt} | {s[6]:+.2f} | {s[7]:.2f} | {s[8]} | {raw_counts[(name,h,period)]} |")
    lines += ["","## Screening rules","",
      "- First inspect VALIDATION; prioritize >=57% with meaningful N and positive net. 56.0–56.9% is borderline.",
      "- TRAIN/VALIDATION consistency matters; TEST is descriptive only and must not select or tune candidates.",
      "- Inversion is a paired hypothesis, not independent evidence.",
      "- Wilson intervals do not correct for serial dependence or multiple testing; shortlisted rows require day-block bootstrap and prospective quote-level replay.",
      "- No candidate is promoted and no application or production code is changed.",""]
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text("\n".join(lines),encoding="utf-8")
    print(f"Eleventh-wave screen complete: M1={len(m1):,}; M5={sum(map(len,segments)):,}; families={len(families)}; report={a.out}")

if __name__=="__main__":
    main()
