#!/usr/bin/env python3
"""HYD-CAND-008 frozen market-situation profile discovery. Research only."""
from __future__ import annotations
import argparse, csv, math, statistics
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from reproduce_m5_bb_williams_adx import Bar, make_m5, indicators, PAYOUT, wilson_interval

D1=datetime(2025,9,17,tzinfo=timezone.utc)
D2=datetime(2026,4,14,tzinfo=timezone.utc)
H=6  # 30-minute expiry; entry next M5 open, settle close of sixth subsequent bar

def read_m1(path):
    rows={}
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        rd=csv.DictReader(f)
        fields=rd.fieldnames or []
        tc="timestamp" if "timestamp" in fields else "datetime_utc" if "datetime_utc" in fields else "datetime"
        for r in rd:
            raw=r[tc].strip()
            ts=datetime.fromtimestamp(int(float(raw))/1000,tz=timezone.utc) if tc=="timestamp" else datetime.fromisoformat(raw.replace("Z","+00:00"))
            if ts.tzinfo is None: ts=ts.replace(tzinfo=timezone.utc)
            ts=ts.astimezone(timezone.utc)
            o,hi,lo,c=(float(r[k]) for k in ("open","high","low","close"))
            if all(math.isfinite(x) and x>0 for x in (o,hi,lo,c)) and hi>=max(o,lo,c) and lo<=min(o,c):
                rows[ts]=Bar(ts,o,hi,lo,c)
    return [rows[t] for t in sorted(rows)]

def ema(vals,n):
    out=[None]*len(vals)
    if len(vals)<n:return out
    state=sum(vals[:n])/n; out[n-1]=state; a=2/(n+1)
    for i in range(n,len(vals)):
        state=a*vals[i]+(1-a)*state; out[i]=state
    return out

def prior_week_lows(segments):
    wk=defaultdict(list)
    for seg in segments:
        for b in seg:
            iso=b.timestamp.isocalendar(); wk[(iso.year,iso.week)].append(b.low)
    keys=sorted(wk); prev={}
    for j,k in enumerate(keys):
        if j: prev[k]=min(wk[keys[j-1]])
    return [[prev.get((b.timestamp.isocalendar().year,b.timestamp.isocalendar().week)) for b in seg] for seg in segments]

def features(bars):
    closes=[b.close for b in bars]; e20=ema(closes,20); e50=ema(closes,50); ind=indicators(bars)
    tr=[]
    for i,b in enumerate(bars):
        tr.append(b.high-b.low if i==0 else max(b.high-b.low,abs(b.high-bars[i-1].close),abs(b.low-bars[i-1].close)))
    atr=[None]*len(bars); state=None
    for i,x in enumerate(tr):
        if i==13: state=sum(tr[:14])/14
        elif i>13: state=(13*state+x)/14
        if i>=13: atr[i]=state
    out=[]
    for i,b in enumerate(bars):
        a=atr[i]; rng=b.high-b.low
        hist=[atr[j]/bars[j].close for j in range(max(0,i-120),i) if atr[j] is not None]
        rank=(sum(x<=a/b.close for x in hist)/len(hist)) if a and hist and len(hist)>=60 else None
        bias=None if e20[i] is None or e50[i] is None else "UP" if e20[i]>e50[i] else "DOWN" if e20[i]<e50[i] else "FLAT"
        adx=ind[i]["adx"]
        adx_band="LOW(<20)" if adx is not None and adx<20 else "MID(20-30)" if adx is not None and adx<30 else "HIGH(>=30)" if adx is not None else None
        vol="LOW(<=33%)" if rank is not None and rank<=1/3 else "MID(33-67%)" if rank is not None and rank<=2/3 else "HIGH(>67%)" if rank is not None else None
        ret6=None if i<6 or not a else (b.close-bars[i-6].close)/a
        mom="DOWN(<-1 ATR)" if ret6 is not None and ret6 < -1 else "FLAT(-1..1 ATR)" if ret6 is not None and ret6<=1 else "UP(>1 ATR)" if ret6 is not None else None
        out.append({"bias":bias,"adx_band":adx_band,"vol_band":vol,"atr_pct_rank":rank,
          "return6_atr":ret6,"mom6_band":mom,"ema_gap_atr":None if not a or e20[i] is None or e50[i] is None else (e20[i]-e50[i])/a,
          "adx":adx,"range_atr":None if not a else rng/a,
          "body_range":None if not rng else abs(b.close-b.open)/rng,
          "close_location":None if not rng else (b.close-b.low)/rng})
    return out

