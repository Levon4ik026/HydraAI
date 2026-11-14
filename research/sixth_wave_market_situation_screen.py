#!/usr/bin/env python3
"""Sixth-wave EURUSD M5 market-situation discovery. Research only; no execution."""
from __future__ import annotations
import argparse, math
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from expanded_strategy_screen import read_m1, outcome, stats, PAYOUT
from long_history_validation import make_m5

HORIZONS=(1,2,3,4,6,12)  # 5, 10, 15, 20, 30, 60 minutes
ATR_N=14

def atr_values(bars):
    tr=[]
    for i,b in enumerate(bars):
        tr.append(b.high-b.low if i==0 else max(b.high-b.low,abs(b.high-bars[i-1].close),abs(b.low-bars[i-1].close)))
    out=[None]*len(bars)
    if len(tr)>=ATR_N:
        seed=sum(tr[:ATR_N])/ATR_N; out[ATR_N-1]=seed; prev=seed
        for i in range(ATR_N,len(tr)):
            prev=((ATR_N-1)*prev+tr[i])/ATR_N; out[i]=prev
    return out

def observed_period_levels(segments, period):
    """Levels from the immediately preceding observed completed UTC date/week."""
    groups=defaultdict(list)
    for sid,bars in enumerate(segments):
        for i,b in enumerate(bars):
            key=b.timestamp.date() if period=="day" else (b.timestamp.isocalendar().year,b.timestamp.isocalendar().week)
            groups[key].append((sid,i,b))
    keys=sorted(groups)
    result={}
    for pos,key in enumerate(keys):
        if pos==0: continue
        prev=groups[keys[pos-1]]
        result[key]=(max(x[2].high for x in prev),min(x[2].low for x in prev))
    return result

def session_id(ts):
    # Four fixed UTC blocks; descriptive grouping, not an optimized filter.
    return ("ASIA_00_06" if ts.hour<6 else "EUROPE_06_12" if ts.hour<12
            else "US_12_18" if ts.hour<18 else "LATE_18_24")

def add_event(store, name, i, side, bars, session):
    store[name].append((i,side,session))

