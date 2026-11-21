#!/usr/bin/env python3
"""Expanded, predeclared EURUSD M5 strategy discovery. Research only."""
from __future__ import annotations
import argparse, csv, math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from long_history_validation import Bar, make_m5

PAYOUT=0.92
HORIZONS=(1,2,3,4,6,12)

def read_m1(path):
    rows={}
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        rd=csv.DictReader(f)
        tc="timestamp" if "timestamp" in (rd.fieldnames or []) else "datetime_utc" if "datetime_utc" in (rd.fieldnames or []) else "datetime"
        if not {"open","high","low","close",tc}.issubset(rd.fieldnames or []): raise ValueError(f"Bad CSV header: {rd.fieldnames}")
        for r in rd:
            raw=r[tc].strip()
            ts=datetime.fromtimestamp(int(float(raw))/1000,tz=timezone.utc) if tc=="timestamp" else datetime.fromisoformat(raw.replace("Z","+00:00"))
            if ts.tzinfo is None: ts=ts.replace(tzinfo=timezone.utc)
            ts=ts.astimezone(timezone.utc)
            o,h,l,c=(float(r[k]) for k in ("open","high","low","close"))
            if all(math.isfinite(x) and x>0 for x in (o,h,l,c)) and h>=max(o,l,c) and l<=min(o,c): rows[ts]=Bar(ts,o,h,l,c)
    return [rows[t] for t in sorted(rows)]

def ema(values,n):
    out=[None]*len(values)
    if len(values)<n:return out
    seed=sum(values[:n])/n; out[n-1]=seed; alpha=2/(n+1); prev=seed
    for i in range(n,len(values)):
        prev=alpha*values[i]+(1-alpha)*prev; out[i]=prev
    return out

def rsi(values,n=14):
    out=[None]*len(values)
    if len(values)<=n:return out
    gains=[max(values[i]-values[i-1],0) for i in range(1,len(values))]
    losses=[max(values[i-1]-values[i],0) for i in range(1,len(values))]
    ag=sum(gains[:n])/n; al=sum(losses[:n])/n
    out[n]=100 if al==0 else 100-100/(1+ag/al)
    for i in range(n+1,len(values)):
        ag=((n-1)*ag+gains[i-1])/n; al=((n-1)*al+losses[i-1])/n
        out[i]=100 if al==0 else 100-100/(1+ag/al)
    return out

def rolling_mean(x,i,n):
    if i+1<n:return None
    return sum(x[i-n+1:i+1])/n

def rolling_std(x,i,n):
    m=rolling_mean(x,i,n)
    return None if m is None else math.sqrt(sum((v-m)**2 for v in x[i-n+1:i+1])/n)

