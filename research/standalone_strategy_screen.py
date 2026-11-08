#!/usr/bin/env python3
"""Standalone EURUSD M5 strategy-family screen. Research only; no execution.

Signals are computed from closed bars only. Entry is next M5 open; expiry is
the close of the Nth M5 bar after the signal. Gaps split the series.
"""
from __future__ import annotations
import argparse, csv, math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from long_history_validation import Bar, make_m5

PAYOUT = 0.92
HORIZONS = (1, 2, 3, 4, 6, 12)  # 5,10,15,20,30,60 minutes

def read_m1(path):
    rows = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        required = {"timestamp","open","high","low","close"}
        if not required.issubset(rd.fieldnames or []):
            raise ValueError(f"Unexpected CSV header: {rd.fieldnames}")
        for r in rd:
            ts = datetime.fromtimestamp(int(float(r["timestamp"]))/1000, tz=timezone.utc)
            o,h,l,c = (float(r[k]) for k in ("open","high","low","close"))
            if all(math.isfinite(x) and x > 0 for x in (o,h,l,c)) and h >= max(o,l,c) and l <= min(o,c):
                rows[ts] = Bar(ts,o,h,l,c)
    return [rows[t] for t in sorted(rows)]

def rolling_mean(x, i, n):
    if i+1<n: return None
    return sum(x[i-n+1:i+1])/n

def rolling_std(x, i, n):
    m=rolling_mean(x,i,n)
    if m is None:return None
    return math.sqrt(sum((v-m)**2 for v in x[i-n+1:i+1])/n)

def build_specs():
    specs=[]
    # False break: pierce prior range, then close back inside; direction is reversal.
    for n in (12,24):
        specs += [(f"FALSE_BREAK_{n}_PUT", "fb_put", n, 0),
                  (f"FALSE_BREAK_{n}_CALL", "fb_call", n, 0)]
    # Momentum range breakout: close beyond previous range in breakout direction.
    for n in (12,24):
        specs += [(f"MOM_BREAK_{n}_CALL","mom_call",n,0),
                  (f"MOM_BREAK_{n}_PUT","mom_put",n,0)]
    # Mean reversion: normalized distance from rolling mean + reversal close.
    for n in (20,40):
        for z in (1.5,2.0):
            specs += [(f"MEAN_REV_{n}_Z{z}_CALL","mr_call",n,z),
                      (f"MEAN_REV_{n}_Z{z}_PUT","mr_put",n,z)]
    # Candle-only patterns: bullish/bearish engulfing and rejection pin bars.
    specs += [("ENGULF_CALL","engulf_call",0,0),("ENGULF_PUT","engulf_put",0,0),
              ("PIN_REJECT_CALL","pin_call",0,0),("PIN_REJECT_PUT","pin_put",0,0)]
    return specs

def signals_for_segment(bars, specs):
    c=[b.close for b in bars]; o=[b.open for b in bars]
    hi=[b.high for b in bars]; lo=[b.low for b in bars]
    out=defaultdict(list)
    for i in range(41, len(bars)-13):
        for name,kind,n,p in specs:
            side=None
            if kind.startswith("fb_"):
                ph=max(hi[i-n:i]); pl=min(lo[i-n:i])
                if kind=="fb_put" and hi[i]>ph and c[i]<ph and c[i]<o[i]: side="PUT"
                if kind=="fb_call" and lo[i]<pl and c[i]>pl and c[i]>o[i]: side="CALL"
            elif kind.startswith("mom_"):
                ph=max(hi[i-n:i]); pl=min(lo[i-n:i])
                if kind=="mom_call" and c[i]>ph and c[i]>o[i]: side="CALL"
                if kind=="mom_put" and c[i]<pl and c[i]<o[i]: side="PUT"
            elif kind.startswith("mr_"):
                m=rolling_mean(c,i-1,n); sd=rolling_std(c,i-1,n)
                if sd and sd>0:
                    z=(c[i-1]-m)/sd
                    if kind=="mr_call" and z<=-p and c[i]>o[i] and c[i]>c[i-1]: side="CALL"
                    if kind=="mr_put" and z>=p and c[i]<o[i] and c[i]<c[i-1]: side="PUT"
            elif kind.startswith("engulf_"):
                bull=(c[i-1]<o[i-1] and c[i]>o[i] and o[i]<=c[i-1] and c[i]>=o[i-1])
                bear=(c[i-1]>o[i-1] and c[i]<o[i] and o[i]>=c[i-1] and c[i]<=o[i-1])
                if kind=="engulf_call" and bull: side="CALL"
                if kind=="engulf_put" and bear: side="PUT"
            elif kind.startswith("pin_"):
                rng=hi[i]-lo[i]
                if rng>0:
                    lower=min(o[i],c[i])-lo[i]; upper=hi[i]-max(o[i],c[i])
                    if kind=="pin_call" and lower/rng>=0.60 and (c[i]-lo[i])/rng>=0.65: side="CALL"
                    if kind=="pin_put" and upper/rng>=0.60 and (hi[i]-c[i])/rng>=0.65: side="PUT"
            if side: out[name].append((i,side))
    return out

def outcome(bars,i,side,h):
    delta=bars[i+h].close-bars[i+1].open
    if abs(delta)<1e-12:return "D"
    return "W" if (delta>0)==(side=="CALL") else "L"

def split_dates(segments):
    dates=sorted({b.timestamp.date() for s in segments for b in s})
    return dates[int(.60*len(dates))], dates[int(.80*len(dates))]

