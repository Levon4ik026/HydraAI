#!/usr/bin/env python3
"""Walk-forward block-bootstrap Time Machine for EURUSD M5. Research only."""
from __future__ import annotations
import argparse, math, random, statistics
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

from standalone_strategy_screen import (
    PAYOUT, HORIZONS, build_specs, read_m1, signals_for_segment,
    split_dates, summarize,
)
from long_history_validation import make_m5

BREAK_EVEN = 1.0 / (1.0 + PAYOUT)
BLOCK = 3
LOOKBACK_DATES = 60
TOD_TOLERANCE_MIN = 10
MIN_POOL = 30
SIMULATIONS = 1200
SEED = 20261108

def log_returns(bars):
    """Return increments usable from an entry open: first close/open, then close/prev close."""
    out=[]
    for i,b in enumerate(bars):
        base=b.open if i==0 else bars[i-1].close
        out.append(math.log(b.close/base))
    return out

def trailing_vol(bars, i, n=12):
    if i < n:
        return None
    vals=[math.log(bars[k].close/bars[k-1].close) for k in range(i-n+1,i+1)]
    return statistics.pstdev(vals)

def tod_distance(a, b):
    day=24*60
    return min((a-b)%day,(b-a)%day)

def classify_vol(current, pool_values):
    if current is None or len(pool_values)<10:
        return None
    q1=statistics.quantiles(pool_values,n=3,method="inclusive")[0]
    q2=statistics.quantiles(pool_values,n=3,method="inclusive")[1]
    return 0 if current<=q1 else 1 if current<=q2 else 2

def candidate_pool(segments, signal_time, current_vol, horizon, block=BLOCK):
    cutoff_dates=sorted({b.timestamp.date() for seg in segments for b in seg if b.timestamp < signal_time})
    allowed_dates=set(cutoff_dates[-LOOKBACK_DATES:])
    candidates=[]
    # Only historical starts with complete blocks strictly before this forecast.
    for sid, bars in enumerate(segments):
        for j in range(13, len(bars)-block+1):
            if bars[j].timestamp >= signal_time or bars[j+block-1].timestamp >= signal_time:
                continue
            if bars[j].timestamp.date() not in allowed_dates:
                continue
            if tod_distance(bars[j].timestamp.hour*60+bars[j].timestamp.minute,
                            signal_time.hour*60+signal_time.minute)>TOD_TOLERANCE_MIN:
                continue
            vol=trailing_vol(bars,j-1)
            if vol is None:
                continue
            candidates.append((sid,j,vol,bars))
    if not candidates:
        return [], None
    vol_values=[x[2] for x in candidates]
    current_regime=classify_vol(current_vol,vol_values)
    if current_regime is None:
        return [], None
    q1=statistics.quantiles(vol_values,n=3,method="inclusive")[0]
    q2=statistics.quantiles(vol_values,n=3,method="inclusive")[1]
    matched=[]
    for sid,j,v,bars in candidates:
        regime=0 if v<=q1 else 1 if v<=q2 else 2
        if regime==current_regime and j+block-1 < len(bars):
            matched.append((sid,j,bars))
    return matched,current_regime

def simulate_probabilities(pool, entry_price, direction, horizon, seed, simulations=SIMULATIONS, block=BLOCK):
    rng=random.Random(seed)
    paths=[]
    for sid,j,bars in pool:
        # Build block returns, never crossing the segment boundary.
        rs=[]
        for k in range(block):
            base=bars[j+k].open if k==0 else bars[j+k-1].close
            rs.append(math.log(bars[j+k].close/base))
        paths.append(rs)
    if not paths:
        return None
    wins=losses=draws=0
    for _ in range(simulations):
        remaining=horizon
        total=0.0
        while remaining>0:
            rs=rng.choice(paths)
            take=min(remaining,len(rs))
            total += sum(rs[:take])
            remaining -= take
        # For a fixed expiry, the final simulated log return determines direction.
        delta=entry_price*(math.exp(total)-1.0)
        signed=delta if direction=="CALL" else -delta
        if abs(signed)<1e-10: draws+=1
        elif signed>0: wins+=1
        else: losses+=1
    n=simulations
    pw,pl,pd=wins/n,losses/n,draws/n
    return {"p_win":pw,"p_loss":pl,"p_draw":pd,
            "ev":PAYOUT*pw-pl,
            "mc_se":math.sqrt(max(0,pw*(1-pw)/n)),
            "n_sim":n}