def make_events(bars):
    o=[b.open for b in bars]; c=[b.close for b in bars]; hi=[b.high for b in bars]; lo=[b.low for b in bars]
    events=defaultdict(list)
    rv=rsi(c,14); e20=ema(c,20); e50=ema(c,50); ef=ema(c,12); es=ema(c,26)
    macd=[None if ef[i] is None or es[i] is None else ef[i]-es[i] for i in range(len(c))]
    signal=ema([0 if x is None else x for x in macd],9)
    tr=[hi[0]-lo[0]]
    for i in range(1,len(bars)): tr.append(max(hi[i]-lo[i],abs(hi[i]-c[i-1]),abs(lo[i]-c[i-1])))
    atr=ema(tr,14)
    for i in range(60,len(bars)-13):
        # RSI extreme + close reversal, thresholds fixed before evaluation
        if rv[i] is not None:
            if rv[i]<=25 and c[i]>o[i]: events["RSI14_25_REV_CALL"].append((i,"CALL"))
            if rv[i]>=75 and c[i]<o[i]: events["RSI14_75_REV_PUT"].append((i,"PUT"))
            if rv[i]<=30 and c[i]>o[i]: events["RSI14_30_REV_CALL"].append((i,"CALL"))
            if rv[i]>=70 and c[i]<o[i]: events["RSI14_70_REV_PUT"].append((i,"PUT"))
        # Stochastic %K(14), smoothed %D(3), cross back from extremes
        ll=min(lo[i-13:i+1]); hh=max(hi[i-13:i+1])
        k=50 if hh==ll else 100*(c[i]-ll)/(hh-ll)
        prev_ll=min(lo[i-14:i]); prev_hh=max(hi[i-14:i])
        pk=50 if prev_hh==prev_ll else 100*(c[i-1]-prev_ll)/(prev_hh-prev_ll)
        if pk<20 and k>=20 and c[i]>o[i]: events["STOCH14_EXIT20_CALL"].append((i,"CALL"))
        if pk>80 and k<=80 and c[i]<o[i]: events["STOCH14_EXIT80_PUT"].append((i,"PUT"))
        # Bollinger re-entry after prior close outside band
        for n,mult in ((20,1.5),(20,2.0)):
            mid=rolling_mean(c,i,n); sd=rolling_std(c,i,n)
            pm=rolling_mean(c,i-1,n); ps=rolling_std(c,i-1,n)
            if sd and ps:
                if c[i-1]<pm-mult*ps and c[i]>mid-mult*sd and c[i]>o[i]:
                    events[f"BB{n}_{mult}_REENTRY_CALL"].append((i,"CALL"))
                if c[i-1]>pm+mult*ps and c[i]<mid+mult*sd and c[i]<o[i]:
                    events[f"BB{n}_{mult}_REENTRY_PUT"].append((i,"PUT"))
        # EMA20 pullback in EMA20/50 aligned trend; rejection close
        if e20[i] and e50[i] and e20[i-1]:
            if e20[i]>e50[i] and lo[i]<=e20[i] and c[i]>e20[i] and c[i]>o[i]:
                events["EMA20_PULLBACK_TREND_CALL"].append((i,"CALL"))
            if e20[i]<e50[i] and hi[i]>=e20[i] and c[i]<e20[i] and c[i]<o[i]:
                events["EMA20_PULLBACK_TREND_PUT"].append((i,"PUT"))
        # MACD line/signal cross, fixed 12/26/9
        if macd[i] is not None and signal[i] is not None and macd[i-1] is not None and signal[i-1] is not None:
            if macd[i-1]<=signal[i-1] and macd[i]>signal[i] and c[i]>o[i]: events["MACD129_CROSS_CALL"].append((i,"CALL"))
            if macd[i-1]>=signal[i-1] and macd[i]<signal[i] and c[i]<o[i]: events["MACD129_CROSS_PUT"].append((i,"PUT"))
        # Inside bar breakout: prior candle inside its mother; close breaks mother range
        if hi[i-1]<hi[i-2] and lo[i-1]>lo[i-2]:
            if c[i]>hi[i-2] and c[i]>o[i]: events["INSIDE_BAR_BREAK_CALL"].append((i,"CALL"))
            if c[i]<lo[i-2] and c[i]<o[i]: events["INSIDE_BAR_BREAK_PUT"].append((i,"PUT"))
        # ATR expansion: current ATR > 1.25x prior ATR, directional body continuation
        if atr[i] and atr[i-1] and atr[i]>1.25*atr[i-1]:
            if c[i]>o[i] and c[i]-o[i]>=0.5*atr[i]: events["ATR_EXPANSION_CALL"].append((i,"CALL"))
            if c[i]<o[i] and o[i]-c[i]>=0.5*atr[i]: events["ATR_EXPANSION_PUT"].append((i,"PUT"))
    return events

def outcome(bars,i,side,h):
    d=bars[i+h].close-bars[i+1].open
    return "D" if abs(d)<1e-12 else "W" if (d>0)==(side=="CALL") else "L"

def wilson(w,n):
    if not n:return None
    z=1.959963984540054; p=w/n; den=1+z*z/n
    center=(p+z*z/(2*n))/den; half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return 100*(center-half),100*(center+half)

def stats(xs):
    w=xs.count("W"); l=xs.count("L"); d=xs.count("D"); n=w+l+d; dec=w+l
    net=w*PAYOUT-l; eq=peak=dd=0; streak=mx=0
    for x in xs:
        if x=="W":eq+=PAYOUT;streak=0
        elif x=="L":eq-=1;streak+=1;mx=max(mx,streak)
        peak=max(peak,eq);dd=max(dd,peak-eq)
    return n,w,l,d,(100*w/dec if dec else None),wilson(w,dec),net,dd,mx