def summarize(rows):
    w=sum(x=="W" for x in rows); l=sum(x=="L" for x in rows); d=sum(x=="D" for x in rows)
    dec=w+l; wr=100*w/dec if dec else float("nan")
    net=w*PAYOUT-l; pf=w*PAYOUT/l if l else (float("inf") if w else 0)
    return len(rows),w,l,d,wr,net,pf

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--out",type=Path,default=Path("research/STANDALONE_STRATEGY_SCREEN.md"))
    a=ap.parse_args()
    m1=read_m1(a.data); segments=make_m5(m1); d1,d2=split_dates(segments)
    specs=build_specs(); records=[]
    for sid,bars in enumerate(segments):
        sigs=signals_for_segment(bars,specs)
        for name,events in sigs.items():
            for h in HORIZONS:
                for i,side in events:
                    if i+h>=len(bars): continue
                    st=bars[i].timestamp.date(); et=bars[i+h].timestamp.date()
                    if st<d1:
                        period="TRAIN" if et<d1 else None
                    elif st<d2:
                        period="VALIDATION" if et<d2 else None
                    else: period="TEST"
                    if period:
                        records.append((name,h,sid,i,side,period,outcome(bars,i,side,h)))
    grouped=defaultdict(list)
    for r in records: grouped[(r[0],r[1],r[5])].append(r)
    # one-position trades independently per family and expiry, no overlap within segment
    nonoverlap=defaultdict(list)
    raw_by=defaultdict(list)
    for r in records: raw_by[(r[0],r[1],r[5],r[2])].append(r)
    for (name,h,period,sid),rows in raw_by.items():
        next_i=-1
        for r in sorted(rows,key=lambda x:x[3]):
            if r[3]>=next_i:
                nonoverlap[(name,h,period)].append(r[6]); next_i=r[3]+h
    rows=["# Standalone EURUSD strategy-family screen","",
      f"Source: Dukascopy EURUSD M1 BID; {len(m1):,} M1 rows; {sum(map(len,segments)):,} complete M5 bars; {len(segments):,} gap-separated segments.",
      f"Coverage: {m1[0].timestamp.isoformat()} to {m1[-1].timestamp.isoformat()}.",
      f"Chronological split by calendar dates: TRAIN < {d1}; VALIDATION {d1} through {d2}; TEST >= {d2}.",
      "Families: false range breaks, momentum range breaks, mean reversion, engulfing, rejection pin bars.",
      "Parameters fixed before evaluation; no optimization. Closed M5 signal, next M5 open entry; expiry at close of Nth subsequent M5 bar.",
      "Horizon set: 5/10/15/20/30/60 minutes. Payout: WIN +0.92u, LOSS -1u, DRAW 0u; break-even decisive WR 52.0833%.",
      "Raw events and one-position non-overlap are reported separately. Non-overlap is enforced within each individual strategy/expiry.",
      "No transaction cost or Pocket Option quote simulation: Dukascopy BID is not the platform's exact price stream.",
      "Exploratory screen with many tested combinations; top rows are not confirmatory evidence. Do not promote from TEST ranking; select on validation and verify prospectively.","",
      "## Results — non-overlapping schedule","",
      "| Family | Expiry | Period | Trades | W/L/D | Decisive WR | Net u | PF | Signals/20 trading days* |",
      "|---|---:|---|---:|---|---:|---:|---:|---:|"]
    # use 20 trading days as frequency normalization; count unique observed weekdays is not perfect, but weekdays approx
    all_days=max(1,len({b.timestamp.date() for s in segments for b in s if b.timestamp.date()>=d1}))
    for name,h,period in sorted(nonoverlap):
        vals=nonoverlap[(name,h,period)]; n,w,l,d,wr,net,pf=summarize(vals)
        period_days=len({r[3] for r in grouped[(name,h,period)]})
        # calculate signal rate from number of rows / period calendar trading weekdays
        date_lo=d1 if period=="VALIDATION" else d2 if period=="TEST" else min(b.timestamp.date() for s in segments for b in s)
        date_hi=d2 if period=="VALIDATION" else max(b.timestamp.date() for s in segments for b in s)
        weekdays=max(1,sum(1 for x in {b.timestamp.date() for s in segments for b in s} if date_lo<=x<date_hi and x.weekday()<5))
        freq=20*n/weekdays
        rows.append(f"| {name} | {h*5}m | {period} | {n} | {w}/{l}/{d} | {wr:.2f}% | {net:+.2f} | {pf:.2f} | {freq:.2f} |")
    rows += ["","## Raw event counts by family and expiry","",
      "| Family | Expiry | TRAIN | VALIDATION | TEST |","|---|---:|---:|---:|---:|"]
    for name,h in sorted({(r[0],r[1]) for r in records}):
        vals=[len(grouped[(name,h,p)]) for p in ("TRAIN","VALIDATION","TEST")]
        rows.append(f"| {name} | {h*5}m | {vals[0]} | {vals[1]} | {vals[2]} |")
    rows += ["","*Frequency is normalized to 20 observed weekday trading dates in each period; it is a historical average, not a daily guarantee. Different strategies can fire simultaneously; portfolio totals require de-duplication across families.",
      "## Interpretation","",
      "- Compare validation and test together; high WR with tiny n is not actionable.",
      "- All variants reuse the same price history and are subject to multiple-testing bias.",
      "- Results are not independent of prior exploratory use of this historical dataset.",
      "- No model was deployed and no trade was executed.",""]
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text("\n".join(rows),encoding="utf-8")
    print(f"Wrote {a.out}; raw events={len(records):,}; M5 bars={sum(map(len,segments)):,}; splits={d1}/{d2}")

if __name__=="__main__": main()