def historical_baselines(segments, signal_time, direction, horizon):
    dates=sorted({b.timestamp.date() for seg in segments for b in seg if b.timestamp < signal_time})
    allowed=set(dates[-LOOKBACK_DATES:])
    all_out=[]; tod_out=[]
    for bars in segments:
        for j in range(12,len(bars)-horizon):
            if bars[j].timestamp >= signal_time or bars[j+horizon].timestamp >= signal_time:
                continue
            if bars[j].timestamp.date() not in allowed:
                continue
            delta=bars[j+horizon].close-bars[j].open
            signed=delta if direction=="CALL" else -delta
            result=0 if abs(signed)<1e-10 else 1 if signed>0 else -1
            all_out.append(result)
            if tod_distance(bars[j].timestamp.hour*60+bars[j].timestamp.minute,
                            signal_time.hour*60+signal_time.minute)<=TOD_TOLERANCE_MIN:
                tod_out.append(result)
    def pwin(rows):
        decisive=[x for x in rows if x]
        return sum(x==1 for x in decisive)/len(decisive) if decisive else None
    return pwin(all_out),pwin(tod_out),len(all_out),len(tod_out)

def choose_validation_variants(segments, d1, d2):
    """Predeclared validation-only selection: one best eligible variant per family."""
    specs=build_specs()
    raw=defaultdict(list)
    for sid,bars in enumerate(segments):
        signals=signals_for_segment(bars,specs)
        for name,events in signals.items():
            for h in HORIZONS:
                for i,side in events:
                    if i+h>=len(bars): continue
                    signal_day=bars[i].timestamp.date()
                    settle_day=bars[i+h].timestamp.date()
                    if d1<=signal_day<d2 and settle_day<d2:
                        raw[(name,h)].append((sid,i,side,bars))
    family_best={}
    for (name,h),rows in raw.items():
        # Individual strategy/expiry non-overlap during validation.
        accepted=[]
        by_seg=defaultdict(list)
        for row in rows: by_seg[row[0]].append(row)
        for sid,items in by_seg.items():
            next_i=-1
            for item in sorted(items,key=lambda x:x[1]):
                if item[1]>=next_i:
                    accepted.append(item); next_i=item[1]+h
        outcomes=[]
        for sid,i,side,bars in accepted:
            delta=bars[i+h].close-bars[i+1].open
            signed=delta if side=="CALL" else -delta
            outcomes.append("D" if abs(signed)<1e-12 else "W" if signed>0 else "L")
        n,w,l,d,wr,net,pf=summarize(outcomes)
        family=name.split("_")[0]
        if n<500 or not (wr>100*BREAK_EVEN and net>0 and pf>=1.05):
            continue
        score=(net,wr,n)
        if family not in family_best or score>family_best[family][0]:
            family_best[family]=(score,(name,h))
    return sorted(v[1] for v in family_best.values())

