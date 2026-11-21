#!/usr/bin/env python3
"""Dependence-aware validation audit for the frozen HYD-CAND-001 situation profile."""
from __future__ import annotations
import argparse, random
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from cand001_situation_profile import read_m1, make_feature_rows, period_for, D1, D2

PAYOUT=0.92
BLOCKS=(1,3,5,7,10)

def q(v,p):
    if not v:return float("nan")
    z=sorted(v); x=(len(z)-1)*p; lo=int(x); hi=min(lo+1,len(z)-1)
    return z[lo]+(z[hi]-z[lo])*(x-lo)

def rate(w,l):
    return w/(w+l) if w+l else float("nan")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--reps",type=int,default=20000)
    a=ap.parse_args()
    m1=read_m1(a.data)
    from reproduce_m5_bb_williams_adx import make_m5
    segments=make_m5(m1)
    cand=[]; bg=[]; all_signal_times=set()
    for bars in segments:
        f=make_feature_rows(bars)
        for i in range(60,len(bars)-13):
            if bars[i+1].timestamp-bars[i].timestamp != timedelta(minutes=5): continue
            settle=bars[i+1].timestamp+timedelta(minutes=5)
            split=period_for(bars[i].timestamp,settle)
            if split!="VALIDATION": continue
            x=f[i]
            # Exclude every frozen HYD-CAND-001 trigger from background,
            # not only triggers that also pass the situation gate.
            is_candidate = x["rsi14"] is not None and x["rsi14"]>=70 and bars[i].close<bars[i].open
            if is_candidate:
                all_signal_times.add(bars[i].timestamp)
            if x["bias"]!="UP" or x["vol_band"]!="HIGH(>67%)": continue
            delta=bars[i+1].close-bars[i+1].open
            outcome="D" if abs(delta)<1e-12 else "DOWN" if delta<0 else "UP"
            bg.append((bars[i].timestamp.date(),outcome,bars[i].timestamp))
            if is_candidate:
                cand.append((bars[i].timestamp.date(),"D" if outcome=="D" else "W" if outcome=="DOWN" else "L",bars[i].timestamp))
    # Match the discovery report: remove all candidate trigger timestamps,
    # including triggers outside the situation gate, from situation background.
    bg=[x for x in bg if x[2] not in all_signal_times and x[1] in ("DOWN","UP")]
    cw=sum(x[1]=="W" for x in cand); cl=sum(x[1]=="L" for x in cand); cd=sum(x[1]=="D" for x in cand)
    bw=sum(x[1]=="DOWN" for x in bg); bl=sum(x[1]=="UP" for x in bg)
    if (len(cand),cw,cl,cd)!=(123,75,48,0):
        raise SystemExit(f"FROZEN SITUATION COHORT MISMATCH: got {(len(cand),cw,cl,cd)}, expected (123,75,48,0)")
    if len(bg)!=6081:
        raise SystemExit(f"BACKGROUND COHORT MISMATCH: got {len(bg)}, expected 6081; inspect data/eligibility")
    start=D1.date(); end=(D2-timedelta(days=1)).date()
    days=[start+timedelta(days=k) for k in range((end-start).days+1)]
    cdaily=defaultdict(lambda:[0,0,0]); bdaily=defaultdict(lambda:[0,0])
    for day,o,_ in cand:
        cdaily[day][0]+=o=="W"; cdaily[day][1]+=o=="L"; cdaily[day][2]+=o=="D"
    for day,o,_ in bg:
        bdaily[day][0]+=o=="DOWN"; bdaily[day][1]+=o=="UP"
    # Fixed daily vectors include zero-event days. Resample the same contiguous
    # calendar blocks for candidate and background to retain paired day conditions.
    vectors={d:(*cdaily[d],*bdaily[d]) for d in days}
    rng_seed=20261112
    lines=[
      "# HYD-CAND-001 — dependence-aware validation of EMA-UP × ATR-HIGH",
      "",
      "Frozen profile: original RSI14>=70 + bearish M5 candle => PUT; entry next M5 open; 5-minute expiry. Situation gate: EMA20>EMA50 and ATR(14)/close percentile rank >67% against prior 120 completed M5 bars, signal candle excluded. The source feature implementation is reused unchanged.",
      f"Data: Dukascopy EUR/USD M1 BID, {len(m1):,} valid rows; {sum(map(len,segments)):,} complete M5 bars; VALIDATION {start} through {end}. Payout is a 92% scenario (+0.92u/-1u/0u), not platform-confirmed.",
      "Bootstrap: paired moving blocks over the complete UTC calendar-day grid, including zero-event days. Same sampled days/blocks are used for candidate and background. Non-wrapping contiguous blocks; 20,000 replicates; fixed seed 20261112. Percentile intervals describe calendar sampling variability, not selection bias or feed/execution risk.",
      "Background is every eligible continuous M5 bar in the same EMA-UP × ATR-HIGH situation, excluding candidate signal timestamps. It is a descriptive serially dependent benchmark, not a matched non-overlapping trade schedule. Candidate trades retain the frozen event schedule.",
      "",
      "## Frozen cohort reproduction",
      "",
      f"- Candidate: N={len(cand)}, W/L/D={cw}/{cl}/{cd}, decisive WR={100*rate(cw,cl):.2f}%, net={PAYOUT*cw-cl:+.2f}u.",
      f"- Background: N={len(bg)}, DOWN/UP={bw}/{bl}, PUT-equivalent rate={100*rate(bw,bl):.2f}%.",
      f"- Observed decisive WR lift: {(rate(cw,cl)-rate(bw,bl))*100:+.2f} percentage points.",
      f"- Candidate active days: {sum(sum(v[:3])>0 for v in vectors.values())}/{len(days)}; background active days: {sum(sum(v[3:])>0 for v in vectors.values())}/{len(days)}.",
      "",
      "## Paired calendar-block bootstrap",
      "",
      "| Block days | Lift 95% CI (pp) | P(lift > 0) | Candidate WR 95% CI | Candidate net units 95% CI |",
      "|---:|---:|---:|---:|---:|"
    ]
    for bi,block in enumerate(BLOCKS):
        rng=random.Random(rng_seed+block)
        lifts=[]; wrs=[]; nets=[]
        for _ in range(a.reps):
            picked=[]
            while len(picked)<len(days):
                s=rng.randrange(0,len(days)-block+1)
                picked.extend(days[s:s+block])
            sample=[vectors[d] for d in picked[:len(days)]]
            sw=sum(v[0] for v in sample); sl=sum(v[1] for v in sample)
            sbw=sum(v[3] for v in sample); sbl=sum(v[4] for v in sample)
            if sw+sl and sbw+sbl:
                lifts.append((rate(sw,sl)-rate(sbw,sbl))*100)
                wrs.append(rate(sw,sl)*100)
                nets.append(PAYOUT*sw-sl)
        lines.append(f"| {block} | [{q(lifts,.025):+.2f}, {q(lifts,.975):+.2f}] | {100*sum(x>0 for x in lifts)/len(lifts):.1f}% | [{q(wrs,.025):.2f}, {q(wrs,.975):.2f}]% | [{q(nets,.025):+.2f}, {q(nets,.975):+.2f}]u |")
    lines += ["","## Monthly and daily concentration","",
      "| Month | N | W/L/D | Decisive WR | Net u |",
      "|---|---:|---|---:|---:|"]
    monthly=defaultdict(lambda:[0,0,0])
    for day,o,_ in cand:
        k=day.strftime("%Y-%m"); monthly[k][0]+=o=="W"; monthly[k][1]+=o=="L"; monthly[k][2]+=o=="D"
    month_nets=[]
    for mo,v in sorted(monthly.items()):
        w,l,d=v; net=PAYOUT*w-l; month_nets.append((mo,net))
        lines.append(f"| {mo} | {w+l+d} | {w}/{l}/{d} | {100*rate(w,l):.2f}% | {net:+.2f} |")
    total_net=PAYOUT*cw-cl
    daily=[]
    for day in days:
        w,l,d=cdaily[day]; daily.append((day,PAYOUT*w-l,w+l+d))
    best_day=max(daily,key=lambda x:x[1])
    best_month=max(month_nets,key=lambda x:x[1]) if month_nets else ("n/a",0)
    lines += ["",f"- Positive months: {sum(v>0 for _,v in month_nets)}/{len(month_nets)}.",
      f"- Best month: {best_month[0]} ({best_month[1]:+.2f}u), {100*best_month[1]/total_net:.1f}% of total net." if total_net>0 else f"- Best month: {best_month[0]} ({best_month[1]:+.2f}u).",
      f"- Best day: {best_day[0]} ({best_day[1]:+.2f}u; {best_day[2]} trades), {100*best_day[1]/total_net:.1f}% of total net." if total_net>0 else f"- Best day: {best_day[0]} ({best_day[1]:+.2f}u; {best_day[2]} trades).",
      "",
      "## Interpretation",
      "",
      "- This is a validation-only uncertainty audit of a predeclared profile from the discovery report; it does not turn the profile into a confirmed strategy.",
      "- A positive lift whose block-bootstrap interval crosses zero is not robust evidence of a distinct situation advantage.",
      "- The 1-day block is a lower-dependence benchmark; 3/5/7/10-day blocks test sensitivity to short-range clustering. All include zero-event dates.",
      "- Because the broad profile was noticed after examining candidate results, this audit remains exposed to multiple-testing/selection bias. Bootstrap does not repair that.",
      "- Background is intentionally reported as a descriptive all-bars comparator; its sample size is not directly comparable to the non-overlapping candidate trade count.",
      "- Dukascopy BID is a historical proxy. No Pocket Option quote, spread, latency, payout variability, or live execution model is included.",
      "- No TEST-based filter selection, threshold changes, month filters, or parameter optimization were performed.",
      ""]
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text("\n".join(lines),encoding="utf-8")
    print(f"PASS frozen cohort candidate={len(cand)} {cw}/{cl}/{cd}; background={len(bg)} {bw}/{bl}; days={len(days)}; report={a.out}")
if __name__=="__main__": main()
