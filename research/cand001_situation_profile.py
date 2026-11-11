#!/usr/bin/env python3
"""HYD-CAND-001 market-situation profile discovery. Exploratory; no filters promoted."""
from __future__ import annotations
import argparse, csv, math, statistics
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from reproduce_m5_bb_williams_adx import Bar, make_m5, indicators, PAYOUT, wilson_interval

D1 = datetime(2025, 9, 17, tzinfo=timezone.utc)
D2 = datetime(2026, 4, 14, tzinfo=timezone.utc)
H = 1  # one subsequent M5 candle; 5-minute expiry

def read_m1(path):
    rows={}
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        rd=csv.DictReader(f)
        tc="timestamp" if "timestamp" in (rd.fieldnames or []) else "datetime_utc" if "datetime_utc" in (rd.fieldnames or []) else "datetime"
        for r in rd:
            raw=r[tc].strip()
            ts=datetime.fromtimestamp(int(float(raw))/1000,tz=timezone.utc) if tc=="timestamp" else datetime.fromisoformat(raw.replace("Z","+00:00"))
            if ts.tzinfo is None: ts=ts.replace(tzinfo=timezone.utc)
            ts=ts.astimezone(timezone.utc)
            o,hi,lo,c=(float(r[k]) for k in ("open","high","low","close"))
            if all(math.isfinite(x) and x>0 for x in (o,hi,lo,c)) and hi>=max(o,lo,c) and lo<=min(o,c):
                rows[ts]=Bar(ts,o,hi,lo,c)
    return [rows[t] for t in sorted(rows)]

def rsi_series(closes,n=14):
    out=[None]*len(closes)
    if len(closes)<=n:return out
    gains=[max(closes[i]-closes[i-1],0) for i in range(1,len(closes))]
    losses=[max(closes[i-1]-closes[i],0) for i in range(1,len(closes))]
    ag=sum(gains[:n])/n; al=sum(losses[:n])/n
    out[n]=100.0 if al==0 else 100-100/(1+ag/al)
    for i in range(n+1,len(closes)):
        ag=((n-1)*ag+gains[i-1])/n; al=((n-1)*al+losses[i-1])/n
        out[i]=100.0 if al==0 else 100-100/(1+ag/al)
    return out

def ema(values,n):
    out=[None]*len(values)
    if len(values)<n:return out
    state=sum(values[:n])/n; out[n-1]=state; alpha=2/(n+1)
    for i in range(n,len(values)):
        state=alpha*values[i]+(1-alpha)*state; out[i]=state
    return out

def percentile_rank(history,x):
    return sum(v<=x for v in history)/len(history) if history else None

def make_feature_rows(bars):
    closes=[b.close for b in bars]
    rsi=rsi_series(closes); e20=ema(closes,20); e50=ema(closes,50)
    ind=indicators(bars)
    tr=[]
    for i,b in enumerate(bars):
        tr.append(b.high-b.low if i==0 else max(b.high-b.low,abs(b.high-bars[i-1].close),abs(b.low-bars[i-1].close)))
    atr=[]
    state=None
    for i,x in enumerate(tr):
        if i==13: state=sum(tr[:14])/14
        elif i>13: state=(state*13+x)/14
        atr.append(state if i>=13 else None)
    feats=[]
    for i,b in enumerate(bars):
        a=atr[i]; rng=b.high-b.low
        ret=lambda k: None if i<k or not a else (b.close-bars[i-k].close)/a
        hist=[v/bars[j].close for j,v in enumerate(atr[:i]) if v is not None and bars[j].close]
        rank=percentile_rank(hist,a/b.close) if a is not None and len(hist)>=60 else None
        bias="UP" if e20[i] is not None and e50[i] is not None and e20[i]>e50[i] else "DOWN" if e20[i] is not None and e50[i] is not None and e20[i]<e50[i] else "FLAT"
        adx=ind[i]["adx"]
        adx_band="LOW(<20)" if adx is not None and adx<20 else "MID(20-30)" if adx is not None and adx<30 else "HIGH(>=30)" if adx is not None else None
        vol_band="LOW(<=33%)" if rank is not None and rank<=1/3 else "MID(33-67%)" if rank is not None and rank<=2/3 else "HIGH(>67%)" if rank is not None else None
        r=rsi[i]
        rsi_band="70-75" if r is not None and r<75 else "75-80" if r is not None and r<80 else ">=80" if r is not None else None
        mom=ret(6)
        mom_band="DOWN(<-1 ATR)" if mom is not None and mom < -1 else "FLAT(-1..1 ATR)" if mom is not None and mom<=1 else "UP(>1 ATR)" if mom is not None else None
        feats.append({
          "rsi14":r,"adx14":adx,"atr_pct_rank_lookback":rank,
          "ema20_50_atr":None if a is None or not a or e20[i] is None or e50[i] is None else (e20[i]-e50[i])/a,
          "return1_atr":ret(1),"return3_atr":ret(3),"return6_atr":mom,"return12_atr":ret(12),
          "body_range":None if not rng else abs(b.close-b.open)/rng,
          "upper_wick_range":None if not rng else (b.high-max(b.open,b.close))/rng,
          "lower_wick_range":None if not rng else (min(b.open,b.close)-b.low)/rng,
          "range_atr":None if not a or not rng else rng/a,
          "close_location":None if not rng else (b.close-b.low)/rng,
          "bias":bias,"adx_band":adx_band,"vol_band":vol_band,"rsi_band":rsi_band,"mom6_band":mom_band
        })
    return feats