def discover_events(bars, day_levels, week_levels):
    ev=defaultdict(list); atr=atr_values(bars)
    # Group local indices by UTC period. Levels are from the previous observed period.
    for i in range(max(ATR_N,3),len(bars)-12):
        b=bars[i]; prev=bars[i-1]; sess=session_id(b.timestamp)
        daykey=b.timestamp.date()
        iso=b.timestamp.isocalendar(); weekkey=(iso.year,iso.week)
        # 1/2. Previous observed day/week high/low sweep-and-reclaim.
        for label,levels in (("PREV_DAY",day_levels),("PREV_WEEK",week_levels)):
            lv=levels.get(daykey if label=="PREV_DAY" else weekkey)
            if lv:
                ph,pl=lv
                if b.low<pl and b.close>pl and b.close>b.open:
                    add_event(ev,label+"_LOW_SWEEP_RECLAIM_CALL",i,"CALL",bars,sess)
                if b.high>ph and b.close<ph and b.close<b.open:
                    add_event(ev,label+"_HIGH_SWEEP_RECLAIM_PUT",i,"PUT",bars,sess)
        # 3. Previous observed day breakout close; close-cross only, not wick-only.
        lv=day_levels.get(daykey)
        if lv:
            ph,pl=lv
            if prev.close<=ph and b.close>ph:
                add_event(ev,"PREV_DAY_HIGH_BREAKOUT_CALL",i,"CALL",bars,sess)
            if prev.close>=pl and b.close<pl:
                add_event(ev,"PREV_DAY_LOW_BREAKOUT_PUT",i,"PUT",bars,sess)
        # 4. Round-number rejection: touch/cross grid and close back away.
        # Grid sizes 25 and 50 pips; use only nearest level crossed by candle.
        for step,label in ((0.0025,"25PIP"),(0.0050,"50PIP")):
            first=math.ceil(b.low/step-1e-10)
            last=math.floor(b.high/step+1e-10)
            touched=[k*step for k in range(first,last+1)]
            if touched and b.close>b.open and any(b.low<=level and b.close>level and b.open>=level for level in touched):
                add_event(ev,f"ROUND_{label}_SUPPORT_REJECT_CALL",i,"CALL",bars,sess)
            if touched and b.close<b.open and any(b.high>=level and b.close<level and b.open<=level for level in touched):
                add_event(ev,f"ROUND_{label}_RESISTANCE_REJECT_PUT",i,"PUT",bars,sess)
        # 5/6. Three-bar impulse normalized by ATR known at signal close.
        if atr[i] and atr[i]>0:
            move=b.close-bars[i-2].open
            # Threshold fixed ex ante: net three-bar displacement >=1.5 ATR.
            if move>=1.5*atr[i] and b.close>b.open and (b.high-b.close)<=0.25*max(1e-12,b.high-b.low):
                add_event(ev,"THREE_BAR_IMPULSE_CONTINUATION_CALL",i,"CALL",bars,sess)
            if move<=-1.5*atr[i] and b.close<b.open and (b.close-b.low)<=0.25*max(1e-12,b.high-b.low):
                add_event(ev,"THREE_BAR_IMPULSE_CONTINUATION_PUT",i,"PUT",bars,sess)
            # Exhaustion: same prior displacement, then current candle reverses
            # and closes beyond prior candle midpoint.
            prior_move=bars[i-1].close-bars[i-3].open
            mid=(prev.open+prev.close)/2
            if prior_move>=1.5*atr[i] and b.close<b.open and b.close<mid:
                add_event(ev,"THREE_BAR_IMPULSE_EXHAUSTION_PUT",i,"PUT",bars,sess)
            if prior_move<=-1.5*atr[i] and b.close>b.open and b.close>mid:
                add_event(ev,"THREE_BAR_IMPULSE_EXHAUSTION_CALL",i,"CALL",bars,sess)
    return ev

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    m1=read_m1(a.data); segments=make_m5(m1)
    if len(m1)<100000 or len(segments)<2: raise SystemExit("Insufficient or fragmented history")
    all_dates=sorted({b.timestamp.date() for s in segments for b in s})
    d1=all_dates[int(.60*len(all_dates))]; d2=all_dates[int(.80*len(all_dates))]
    day_levels=observed_period_levels(segments,"day")
    week_levels=observed_period_levels(segments,"week")
    accepted=defaultdict(list); raw_counts=defaultdict(int); family_names=set()
    session_rows=defaultdict(list)
    for sid,bars in enumerate(segments):
        events=discover_events(bars,day_levels,week_levels)
        family_names.update(events)
        for name,items in events.items():
            for h in HORIZONS:
                rows=[]
                for i,side,sess in items:
                    if i+h>=len(bars): continue
                    sig_day=bars[i].timestamp.date()
                    settle_time=bars[i+h].timestamp+timedelta(minutes=5)
                    period="TRAIN" if sig_day<d1 else "VALIDATION" if sig_day<d2 else "TEST"
                    if (period=="TRAIN" and settle_time.date()>=d1) or (period=="VALIDATION" and settle_time.date()>=d2):
                        continue
                    rows.append((i,side,sess,period))
                raw_counts[(name,h)]+=len(rows)
                # Non-overlap is selected separately inside each chronological split.
                for period in ("TRAIN","VALIDATION","TEST"):
                    nxt=-1
                    for i,side,sess,p in sorted((r for r in rows if r[3]==period),key=lambda x:x[0]):
                        if i<nxt: continue
                        original=outcome(bars,i,side,h)
                        inverse=outcome(bars,i,"PUT" if side=="CALL" else "CALL",h)
                        accepted[(name,h,period,"ORIGINAL")].append(original)
                        accepted[(name,h,period,"INVERTED")].append(inverse)
                        session_rows[(name,h,period,"ORIGINAL",sess)].append(original)
                        session_rows[(name,h,period,"INVERTED",sess)].append(inverse)
                        nxt=i+h
    total_m5=sum(map(len,segments))
    lines=[
      "# Sixth-wave EURUSD M5 market-situation discovery","",
      f"Source: Dukascopy EURUSD M1 BID; M1 rows={len(m1):,}; M5 bars={total_m5:,}; gap-separated segments={len(segments)}.",
      f"Coverage: {m1[0].timestamp.isoformat()} — {m1[-1].timestamp.isoformat()}.",
      f"Chronological UTC-date split: TRAIN < {d1}; VALIDATION {d1}–{d2}; TEST >= {d2}; outcomes crossing TRAIN/VALIDATION boundaries purged.",
      "Families: previous observed UTC-day and UTC-week sweep/reclaim; previous observed UTC-day close breakout; 25/50-pip round-number rejection; three-bar ATR-normalized impulse continuation and exhaustion.",
      "All features use completed M5 candles. Prior-day/week levels are computed only from the immediately preceding observed completed UTC period. Round-number grid sizes and impulse threshold are fixed ex ante.",
      "Entry next M5 open; expiry close of the Nth subsequent M5 candle; expiries 5/10/15/20/30/60m. One active position per family/expiry/segment/split.",
      "ORIGINAL and INVERTED use identical timestamps, entry, expiry and non-overlap schedule; only CALL/PUT is reversed. Assumed payout 92%: WIN +0.92u, LOSS -1u, DRAW 0u.",
      "UTC session table is descriptive, not a tuned filter. No actual order book, stops, spread, latency, variable payout or Pocket Option executable quote is observed.",
      "TEST is chronological context only and is not used to select or tune candidates. Wilson intervals do not correct for serial dependence or multiple testing.","",
      "| Family | Variant | Expiry | Split | n | W/L/D | Decisive WR | Wilson 95% CI | Net u | Max DD u | Max loss streak | Raw events |",
      "|---|---|---:|---|---:|---|---:|---|---:|---:|---:|---:|"
    ]
    for key in sorted(accepted):
        name,h,period,variant=key; xs=accepted[key]; s=stats(xs); ci=s[5]
        wr="n/a" if s[4] is None else f"{s[4]:.2f}%"
        ci_txt="n/a" if ci is None else f"[{ci[0]:.2f},{ci[1]:.2f}]%"
        lines.append(f"| {name} | {variant} | {h*5}m | {period} | {s[0]} | {s[1]}/{s[2]}/{s[3]} | {wr} | {ci_txt} | {s[6]:+.2f} | {s[7]:.2f} | {s[8]} | {raw_counts[(name,h)]} |")
    lines += ["","## UTC session breakdown (descriptive only)","",
      "| Family | Variant | Expiry | Split | UTC session | n | W/L/D | Decisive WR | Net u |",
      "|---|---|---:|---|---|---:|---|---:|---:|"]
    for key,xs in sorted(session_rows.items()):
        name,h,period,variant,sess=key; s=stats(xs)
        wr="n/a" if s[4] is None else f"{s[4]:.2f}%"
        lines.append(f"| {name} | {variant} | {h*5}m | {period} | {sess} | {s[0]} | {s[1]}/{s[2]}/{s[3]} | {wr} | {s[6]:+.2f} |")
    lines += ["","## Candidate-screen interpretation","",
      "- Priority: VALIDATION decisive WR >=57%, meaningful sample and positive assumed-payout net. 56.0–56.9% is borderline.",
      "- A high TEST row alone is not a candidate promotion; TRAIN and VALIDATION are primary discovery evidence.",
      "- Inversion is a separate hypothesis on the same event timestamps, not independent evidence.",
      "- The screen is broad and therefore exposed to multiple-testing bias; no candidate is confirmed by this run.",
      "- Next stage only after candidate selection: define its precise market situation and search independent analog periods / matched controls.",
      "- Dukascopy BID is not Pocket Option executable pricing. Prospective quote-level validation is required.",""]
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text("\n".join(lines),encoding="utf-8")
    print(f"Sixth-wave screen complete: M1={len(m1):,}; M5={total_m5:,}; families={len(family_names)}; report={a.out}")

if __name__=="__main__": main()