def period_for(signal,settle):
    if signal<D1:return "TRAIN" if settle<D1 else None
    if signal<D2:return "VALIDATION" if settle<D2 else None
    return "TEST"

def outcome(bars,i):
    delta=bars[i+H].close-bars[i+1].open
    return "D" if abs(delta)<1e-12 else "W" if delta<0 else "L" # candidate is PUT

def stat(xs):
    w=xs.count("W"); l=xs.count("L"); d=xs.count("D"); dec=w+l
    return len(xs),w,l,d,(100*w/dec if dec else None),wilson_interval(w,dec),w*PAYOUT-l

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--data",type=Path,required=True); ap.add_argument("--out",type=Path,required=True); a=ap.parse_args()
    m1=read_m1(a.data); segments=make_m5(m1); levels=prior_week_lows(segments)
    events=[]; backgrounds=[]; purged=0
    for sid,bars in enumerate(segments):
        f=features(bars); lows=levels[sid]
        for i in range(60,len(bars)-13):
            if bars[i+1].timestamp-bars[i].timestamp!=timedelta(minutes=5): continue
            settle=bars[i+H].timestamp+timedelta(minutes=5)
            p=period_for(bars[i].timestamp,settle)
            if p is None:
                if bars[i].timestamp<D2 and settle>=D1 and bars[i].timestamp<D1 or D1<=bars[i].timestamp<D2 and settle>=D2: purged+=1
                continue
            b=bars[i]; level=lows[i]
            if level is None: continue
            delta=bars[i+H].close-bars[i+1].open
            base={"time":b.timestamp,"period":p,"state":f[i],"outcome":"D" if abs(delta)<1e-12 else "DOWN" if delta<0 else "UP"}
            backgrounds.append(base)
            # Original CALL event: sweep below previous completed UTC week's low,
            # bullish signal candle closes back above that level. Candidate is exact inverse PUT.
            if b.low<level and b.close>level and b.close>b.open:
                oc=outcome(bars,i)
                events.append({**base,"outcome":oc,"segment":sid,"index":i})
    # Reproduce frozen original candidate non-overlap schedule: h=6, reset by segment and split.
    accepted=[]
    for sid in range(len(segments)):
        for p in ("TRAIN","VALIDATION","TEST"):
            rows=sorted((x for x in events if x["segment"]==sid and x["period"]==p),key=lambda x:x["index"])
            nxt=-1
            for x in rows:
                if x["index"]>=nxt:
                    accepted.append(x); nxt=x["index"]+H
    expected={"TRAIN":(227,130,97,0),"VALIDATION":(45,25,20,0),"TEST":(76,47,29,0)}
    actual={}
    for p in expected:
        xs=[x for x in accepted if x["period"]==p]
        actual[p]=(len(xs),sum(x["outcome"]=="W" for x in xs),sum(x["outcome"]=="L" for x in xs),sum(x["outcome"]=="D" for x in xs))
    if actual!=expected:
        raise SystemExit(f"FROZEN COHORT MISMATCH: expected={expected}; actual={actual}; raw_events={len(events)}. Stop before profile interpretation.")
    print(f"Frozen cohort reproduced exactly: {actual}")
    all_signal_times={x["time"] for x in events}
    bg=[x for x in backgrounds if x["time"] not in all_signal_times and x["outcome"] in ("UP","DOWN")]
    lines=["# HYD-CAND-008 — previous-week-low sweep/reclaim inverse PUT: market-situation profile","",
      f"Source: Dukascopy EUR/USD M1 BID; M1={len(m1):,}; complete M5={sum(map(len,segments)):,}; segments={len(segments)}.",
      f"Coverage: {m1[0].timestamp.isoformat()} — {m1[-1].timestamp.isoformat()}.",
      "Frozen candidate: closed bullish M5 candle sweeps below the previous completed UTC ISO week's low and closes back above it; exact-event inverse PUT. Entry next M5 open; expiry close of sixth subsequent M5 candle (30m). Non-overlap: one event per segment/split while prior 30m trade active.",
      f"Frozen splits: TRAIN < {D1.date()}; VALIDATION {D1.date()} through {D2.date()-timedelta(days=1)}; TEST >= {D2.date()}. Boundary-crossing events purged={purged}.",
      "Causal pre-entry features at signal close: EMA20/50 bias; ADX14; ATR14/close percentile vs prior 120 completed M5 bars (signal candle excluded); prior 6-bar return/ATR; signal candle body/range and close location.",
      "92% payout scenario only (+0.92/-1/0); break-even decisive WR 52.083%. Dukascopy BID is a historical proxy, not Pocket Option executable pricing. TEST has prior exposure and is not pristine.","",
      "## Frozen candidate baseline","","| Split | n | W/L/D | WR | Wilson 95% CI | Net u |","|---|---:|---|---:|---|---:|"]
    for p in ("TRAIN","VALIDATION","TEST"):
        xs=[x["outcome"] for x in accepted if x["period"]==p]; n,w,l,d,wr,ci,net=stat(xs)
        lines.append(f"| {p} | {n} | {w}/{l}/{d} | {wr:.2f}% | [{ci[0]:.2f},{ci[1]:.2f}]% | {net:+.2f} |")
    dims=[("EMA20/EMA50 bias","bias"),("ADX strength","adx_band"),("Prior 120 M5 ATR percentile","vol_band"),("Prior 6-bar return / ATR","mom6_band")]
    for title,key in dims:
        lines += ["",f"## Situation map: {title}","","| Split | Bin | Candidate n | W/L/D | WR | Background n | Background PUT rate | Lift pp | Net u |","|---|---|---:|---|---:|---:|---:|---:|---:|"]
        for p in ("TRAIN","VALIDATION","TEST"):
            bins=sorted({x["state"][key] for x in accepted if x["period"]==p and x["state"].get(key) is not None})
            for val in bins:
                s=[x for x in accepted if x["period"]==p and x["state"].get(key)==val]
                b=[x for x in bg if x["period"]==p and x["state"].get(key)==val]
                n,w,l,d,wr,ci,net=stat([x["outcome"] for x in s])
                br=100*sum(x["outcome"]=="DOWN" for x in b)/len(b) if b else None
                if n>=4:
                    lines.append(f"| {p} | {val} | {n} | {w}/{l}/{d} | {wr:.2f}% | {len(b)} | {br:.2f}% | {wr-br:+.2f} | {net:+.2f} |" if br is not None else f"| {p} | {val} | {n} | {w}/{l}/{d} | {wr:.2f}% | {len(b)} | n/a | n/a | {net:+.2f} |")
    lines += ["","## Descriptive feature medians by outcome","","| Split | Feature | Winners median | Losers median |","|---|---|---:|---:|"]
    for p in ("TRAIN","VALIDATION","TEST"):
        xs=[x for x in accepted if x["period"]==p]
        for key in ("atr_pct_rank","return6_atr","ema_gap_atr","adx","range_atr","body_range","close_location"):
            w=[x["state"][key] for x in xs if x["outcome"]=="W" and x["state"].get(key) is not None]
            l=[x["state"][key] for x in xs if x["outcome"]=="L" and x["state"].get(key) is not None]
            if w and l: lines.append(f"| {p} | {key} | {statistics.median(w):.5g} | {statistics.median(l):.5g} |")
    lines += ["","## Guardrails","","- This is a descriptive profile map, not a causal filter or confirmation. Candidate VALIDATION is only 45 trades; subgroup estimates will be very uncertain.",
      "- Background uses all eligible M5 bars under the same 30m outcome convention, excluding all raw candidate trigger timestamps. It is overlapping and descriptive, not a matched non-overlapping control-trade schedule.",
      "- No TEST-based threshold selection, month filters, or parameter tuning. Any promising profile must be frozen and tested on fresh prospective data.",
      "- If the exact frozen cohort fails to reproduce, stop; do not interpret profile results.",""]
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text("\n".join(lines),encoding="utf-8")
    print(f"Completed: M1={len(m1):,}; M5={sum(map(len,segments)):,}; raw candidate events={len(events):,}; accepted={len(accepted)}; report={a.out}")
if __name__=="__main__": main()