def build_portfolio(segments, selected, d2):
    specs=build_specs()
    selected_set=set(selected)
    raw=[]
    for sid,bars in enumerate(segments):
        signals=signals_for_segment(bars,specs)
        for name,h in selected_set:
            for i,side in signals.get(name,[]):
                if i+h>=len(bars) or bars[i].timestamp.date()<d2:
                    continue
                if bars[i+h].timestamp.date()<d2:
                    continue
                raw.append({"name":name,"h":h,"sid":sid,"i":i,"side":side,"bars":bars,
                            "signal_time":bars[i].timestamp,"entry":bars[i+1].open,
                            "outcome":None})
    # Resolve same-bar collisions: same direction collapses; opposite directions -> WAIT.
    grouped=defaultdict(list)
    for r in raw: grouped[(r["sid"],r["i"])].append(r)
    events=[]
    for key,rows in grouped.items():
        sides={r["side"] for r in rows}
        if len(sides)!=1: continue
        events.append(sorted(rows,key=lambda x:(x["h"],x["name"]))[0])
    # Global one-position schedule; no overlapping intervals.
    events.sort(key=lambda x:(x["signal_time"],x["h"],x["name"]))
    kept=[]; busy_until={}
    for e in events:
        sid=e["sid"]; i=e["i"]
        if i < busy_until.get(sid,-1): continue
        e["outcome"]=outcome_from(e["bars"],i,e["side"],e["h"])
        busy_until[sid]=i+e["h"]
        kept.append(e)
    return kept

def outcome_from(bars,i,side,h):
    delta=bars[i+h].close-bars[i+1].open
    signed=delta if side=="CALL" else -delta
    return "DRAW" if abs(signed)<1e-10 else "WIN" if signed>0 else "LOSS"