def period_for(signal_time,settle_time):
    if signal_time<D1: return None if settle_time>=D1 else "TRAIN"
    if signal_time<D2: return None if settle_time>=D2 else "VALIDATION"
    return "TEST"

def stat(rows):
    w=sum(x["outcome"]=="W" for x in rows); l=sum(x["outcome"]=="L" for x in rows); d=sum(x["outcome"]=="D" for x in rows)
    dec=w+l; wr=100*w/dec if dec else None
    ci=wilson_interval(w,dec)
    net=w*PAYOUT-l
    return len(rows),w,l,d,wr,ci,net

def fmt(rows):
    n,w,l,d,wr,ci,net=stat(rows)
    return f"{n} | {w}/{l}/{d} | {wr:.2f}%" if wr is not None else f"{n} | {w}/{l}/{d} | n/a"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True); ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    m1=read_m1(a.data); segments=make_m5(m1)
    events=[]; backgrounds=[]; purged=0
    for sid,bars in enumerate(segments):
        feats=make_feature_rows(bars); rs=[x["rsi14"] for x in feats]
        for i in range(1,len(bars)-1):
            if bars[i+1].timestamp-bars[i].timestamp!=timedelta(minutes=5): continue
            settle=bars[i+1].timestamp+timedelta(minutes=5)
            period=period_for(bars[i].timestamp,settle)
            if period is None: purged+=1; continue
            delta=bars[i+1].close-bars[i+1].open
            base={"time":bars[i].timestamp,"period":period,"state":feats[i],"outcome":"D" if abs(delta)<1e-12 else "UP" if delta>0 else "DOWN"}
            backgrounds.append(base)
            if rs[i] is None or rs[i]<70 or bars[i].close>=bars[i].open: continue
            outcome="D" if abs(delta)<1e-12 else "W" if delta<0 else "L"
            events.append({**base,"outcome":outcome,"segment":sid,"index":i})
    # Exact candidate event rule, one active 5m trade; trigger candles cannot overlap by construction.
    signal_times={x["time"] for x in events}
    bg=[x for x in backgrounds if x["time"] not in signal_times]
    lines=[
      "# HYD-CAND-001 — RSI14>=70 bearish M5 candle: market-situation profile discovery","",
      f"Source: Dukascopy EUR/USD M1 BID; M1 rows={len(m1):,}; complete M5 bars={sum(map(len,segments)):,}; gap-separated segments={len(segments)}.",
      f"Coverage: {m1[0].timestamp.isoformat()} — {m1[-1].timestamp.isoformat()}.",
      "Frozen candidate: closed M5 RSI(14) >= 70 AND bearish candle (close < open) => PUT; entry next M5 open; settlement at close of that entry M5 candle (5m). RSI uses Wilder smoothing, seeded on the first 14 close-to-close changes.",
      f"Frozen chronological boundaries: TRAIN < {D1.date()}; VALIDATION {D1.date()} through {D2.date()-timedelta(days=1)}; TEST >= {D2.date()}. Boundary-crossing outcomes purged ({purged}).",
      "Payout scenario only: 92%, WIN +0.92u / LOSS -1u / DRAW 0u; break-even decisive WR 52.0833%. Actual platform payout/quotes not modeled.",
      "All profile variables are measured at signal-candle close, before entry. No threshold search or filter promotion. Test period has been previously inspected and is not pristine.",
      "Background = every eligible continuous M5 bar under the same next-bar outcome convention, excluding candidate signal timestamps. It is a descriptive, serially dependent comparison, not an independent sample.","",
      "## Candidate outcomes by chronological split","",
      "| Split | n | W/L/D | Decisive WR | Wilson 95% CI | Net (92% scenario) |",
      "|---|---:|---:|---:|---:|---:|"]
    for p in ("TRAIN","VALIDATION","TEST"):
        chosen=[x for x in events if x["period"]==p]; n,w,l,d,wr,ci,net=stat(chosen)
        lines.append(f"| {p} | {n} | {w}/{l}/{d} | {wr:.2f}% | [{ci[0]:.2f},{ci[1]:.2f}]% | {net:+.2f}u |" if ci else f"| {p} | {n} | {w}/{l}/{d} | n/a | n/a | {net:+.2f}u |")
    dims=[("EMA20/EMA50 bias","bias"),("ADX strength","adx_band"),("Prior 120-bar ATR percentile","vol_band"),("Signal RSI severity","rsi_band"),("Prior 6-bar return / ATR","mom6_band")]
    for title,key in dims:
        lines += ["",f"## One-dimensional situation map: {title}","",
          "| Split | Situation bin | Candidate n | W/L/D | Candidate WR | Matched background n | Background PUT-equivalent rate | Lift (pp) | Net u |",
          "|---|---|---:|---|---:|---:|---:|---:|---:|"]
        for p in ("TRAIN","VALIDATION","TEST"):
            vals=sorted({x["state"][key] for x in events if x["period"]==p and x["state"].get(key) is not None})
            for val in vals:
                s=[x for x in events if x["period"]==p and x["state"].get(key)==val]
                b=[x for x in bg if x["period"]==p and x["state"].get(key)==val and x["outcome"] in ("UP","DOWN")]
                n,w,l,d,wr,ci,net=stat(s)
                br=100*sum(x["outcome"]=="DOWN" for x in b)/len(b) if b else None
                lift=wr-br if wr is not None and br is not None else None
                if n>=5:
                    lines.append(f"| {p} | {val} | {n} | {w}/{l}/{d} | {wr:.2f}% | {len(b)} | {br:.2f}% | {lift:+.2f} | {net:+.2f} |" if lift is not None else f"| {p} | {val} | {n} | {w}/{l}/{d} | {wr:.2f}% | {len(b)} | n/a | n/a | {net:+.2f} |")
    lines += ["","## Predeclared two-factor situation combinations","",
      "Only combinations with at least 12 candidate events are shown; this is a descriptive minimum, not a significance threshold. The same bins are applied without refitting across splits.",
      "| Split | EMA bias × ATR percentile | n | W/L/D | WR | Background n | Background down rate | Lift pp | Net u |",
      "|---|---|---:|---|---:|---:|---:|---:|---:|"]
    for p in ("TRAIN","VALIDATION","TEST"):
        combos=sorted({(x["state"]["bias"],x["state"]["vol_band"]) for x in events if x["period"]==p and x["state"]["vol_band"]})
        for bias,vol in combos:
            s=[x for x in events if x["period"]==p and x["state"]["bias"]==bias and x["state"]["vol_band"]==vol]
            if len(s)<12: continue
            b=[x for x in bg if x["period"]==p and x["state"]["bias"]==bias and x["state"]["vol_band"]==vol and x["outcome"] in ("UP","DOWN")]
            n,w,l,d,wr,ci,net=stat(s); br=100*sum(x["outcome"]=="DOWN" for x in b)/len(b) if b else None
            lines.append(f"| {p} | {bias} × {vol} | {n} | {w}/{l}/{d} | {wr:.2f}% | {len(b)} | {br:.2f}% | {wr-br:+.2f} | {net:+.2f} |" if br is not None else f"| {p} | {bias} × {vol} | {n} | {w}/{l}/{d} | {wr:.2f}% | {len(b)} | n/a | n/a | {net:+.2f} |")
    lines += ["","## Winner / loser context medians (descriptive)","",
      "| Split | Feature | Winners median | Losers median |",
      "|---|---|---:|---:|"]
    cont=("rsi14","adx14","atr_pct_rank_lookback","ema20_50_atr","return1_atr","return3_atr","return6_atr","return12_atr","body_range","upper_wick_range","lower_wick_range","range_atr","close_location")
    for p in ("TRAIN","VALIDATION","TEST"):
        chosen=[x for x in events if x["period"]==p]
        for f in cont:
            w=[x["state"][f] for x in chosen if x["outcome"]=="W" and x["state"].get(f) is not None]
            l=[x["state"][f] for x in chosen if x["outcome"]=="L" and x["state"].get(f) is not None]
            if w and l: lines.append(f"| {p} | {f} | {statistics.median(w):.5g} | {statistics.median(l):.5g} |")
    lines += ["","## Guardrails and next decision","",
      "- These tables locate possible market-context associations; they do not establish causal filters or a confirmed situation.",
      "- The primary question is whether candidate performance differs from the matched background in the same pre-entry situation, not whether a small subgroup has an attractive raw WR.",
      "- No bin, interaction, session, or threshold may be selected from TEST. Any follow-up profile must be frozen on TRAIN and assessed on VALIDATION; subsequent confirmation requires genuinely fresh data.",
      "- The candidate's baseline result must reproduce the registry cohort. If it does not, stop and resolve the discrepancy before interpreting situation tables.",
      "- Dukascopy BID is not Pocket Option's exact quote stream; actual payout, spread, latency and platform execution remain unmodeled.",""]
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text("\n".join(lines),encoding="utf-8")
    print(f"Completed: M1={len(m1):,}; M5={sum(map(len,segments)):,}; candidate events={len(events):,}; report={a.out}")
if __name__=="__main__": main()
