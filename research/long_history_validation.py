#!/usr/bin/env python3
"""Long-history, frozen-parameter validation of the M5 BB/Williams/ADX setup."""
from __future__ import annotations
import argparse, csv, math, statistics
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

from reproduce_m5_bb_williams_adx import Bar, make_m5, indicators, PAYOUT, wilson_interval

def read_duka(path: Path) -> list[Bar]:
    rows={}
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        reader=csv.DictReader(f)
        required={"timestamp","open","high","low","close"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Unexpected Dukascopy CSV header: {reader.fieldnames}")
        for r in reader:
            raw=int(float(r["timestamp"]))
            ts=datetime.fromtimestamp(raw/1000,tz=timezone.utc)
            vals=[float(r[k]) for k in ("open","high","low","close")]
            o,h,l,c=vals
            if not all(math.isfinite(x) and x>0 for x in vals) or h<max(o,l,c) or l>min(o,c):
                continue
            rows[ts]=Bar(ts,o,h,l,c)
    return [rows[t] for t in sorted(rows)]

def make_events(segments, adx_min=15):
    events=[]
    for seg_id,bars in enumerate(segments):
        ind=indicators(bars)
        for i in range(1,len(bars)-5):
            prev,cur=ind[i-1],ind[i]
            keys=("upper","lower","willr")
            if any(prev[k] is None or cur[k] is None for k in keys) or cur["adx"] is None:
                continue
            if cur["adx"]<adx_min: continue
            call=(bars[i-1].close<prev["lower"] and bars[i].close>cur["lower"]
                  and prev["willr"]<=-80 and cur["willr"]>-80)
            put=(bars[i-1].close>prev["upper"] and bars[i].close<cur["upper"]
                 and prev["willr"]>=-20 and cur["willr"]<-20)
            if call or put:
                events.append({"signal_time":bars[i].timestamp,"segment":seg_id,
                               "direction":"CALL" if call else "PUT","bar_index":i})
    return events

def outcome(bars, i, direction, horizon):
    entry=bars[i+1].open
    exitp=bars[i+horizon].close
    delta=(exitp-entry)*(1 if direction=="CALL" else -1)
    return "DRAW" if abs(delta)<1e-12 else "WIN" if delta>0 else "LOSS"

def stats(trades):
    w=sum(t=="WIN" for t in trades); l=sum(t=="LOSS" for t in trades); d=sum(t=="DRAW" for t in trades)
    dec=w+l; wr=100*w/dec if dec else float("nan")
    net=w*PAYOUT-l
    gross_win=w*PAYOUT; gross_loss=l
    pf=gross_win/gross_loss if gross_loss else (float("inf") if gross_win else 0)
    eq=peak=maxdd=0.0; streak=cur=0; maxstreak=0
    for t in trades:
        eq += PAYOUT if t=="WIN" else -1 if t=="LOSS" else 0
        peak=max(peak,eq); maxdd=max(maxdd,peak-eq)
        cur=cur+1 if t=="LOSS" else 0; maxstreak=max(maxstreak,cur)
    ci=wilson_interval(w,dec)
    return w,l,d,wr,net,pf,maxdd,maxstreak,ci

def fmt_stats(trades):
    w,l,d,wr,net,pf,dd,streak,ci=stats(trades)
    ci_txt=f"[{ci[0]:.1f}, {ci[1]:.1f}]" if ci else "n/a"
    return f"{len(trades)} | {w}/{l}/{d} | {wr:.2f}% | {ci_txt} | {net:+.2f}u | {pf:.2f} | {dd:.2f}u | {streak}"


def m5_close_time(bar_open_time):
    """Return the actual settlement timestamp at the close of a UTC M5 bar."""
    return bar_open_time + timedelta(minutes=5)


def chronological_period(signal_time, settle_time, d1, d2):
    """Assign by signal day, purging any outcome that reaches the next split boundary."""
    signal_day = signal_time.date()
    settle_day = settle_time.date()
    if signal_day < d1:
        return None if settle_day >= d1 else "TRAIN"
    if signal_day < d2:
        return None if settle_day >= d2 else "VALIDATION"
    return "TEST"


def split_records(records, d1, d2):
    """Chronological split with a purge when a trade settles across a boundary."""
    result = {"TRAIN": [], "VALIDATION": [], "TEST": [], "ALL": list(records)}
    purged = {"TRAIN": 0, "VALIDATION": 0}
    for row in records:
        period = chronological_period(row["signal_time"], row["settle_time"], d1, d2)
        if period is None:
            split = "TRAIN" if row["signal_time"].date() < d1 else "VALIDATION"
            purged[split] += 1
            continue
        result[period].append(row)
    return result, purged


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--out",type=Path,default=Path("LONG_HISTORY_VALIDATION.md"))
    ap.add_argument("--adx-min",type=float,default=15)
    a=ap.parse_args()
    m1=read_duka(a.data); segments=make_m5(m1)
    events=make_events(segments,a.adx_min)
    days=sorted({e["signal_time"].date() for e in events})
    if len(days)<30: raise SystemExit("Insufficient history: fewer than 30 signal days.")
    d1=days[int(len(days)*0.60)]; d2=days[int(len(days)*0.80)]
    by_h={}
    by_h_splits={}
    purged_by_h={}
    for h in (1,2,3,4,5):
        records=[]
        for e in events:
            seg=segments[e["segment"]]; i=e["bar_index"]
            if i+h>=len(seg): continue
            records.append({**e,"horizon":h,"outcome":outcome(seg,i,e["direction"],h),
                            "settle_time":m5_close_time(seg[i+h].timestamp)})
        by_h[h]=records
        by_h_splits[h],purged_by_h[h]=split_records(records,d1,d2)
    total_m5=sum(map(len,segments))
    raw_signal_pct=100.0*len(events)/max(1,total_m5)
    raw_wait_pct=100.0-raw_signal_pct
    lines=[
      "# HYDRA — long-history frozen strategy validation","",
      f"Source: Dukascopy EURUSD M1 BID; raw M1 rows={len(m1):,}; complete UTC M5 bars={total_m5:,}; continuous segments={len(segments)}.",
      f"Coverage: {m1[0].timestamp.isoformat()} — {m1[-1].timestamp.isoformat()}.",
      f"Raw trigger events={len(events):,}; frequency={raw_signal_pct:.3f}% of all complete M5 bars; raw WAIT share={raw_wait_pct:.3f}% before any filter.",
      f"Frozen setup: Bollinger Bands(20,2) re-entry + Williams %R(14) cross; ADX(14) >= {a.adx_min:g}. Signal on closed M5; entry next M5 open.",
      "Expiries: 5/10/15/20/25 minutes; entry at next M5 open, settlement at close of the 1st/2nd/3rd/4th/5th M5 candle after signal.",
      "Payout accounting: WIN +0.92u, LOSS -1u, DRAW 0u. No parameter tuning or filters.",
      f"Chronological signal-day split: TRAIN before {d1}, VALIDATION {d1} through {d2-timedelta(days=1)}, TEST from {d2}.",
      "Each expiry is purged separately when its settlement date crosses the next split boundary.",
      "External Dukascopy BID feed, not Pocket Option's exact quote stream; spread/platform quote differences are not modeled. TEST is chronological but has been exposed to prior exploratory analysis; it is not independent confirmation.","",
      "## Split-boundary purge","",
      "| Expiry | TRAIN rows purged | VALIDATION rows purged |",
      "|---:|---:|---:|"
    ]
    for h in by_h:
        lines.append(f"| {h*5}m | {purged_by_h[h]['TRAIN']} | {purged_by_h[h]['VALIDATION']} |")
    lines += ["","## Overall results by expiry and period","",
      "| Expiry | Period | n | W/L/D | Decisive WR | Wilson 95% CI | Wins / all | Net | ROI | PF | Max DD | Max loss streak |",
      "|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for h in by_h:
      for period in ("TRAIN","VALIDATION","TEST","ALL"):
        chosen=by_h_splits[h][period]
        outcomes=[r["outcome"] for r in chosen]
        w,l,d,wr,net,pf,dd,streak,ci=stats(outcomes)
        ci_txt=f"[{ci[0]:.1f}, {ci[1]:.1f}]" if ci else "n/a"
        win_all=100*w/len(chosen) if chosen else float("nan")
        roi=100*net/len(chosen) if chosen else float("nan")
        lines.append(f"| {h*5}m | {period} | {len(chosen)} | {w}/{l}/{d} | {wr:.2f}% | {ci_txt} | {win_all:.2f}% | {net:+.2f}u | {roi:+.2f}% | {pf:.2f} | {dd:.2f}u | {streak} |")
    lines += ["","## Direction-separated results by split","",
      "| Expiry | Period | Direction | n | W/L/D | Decisive WR | Wilson 95% CI | Wins / all | Net | ROI | PF | Max DD | Max loss streak |",
      "|---:|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for h in by_h:
      for period in ("TRAIN","VALIDATION","TEST"):
        for side in ("CALL","PUT"):
          chosen=[r for r in by_h_splits[h][period] if r["direction"]==side]
          outcomes=[r["outcome"] for r in chosen]
          w,l,d,wr,net,pf,dd,streak,ci=stats(outcomes)
          ci_txt=f"[{ci[0]:.1f}, {ci[1]:.1f}]" if ci else "n/a"
          win_all=100*w/len(chosen) if chosen else float("nan")
          roi=100*net/len(chosen) if chosen else float("nan")
          lines.append(f"| {h*5}m | {period} | {side} | {len(chosen)} | {w}/{l}/{d} | {wr:.2f}% | {ci_txt} | {win_all:.2f}% | {net:+.2f}u | {roi:+.2f}% | {pf:.2f} | {dd:.2f}u | {streak} |")
    lines += ["","## Monthly 20-minute breakdown","",
      "| Month UTC | CALL W/L/D | CALL WR | PUT W/L/D | PUT WR | Combined net |",
      "|---|---:|---:|---:|---:|---:|"]
    recs=by_h[4]
    months=sorted({r["signal_time"].strftime("%Y-%m") for r in recs})
    for month in months:
      monthrows=[r for r in recs if r["signal_time"].strftime("%Y-%m")==month]
      cells=[]
      for side in ("CALL","PUT"):
        x=[r["outcome"] for r in monthrows if r["direction"]==side]
        w,l,d,wr,net,*_=stats(x)
        cells.append((f"{w}/{l}/{d}",f"{wr:.1f}%"))
      net=sum(PAYOUT if r["outcome"]=="WIN" else -1 if r["outcome"]=="LOSS" else 0 for r in monthrows)
      lines.append(f"| {month} | {cells[0][0]} | {cells[0][1]} | {cells[1][0]} | {cells[1][1]} | {net:+.2f}u |")
    lines += ["","## Interpretation rules","",
      "- 92% payout requires 52.0833% decisive win rate to break even; report net, ROI, drawdown and confidence intervals, not WR alone.",
      "- TEST is the final chronological period, but prior exploration means it is not an untouched independent holdout.",
      "- Wilson intervals assume independent decisive outcomes; serial dependence and overlapping market regimes can make them too narrow.",
      "- Expiry comparison reuses the same signal events, so differences are paired and should not be interpreted as independent samples.",
      "- No filter or parameter may be promoted based on this report alone; confirm prospectively on fresh Pocket Option candles.",""]
    a.out.parent.mkdir(parents=True,exist_ok=True); report="\n".join(lines); a.out.write_text(report+"\n",encoding="utf-8"); print(report)

if __name__=="__main__": main()