def score_forecasts(rows):
    """Score P(WIN) conditional on a decisive outcome; DRAWs are excluded."""
    scored=[]
    for key in ("tm","tod","all"):
        vals=[r for r in rows
              if r.get(key) is not None and r["actual"] in ("WIN","LOSS")]
        if not vals:
            continue
        eps=1e-6
        brier=sum((r[key]-(1 if r["actual"]=="WIN" else 0))**2
                  for r in vals)/len(vals)
        ll=-sum((1 if r["actual"]=="WIN" else 0)*math.log(max(eps,r[key]))+
                (1 if r["actual"]=="LOSS" else 0)*math.log(max(eps,1-r[key]))
                for r in vals)/len(vals)
        scored.append((key,len(vals),brier,ll))
    return scored

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--out",type=Path,default=Path("research/HYDRA_TIME_MACHINE_REPORT.md"))
    ap.add_argument("--simulations",type=int,default=SIMULATIONS)
    a=ap.parse_args()
    m1=read_m1(a.data); segments=make_m5(m1); d1,d2=split_dates(segments)
    selected=choose_validation_variants(segments,d1,d2)
    trades=build_portfolio(segments,selected,d2)
    forecasts=[]; insufficient=0
    for k,t in enumerate(trades):
        bars=t["bars"]; i=t["i"]; h=t["h"]
        vol=trailing_vol(bars,i)
        pool,regime=candidate_pool(segments,t["signal_time"],vol,h)
        if len(pool)<MIN_POOL:
            insufficient+=1; continue
        seed=SEED + int(t["signal_time"].timestamp()) + k
        sim=simulate_probabilities(pool,t["entry"],t["side"],h,seed,a.simulations)
        if sim is None: insufficient+=1; continue
        all_p,tod_p,all_n,tod_n=historical_baselines(segments,t["signal_time"],t["side"],h)
        forecasts.append({"signal":t["signal_time"],"name":t["name"],"h":h,
                          "side":t["side"],"actual":t["outcome"],"pool":len(pool),
                          "regime":regime,"tm":sim["p_win"],"tod":tod_p,"all":all_p,
                          "ev":sim["ev"],"mc_se":sim["mc_se"]})
    outcomes=[t["outcome"] for t in trades]
    n,w,l,d,wr,net,pf=summarize(outcomes)
    days=len({t["signal_time"].date() for t in trades})
    freq=20*n/max(1,days)
    lines=[
      "# HYDRA Time Machine — walk-forward research report","",
      f"Source: Dukascopy EURUSD M1 BID; {len(m1):,} M1 rows; {sum(map(len,segments)):,} complete M5 bars; {len(segments):,} gap-separated segments.",
      f"Coverage: {m1[0].timestamp.isoformat()} — {m1[-1].timestamp.isoformat()}.",
      f"Chronological split from signal dates: TRAIN < {d1}; VALIDATION {d1} through {d2-timedelta(days=1)}; TEST >= {d2}.",
      f"Selected on VALIDATION only (one best eligible strategy per family): {', '.join(f'{x[0]}@{x[1]*5}m' for x in selected) if selected else 'NONE'}.",
      "Eligibility rule: validation non-overlap n>=500, decisive WR > 52.0833%, net > 0u, PF >= 1.05; rank by net, then WR, then n.",
      "Portfolio policy: same timestamp/same side collapses to one; opposite-side conflict is WAIT; one global position per segment, no overlap.",
      f"Time Machine: contiguous {BLOCK}-bar moving-block bootstrap; up to {LOOKBACK_DATES} prior trading dates; UTC time-of-day ±{TOD_TOLERANCE_MIN}m; causal trailing-volatility tercile; {a.simulations} simulations per accepted forecast.",
      f"Pool minimum: {MIN_POOL} eligible block starts. Forecasts without sufficient pool are withheld, not forced.",
      "Payout: WIN +0.92u, LOSS -1u, DRAW 0u. Dukascopy BID is not Pocket Option's exact quote stream; no platform payout/spread model.",
      "IMPORTANT: Historical TEST has been repeatedly explored and is not pristine confirmation. All results are exploratory; prospective Pocket Option DEMO validation remains required.","",
      "## Validation-selected portfolio — TEST performance","",
      "| Trades | W/L/D | Decisive WR | Net u | PF | Signals / 20 trading dates |",
      "|---:|---|---:|---:|---:|---:|",
      f"| {n} | {w}/{l}/{d} | {wr:.2f}% | {net:+.2f} | {pf:.2f} | {freq:.2f} |",
      "",
      f"Time Machine forecasts scored: {len(forecasts)} / {len(trades)} portfolio trades; insufficient pool: {insufficient}; coverage {100*len(forecasts)/max(1,len(trades)):.1f}%.",
      "## Probability quality (TEST, exploratory)","",
      "| Forecast | Decisive n (DRAW excluded) | Brier (lower better) | Log loss (lower better) |",
      "|---|---:|---:|---:|"]
    for key,count,brier,ll in score_forecasts(forecasts):
        lines.append(f"| {key} | {count} | {brier:.4f} | {ll:.4f} |")
    if forecasts:
        mean_ev=statistics.mean(r["ev"] for r in forecasts)
        mean_pool=statistics.mean(r["pool"] for r in forecasts)
        mean_se=statistics.mean(r["mc_se"] for r in forecasts)
        lines += ["","## Time Machine diagnostics","",
          f"- Mean simulated expected net per forecast: {mean_ev:+.4f}u at 92% payout (not realized edge).",
          f"- Mean matched pool size: {mean_pool:.1f} block starts.",
          f"- Mean Monte Carlo standard error for P(WIN): {mean_se:.4f} (simulation error only; not market uncertainty).",
          f"- Forecast outcome counts: W={sum(r['actual']=='WIN' for r in forecasts)}, L={sum(r['actual']=='LOSS' for r in forecasts)}, D={sum(r['actual']=='DRAW' for r in forecasts)}."]
    lines += ["","## Interpretation and limitations","",
      "- The Time Machine forecasts P(WIN) from historical block-resampled returns; it is not a CALL/PUT generator and does not upgrade WAIT.",
      "- Baselines are prior 60-date unconditional and time-of-day-only directional win rates. A model is useful only if its out-of-sample Brier/log loss improves on them.",
      "- Bootstrap blocks preserve short-run ordering but do not guarantee realistic long-range dependencies, news behavior, or future regime continuity.",
      "- This implementation uses UTC time-of-day and a trailing 12-bar volatility tercile; no future data is allowed in each forecast pool.",
      "- Monte Carlo standard error quantifies finite simulation noise only; it is not a confidence interval for future market performance.",
      "- Historical strategy selection is validation-only, but the dataset and TEST period have already been explored. Do not treat this as independent proof.",
      "- No production integration, local Windows file changes, or order execution.",""]
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__": main()
