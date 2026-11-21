#!/usr/bin/env python3
"""Frozen-parameter robustness audit for first-wave inverse leads."""
from __future__ import annotations
import argparse, random
from collections import defaultdict
from pathlib import Path
from expanded_strategy_screen import read_m1, make_events, outcome, HORIZONS, PAYOUT
from long_history_validation import make_m5

TARGETS = {
    ("ATR_EXPANSION_PUT", 4): ("HYD-CAND-004", "ATR expansion downside event -> CALL", 20),
    ("INSIDE_BAR_BREAK_PUT", 6): ("HYD-CAND-005", "Inside-bar downside break -> CALL", 30),
}

def summarize(xs):
    w, l, d = xs.count("W"), xs.count("L"), xs.count("D")
    decisive = w + l
    eq = peak = dd = 0.0
    streak = max_streak = 0
    for x in xs:
        if x == "W": eq += PAYOUT; streak = 0
        elif x == "L": eq -= 1; streak += 1; max_streak = max(max_streak, streak)
        peak = max(peak, eq); dd = max(dd, peak-eq)
    return dict(n=len(xs), w=w, l=l, d=d, wr=(100*w/decisive if decisive else None),
                net=w*PAYOUT-l, dd=dd, streak=max_streak)

def block_bootstrap(xs, reps=3000, block=10, seed=20261110):
    if len(xs) < block*2: return None
    rng=random.Random(seed)
    n=len(xs); wrs=[]; nets=[]
    for _ in range(reps):
        sample=[]
        while len(sample)<n:
            start=rng.randrange(n)
            sample.extend(xs[(start+j)%n] for j in range(block))
        sample=sample[:n]
        w=sample.count("W"); l=sample.count("L"); d=sample.count("D")
        dec=w+l
        if dec: wrs.append(100*w/dec)
        nets.append(w*PAYOUT-l)
    pct=lambda a,p: sorted(a)[int((len(a)-1)*p)]
    return (pct(wrs,.025), pct(wrs,.975), pct(nets,.025), pct(nets,.975))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    m1=read_m1(a.data); segments=make_m5(m1)
    dates=sorted({b.timestamp.date() for seg in segments for b in seg})
    d1=dates[int(.60*len(dates))]; d2=dates[int(.80*len(dates))]
    cohorts=defaultdict(list); monthly=defaultdict(list)
    for sid,bars in enumerate(segments):
        ev=make_events(bars)
        for (event_name,h),(cid,label,expiry) in TARGETS.items():
            opposite="CALL"
            rows=[]
            for i,side in ev.get(event_name,[]):
                if i+h>=len(bars): continue
                start=bars[i].timestamp.date()
                settle=bars[i+h].timestamp.date()
                period="TRAIN" if start<d1 else "VALIDATION" if start<d2 else "TEST"
                if (period=="TRAIN" and settle>=d1) or (period=="VALIDATION" and settle>=d2): continue
                rows.append((i,start,period,outcome(bars,i,side,h),outcome(bars,i,opposite,h)))
            nxt=-1
            for i,day,period,orig,inv in sorted(rows):
                if i<nxt: continue
                nxt=i+h
                cohorts[(cid,period,"ORIGINAL")].append(orig)
                cohorts[(cid,period,"INVERTED")].append(inv)
                monthly[(cid,day.strftime("%Y-%m"),"INVERTED")].append(inv)
    lines=[
      "# Frozen-parameter inverse lead robustness audit","",
      f"Source: Dukascopy EUR/USD M1 BID; {len(m1):,} rows; {sum(map(len,segments)):,} complete M5 bars; {len(segments)} continuous segments.",
      f"Coverage: {m1[0].timestamp.isoformat()} to {m1[-1].timestamp.isoformat()}.",
      f"Chronological splits: TRAIN < {d1}; VALIDATION {d1}–{d2}; TEST >= {d2}.",
      "Frozen definitions: ATR(14)>1.25x prior ATR, bearish M5 body >=0.5 ATR, invert PUT to CALL, 20m; and inside-bar mother-range downside close break, invert PUT to CALL, 30m.",
      "Closed M5 signal, entry next M5 open, expiry close of Nth subsequent M5 bar. Original/inverse share exact events and non-overlap choices. No parameters tuned in this audit.",
      "Assumed payout 92% (+0.92u/-1u/0u). Dukascopy BID is not Pocket Option executable pricing; spread, latency and variable payout excluded.",
      "Moving-block bootstrap: 3,000 circular resamples, block length 10 trades, deterministic seed. Intervals are descriptive; block length sensitivity and matched controls remain outstanding.",
      "## Split results","",
      "| Candidate | Variant | Split | n | W/L/D | WR | Net u | Max DD u | Max loss streak | Block-bootstrap WR 95% | Net 95% |",
      "|---|---|---|---:|---|---:|---:|---:|---:|---|---|"
    ]
    for cid in sorted({k[0] for k in cohorts}):
      for period in ("TRAIN","VALIDATION","TEST"):
       for variant in ("ORIGINAL","INVERTED"):
        xs=cohorts.get((cid,period,variant),[])
        if not xs: continue
        s=summarize(xs); bb=block_bootstrap(xs,seed=20261110+len(xs)+(0 if variant=="ORIGINAL" else 1))
        wr="n/a" if s["wr"] is None else f'{s["wr"]:.2f}%'
        bwr="n/a" if bb is None else f'[{bb[0]:.2f},{bb[1]:.2f}]%'
        bnet="n/a" if bb is None else f'[{bb[2]:+.2f},{bb[3]:+.2f}]'
        lines.append(f'| {cid} | {variant} | {period} | {s["n"]} | {s["w"]}/{s["l"]}/{s["d"]} | {wr} | {s["net"]:+.2f} | {s["dd"]:.2f} | {s["streak"]} | {bwr} | {bnet} |')
    lines += ["","## Monthly inverse breakdown","",
      "| Candidate | Signal month UTC | n | W/L/D | WR | Net u |","|---|---|---:|---|---:|---:|"]
    for (cid,month,var),xs in sorted(monthly.items()):
        s=summarize(xs); wr="n/a" if s["wr"] is None else f'{s["wr"]:.2f}%'
        lines.append(f'| {cid} | {month} | {s["n"]} | {s["w"]}/{s["l"]}/{s["d"]} | {wr} | {s["net"]:+.2f} |')
    lines += ["","## Interpretation rules","",
      "- This is a frozen-parameter robustness audit, not another parameter search.",
      "- Monthly cells are descriptive; small monthly samples must not be interpreted as reliable WR estimates.",
      "- Block bootstrap accounts partially for local serial dependence but does not eliminate regime shifts or discovery-wide multiple testing.",
      "- No candidate is confirmed by this audit. Require fresh independent data and prospective Pocket Option-feed validation.",
      ""]
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text("\n".join(lines),encoding="utf-8")
    print(f"Frozen inverse robustness audit complete: M1={len(m1):,}, M5={sum(map(len,segments)):,}, candidates={len(TARGETS)}")
if __name__=="__main__": main()