def main():
    p=argparse.ArgumentParser();p.add_argument("--data",type=Path,required=True);p.add_argument("--out",type=Path,required=True);a=p.parse_args()
    m1=read_m1(a.data); segments=make_m5(m1)
    all_days=sorted({b.timestamp.date() for s in segments for b in s})
    d1=all_days[int(.60*len(all_days))];d2=all_days[int(.80*len(all_days))]
    raw=defaultdict(list); accepted=defaultdict(list)
    for sid,bars in enumerate(segments):
        ev=make_events(bars)
        for name,items in ev.items():
            for h in HORIZONS:
                for i,side in items:
                    if i+h>=len(bars):continue
                    start=bars[i].timestamp.date(); settle=(bars[i+h].timestamp.replace(minute=0,second=0,microsecond=0))
                    # settlement is at close of bar i+h (5 minutes after its open)
                    settle_day=(bars[i+h].timestamp.date())
                    period="TRAIN" if start<d1 else "VALIDATION" if start<d2 else "TEST"
                    if (period=="TRAIN" and settle_day>=d1) or (period=="VALIDATION" and settle_day>=d2):continue
                    raw[(name,h,period)].append((sid,i,side,outcome(bars,i,side,h)))
    # Enforce one active position per strategy/expiry/segment; split-specific.
    for key,rows in raw.items():
        nxt=-1
        for r in sorted(rows,key=lambda x:(x[0],x[1])):
            if r[0]!=getattr(main,"_last_sid",-999): pass
            # Per segment non-overlap; maintain next index separately.
        byseg=defaultdict(list)
        for r in rows:byseg[r[0]].append(r)
        for sid,rs in byseg.items():
            nxt=-1
            for r in sorted(rs,key=lambda x:x[1]):
                if r[1]>=nxt:accepted[key].append(r);nxt=r[1]+key[1]
    lines=["# Expanded EURUSD M5 strategy discovery","",
      f"Source: Dukascopy EURUSD M1 BID; {len(m1):,} M1 rows; {sum(map(len,segments)):,} M5 bars; {len(segments)} gap-separated segments.",
      f"Coverage: {m1[0].timestamp.isoformat()} — {m1[-1].timestamp.isoformat()}.",
      f"Chronological date split: TRAIN < {d1}; VALIDATION {d1}–{d2}; TEST >= {d2}.",
      "Predeclared families: RSI(14) reversal; Stochastic(14) extreme exit; Bollinger(20,1.5/2.0) re-entry; EMA20 pullback with EMA50 trend; MACD(12,26,9) cross; inside-bar mother-range breakout; ATR(14) expansion >1.25x.",
      "All signals use closed M5 candles only; entry next M5 open; expiry at close of the Nth subsequent M5 bar. Non-overlap enforced within each strategy/expiry/continuous segment.",
      "Expiries 5/10/15/20/30/60m. Payout assumed 92%: WIN +0.92u, LOSS -1u, DRAW 0u; break-even decisive WR 52.0833%.",
      "No parameter optimization, no lookahead by design. Dukascopy BID is not Pocket Option executable quote; spread, latency and variable payout are not modeled.",
      "Exploratory multi-family screen; multiple-testing bias applies. TEST ranking is not confirmation. Candidates must repeat in independent analog periods and prospective platform data.","",
      "| Strategy | Expiry | Split | n | W/L/D | Decisive WR | Wilson 95% CI | Net u | Max DD u | Max loss streak | Raw signals |",
      "|---|---:|---|---:|---|---:|---|---:|---:|---:|---:|"]
    for key in sorted(accepted):
        name,h,period=key; rs=accepted[key]; s=stats([r[3] for r in rs]); ci=s[5]
        wr="n/a" if s[4] is None else f"{s[4]:.2f}%"; ci_txt="n/a" if ci is None else f"[{ci[0]:.2f},{ci[1]:.2f}]%"
        lines.append(f"| {name} | {h*5}m | {period} | {s[0]} | {s[1]}/{s[2]}/{s[3]} | {wr} | {ci_txt} | {s[6]:+.2f} | {s[7]:.2f} | {s[8]} | {len(raw[key])} |")
    lines += ["","## Screening rule","",
      "- Priority: VALIDATION decisive WR >=57% with meaningful sample, positive net and consistency across multiple periods; 56.0–56.9% is borderline only.",
      "- TEST is reported for chronological context, not used to tune or promote a candidate.",
      "- Wilson intervals assume independent outcomes and can be optimistic under serial dependence.",
      "- A strong row is only a candidate. Next step is to formalize its own market situation and search/test analogs; no catalog promotion from this screen.",""]
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text("\n".join(lines),encoding="utf-8")
    print(f"Expanded screen complete: rows={len(m1):,}; M5={sum(map(len,segments)):,}; event groups={len(raw):,}; output={a.out}")
if __name__=="__main__":main()
