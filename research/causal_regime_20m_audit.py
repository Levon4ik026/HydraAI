#!/usr/bin/env python3
"""Causal regime and pre-entry feature audit for the frozen 20-minute setup.

All predictors are known at the signal candle close. Outcome is measured from
next M5 open to close of the fourth M5 candle. No parameters are optimized.
"""
from __future__ import annotations
import argparse, math, statistics
from collections import defaultdict
from pathlib import Path
from long_history_validation import read_duka, make_events, stats, PAYOUT
from reproduce_m5_bb_williams_adx import make_m5, indicators

def ema(values, period):
    out=[None]*len(values)
    if len(values)<period: return out
    state=sum(values[:period])/period
    out[period-1]=state
    alpha=2/(period+1)
    for i in range(period,len(values)):
        state=values[i]*alpha+state*(1-alpha); out[i]=state
    return out

def percentile_rank(history, value):
    if not history: return None
    return sum(x<=value for x in history)/len(history)

def quartile_edges(values):
    vals=sorted(x for x in values if x is not None)
    if len(vals)<20: return None
    return [vals[int((len(vals)-1)*q)] for q in (.25,.5,.75)]

def bucket(value, edges):
    if value is None or edges is None: return "NA"
    return "Q1" if value<=edges[0] else "Q2" if value<=edges[1] else "Q3" if value<=edges[2] else "Q4"

def outcome(bars,i,side):
    delta=bars[i+4].close-bars[i+1].open
    if abs(delta)<1e-12: return "DRAW"
    return "WIN" if (delta>0 if side=="CALL" else delta<0) else "LOSS"

def summarize(rows):
    w=sum(x["outcome"]=="WIN" for x in rows); l=sum(x["outcome"]=="LOSS" for x in rows); d=len(rows)-w-l
    dec=w+l; wr=100*w/dec if dec else float("nan")
    return w,l,d,wr,w*PAYOUT-l

def fmt(rows):
    w,l,d,wr,net=summarize(rows)
    return f"{len(rows)} | {w}/{l}/{d} | {wr:.1f}% | {net:+.2f}u"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--out",type=Path,default=Path("research/CAUSAL_REGIME_20M_AUDIT.md"))
    a=ap.parse_args()
    m1=read_duka(a.data); segments=make_m5(m1)
    events=make_events(segments,15)
    days=sorted({e["signal_time"].date() for e in events})
    d1=days[int(len(days)*.60)]; d2=days[int(len(days)*.80)]
    records=[]
    excluded_short_warmup=0
    events_by_seg=defaultdict(list)
    for e in events: events_by_seg[e["segment"]].append(e)
    for seg_id,bars in enumerate(segments):
        if not events_by_seg[seg_id]: continue
        ind=indicators(bars); closes=[b.close for b in bars]
        e20=ema(closes,20); e50=ema(closes,50)
        trs=[None]*len(bars)
        for j in range(1,len(bars)):
            b,prev=bars[j],bars[j-1]
            trs[j]=max(b.high-b.low,abs(b.high-prev.close),abs(b.low-prev.close))
        atr=[None]*len(bars)
        for j in range(14,len(bars)):
            atr[j]=sum(x for x in trs[j-13:j+1] if x is not None)/14
        atr_pct=[(atr[j]/bars[j].close if atr[j] and bars[j].close else None) for j in range(len(bars))]
        for e in events_by_seg[seg_id]:
            i=e["bar_index"]
            if i+4>=len(bars): continue
            if i<50:
                excluded_short_warmup += 1
                continue
            x=ind[i]; av=atr[i]
            if x["adx"] is None or not av or not e20[i] or not e50[i]: continue
            prior_atr=[v for v in atr_pct[max(14,i-120):i] if v is not None]
            volrank=percentile_rank(prior_atr,atr_pct[i]) if len(prior_atr)>=60 else None
            prev12=bars[i-12:i]; prev24=bars[i-24:i]
            cur=bars[i]; span=max(cur.high-cur.low,1e-12)
            upper_wick=cur.high-max(cur.open,cur.close); lower_wick=min(cur.open,cur.close)-cur.low
            bb=x["upper"]-x["lower"]
            signal_day=cur.timestamp.date()
            period="TRAIN" if signal_day<d1 else "VALIDATION" if signal_day<d2 else "TEST"
            # Causal OHLC path-shape descriptors; all inputs end at signal close.
            diffs6=[bars[j].close-bars[j-1].close for j in range(i-5,i+1)]
            path6=sum(abs(v) for v in diffs6)
            diffs12=[bars[j].close-bars[j-1].close for j in range(i-11,i+1)]
            path12=sum(abs(v) for v in diffs12)
            ranges6=[bars[j].high-bars[j].low for j in range(i-5,i+1)]
            true_ranges6=[trs[j] for j in range(i-5,i+1) if trs[j] is not None]
            overlap_parts=[]
            for left,right in zip(bars[i-2:i+1],bars[i-3:i]):
                denom=min(left.high-left.low,right.high-right.low)
                if denom>0:
                    overlap_parts.append(max(0.0,min(left.high,right.high)-max(left.low,right.low))/denom)
            prior12_low=min(b.low for b in prev12); prior12_high=max(b.high for b in prev12)
            prior12_width=prior12_high-prior12_low
            prior12_ranges=[b.high-b.low for b in prev12]
            recent3_ranges=[b.high-b.low for b in bars[i-2:i+1]]
            prior12_mean=sum(prior12_ranges)/len(prior12_ranges)
            recent3_mean=sum(recent3_ranges)/len(recent3_ranges)
            run_sign=1 if cur.close>bars[i-1].close else -1 if cur.close<bars[i-1].close else 0
            same_color_run=0
            if run_sign:
                for j in range(i,max(0,i-6),-1):
                    sj=1 if bars[j].close>bars[j-1].close else -1 if bars[j].close<bars[j-1].close else 0
                    if sj!=run_sign: break
                    same_color_run+=1
            features={
              "trend":"UP" if e20[i]>e50[i] else "DOWN" if e20[i]<e50[i] else "FLAT",
              "adx_band":"15-20" if x["adx"]<20 else "20-25" if x["adx"]<25 else "25+",
              "volatility":"NA" if volrank is None else "LOW" if volrank<=.333 else "MID" if volrank<=.667 else "HIGH",
              "hour":"ASIA" if cur.timestamp.hour<7 else "LONDON" if cur.timestamp.hour<13 else "NY" if cur.timestamp.hour<21 else "LATE",
              "weekday":cur.timestamp.strftime("%a"),
              "sweep_high_12":"YES" if cur.high>max(b.high for b in prev12) and cur.close<max(b.high for b in prev12) else "NO",
              "sweep_low_12":"YES" if cur.low<min(b.low for b in prev12) and cur.close>min(b.low for b in prev12) else "NO",
              "sweep_high_24":"YES" if cur.high>max(b.high for b in prev24) and cur.close<max(b.high for b in prev24) else "NO",
              "sweep_low_24":"YES" if cur.low<min(b.low for b in prev24) and cur.close>min(b.low for b in prev24) else "NO",
              "aligned_sweep_12":"YES" if ((cur.low<min(b.low for b in prev12) and cur.close>min(b.low for b in prev12)) if e["direction"]=="CALL" else (cur.high>max(b.high for b in prev12) and cur.close<max(b.high for b in prev12))) else "NO",
              "aligned_sweep_24":"YES" if ((cur.low<min(b.low for b in prev24) and cur.close>min(b.low for b in prev24)) if e["direction"]=="CALL" else (cur.high>max(b.high for b in prev24) and cur.close<max(b.high for b in prev24))) else "NO",
              "body_atr":abs(cur.close-cur.open)/av,
              "range_atr":span/av,
              "upper_wick_ratio":upper_wick/span,
              "lower_wick_ratio":lower_wick/span,
              "bb_width_atr":bb/av if bb else None,
              "ema_spread_atr":(e20[i]-e50[i])/av,
              "di_spread":(x["plus_di"] or 0)-(x["minus_di"] or 0),
              "prior12_high_dist_atr":(max(b.high for b in prev12)-cur.close)/av,
              "prior12_low_dist_atr":(cur.close-min(b.low for b in prev12))/av,
              "prior24_high_dist_atr":(max(b.high for b in prev24)-cur.close)/av,
              "prior24_low_dist_atr":(cur.close-min(b.low for b in prev24))/av,
              "momentum3_atr":(cur.close-bars[i-3].close)/av,
              "momentum6_atr":(cur.close-bars[i-6].close)/av,
              "willr":x["willr"],
              "adx":x["adx"],
              "efficiency_6":abs(sum(diffs6))/path6 if path6>0 else 0.0,
              "efficiency_12":abs(sum(diffs12))/path12 if path12>0 else 0.0,
              "path_flips_6":sum(1 for a,b in zip(diffs6,diffs6[1:]) if a*b<0),
              "range_overlap_3":sum(overlap_parts)/len(overlap_parts) if overlap_parts else None,
              "range_compression_3v12":recent3_mean/prior12_mean if prior12_mean>0 else None,
              "close_location":(cur.close-cur.low)/span,
              "position_in_prior_12_range":(cur.close-prior12_low)/prior12_width if prior12_width>0 else None,
              "body_direction_agreement_3":sum(1 if bars[j].close>bars[j-1].close else -1 if bars[j].close<bars[j-1].close else 0 for j in range(i-2,i+1))/3.0,
              "median_range_to_true_range_6":statistics.median(ranges6)/statistics.median(true_ranges6) if true_ranges6 and statistics.median(true_ranges6)>0 else None,
              "same_color_run":float(same_color_run),
              "direction_aligned_body":(cur.close-cur.open)/av*(1 if e["direction"]=="CALL" else -1),
              "direction_aligned_close_location":(cur.close-cur.low)/span if e["direction"]=="CALL" else (cur.high-cur.close)/span,
            }
            records.append({"time":cur.timestamp,"direction":e["direction"],"period":period,
                            "outcome":outcome(bars,i,e["direction"]),"features":features})
    # Build a same-regime, non-signal 20m background. The direction outcome is
    # measured over exactly the same next-open -> fourth-close horizon.
    signal_keys={(r["time"],r["direction"]) for r in records}
    signal_times={segments[e["segment"]][e["bar_index"]].timestamp for e in events}
    background=[]
    for seg_id,bars in enumerate(segments):
        ind=indicators(bars); closes=[b.close for b in bars]
        e20=ema(closes,20); e50=ema(closes,50)
        trs=[None]*len(bars)
        for j in range(1,len(bars)):
            b,prev=bars[j],bars[j-1]
            trs[j]=max(b.high-b.low,abs(b.high-prev.close),abs(b.low-prev.close))
        atr=[None]*len(bars)
        for j in range(14,len(bars)):
            atr[j]=sum(x for x in trs[j-13:j+1] if x is not None)/14
        atr_pct=[(atr[j]/bars[j].close if atr[j] and bars[j].close else None) for j in range(len(bars))]
        for i in range(50,len(bars)-4):
            cur=bars[i]; x=ind[i]; av=atr[i]
            if x["adx"] is None or not av or not e20[i] or not e50[i]: continue
            prior=[v for v in atr_pct[max(14,i-120):i] if v is not None]
            if len(prior)<60 or atr_pct[i] is None: continue
            volrank=percentile_rank(prior,atr_pct[i])
            trend="UP" if e20[i]>e50[i] else "DOWN" if e20[i]<e50[i] else "FLAT"
            adx_band="15-20" if x["adx"]<20 else "20-25" if x["adx"]<25 else "25+"
            vol="LOW" if volrank<=.333 else "MID" if volrank<=.667 else "HIGH"
            day=cur.timestamp.date()
            period="TRAIN" if day<d1 else "VALIDATION" if day<d2 else "TEST"
            entry=bars[i+1].open; exitp=bars[i+4].close
            delta=exitp-entry
            p12h=max(b.high for b in bars[i-12:i]); p12l=min(b.low for b in bars[i-12:i])
            p24h=max(b.high for b in bars[i-24:i]); p24l=min(b.low for b in bars[i-24:i])
            background.append({"time":cur.timestamp,"period":period,"trend":trend,
                               "adx_band":adx_band,"volatility":vol,
                               "call_aligned12":cur.low<p12l and cur.close>p12l,
                               "put_aligned12":cur.high>p12h and cur.close<p12h,
                               "call_aligned24":cur.low<p24l and cur.close>p24l,
                               "put_aligned24":cur.high>p24h and cur.close<p24h,
                               "call_win":delta>1e-12,"put_win":delta< -1e-12,
                               "draw":abs(delta)<=1e-12,
                               "is_signal":cur.timestamp in signal_times})
    # Quantile thresholds learned on TRAIN only and then held fixed.
    numeric=[k for k in records[0]["features"] if isinstance(records[0]["features"][k],(int,float))]
    edges={}
    for key in numeric:
        edges[key]=quartile_edges([r["features"][key] for r in records if r["period"]=="TRAIN"])
    lines=[
      "# HYDRA — causal 20-minute regime audit","",
      f"Signals with 50-bar warmup and complete 20m path: {len(records):,}; excluded for <50 prior continuous M5 bars: {excluded_short_warmup:,}; all eligible trigger events: {len(events):,}.",
      "Volatility-rank classification is NA where fewer than 60 prior ATR observations are available; other features use their own minimum causal lookbacks.",
      f"Split: TRAIN < {d1}; VALIDATION {d1} to {d2}; TEST >= {d2}.",
      "Frozen trigger: BB(20,2) re-entry + Williams %R(14) cross + ADX(14)>=15. Entry next M5 open; exit fourth M5 close; payout 92%.",
      "All candidate predictors are signal-close or trailing-history values. Numeric quartile cutoffs are learned on TRAIN only and reused unchanged.",
      "External Dukascopy BID prices; no Pocket Option spread/quote model. Exploratory regime audit, not proof of profitability.","",
      "## Overall 20m results","",
      "| Period | Direction | n | W/L/D | Decisive WR | Net |",
      "|---|---|---:|---:|---:|---:|"]
    for p in ("TRAIN","VALIDATION","TEST"):
      for side in ("CALL","PUT"):
        sub=[r for r in records if r["period"]==p and r["direction"]==side]
        lines.append(f"| {p} | {side} | {fmt(sub)} |")
    # categorical splits
    for key in ("trend","adx_band","volatility","hour","weekday","sweep_high_12","sweep_low_12","sweep_high_24","sweep_low_24","aligned_sweep_12","aligned_sweep_24"):
      lines += ["",f"## Regime split: {key}","",
                "| Period | Direction | State | n | W/L/D | Decisive WR | Net |",
                "|---|---|---|---:|---:|---:|---:|"]
      states=sorted({r["features"][key] for r in records})
      for p in ("TRAIN","VALIDATION","TEST"):
       for side in ("CALL","PUT"):
        for state in states:
         sub=[r for r in records if r["period"]==p and r["direction"]==side and r["features"][key]==state]
         if sub: lines.append(f"| {p} | {side} | {state} | {fmt(sub)} |")
    # Numeric quartile splits, show only period/direction and bins with >=20 samples.
    for key in numeric:
      lines += ["",f"## Train-defined quartiles: {key}","",
                "| Period | Direction | Bin | n | W/L/D | Decisive WR | Net |",
                "|---|---|---|---:|---:|---:|---:|"]
      for p in ("TRAIN","VALIDATION","TEST"):
       for side in ("CALL","PUT"):
        for q in ("Q1","Q2","Q3","Q4"):
         sub=[r for r in records if r["period"]==p and r["direction"]==side and bucket(r["features"][key],edges[key])==q]
         if len(sub)>=20: lines.append(f"| {p} | {side} | {q} | {fmt(sub)} |")
    # Exact same-state background: trend x ADX band x rolling volatility tertile.
    lines += ["","## Exact matched 20m market baseline","",
              "Background uses every non-signal candle with the same next-open to fourth-close horizon and exact causal state: EMA20/50 trend x ADX band x prior-120 ATR/close tertile. All trigger timestamps are excluded. Cells with fewer than 20 background observations are omitted.",
              "| Period | Direction | State | Signal n | Signal W/L/D | Signal WR | Signal net | Background n | Background WR | Lift |",
              "|---|---|---|---:|---|---:|---:|---:|---:|---:|"]
    states=sorted({(b["trend"],b["adx_band"],b["volatility"]) for b in background})
    for p in ("TRAIN","VALIDATION","TEST"):
      for side in ("CALL","PUT"):
       for trend,adxband,vol in states:
        sig=[r for r in records if r["period"]==p and r["direction"]==side and
             (r["features"]["trend"],r["features"]["adx_band"],r["features"]["volatility"])==(trend,adxband,vol)]
        bg=[b for b in background if b["period"]==p and not b["is_signal"] and
            (b["trend"],b["adx_band"],b["volatility"])==(trend,adxband,vol)]
        if len(bg)<20 or not sig: continue
        sw,sl,sd,swr,snet=summarize(sig)
        bw=sum(b["call_win"] if side=="CALL" else b["put_win"] for b in bg)
        bd=sum(b["draw"] for b in bg); bl=len(bg)-bw-bd
        bwr=100*bw/(bw+bl) if bw+bl else float("nan")
        lift=swr-bwr
        lines.append(f"| {p} | {side} | {trend}/{adxband}/{vol} | {len(sig)} | {sw}/{sl}/{sd} | {swr:.1f}% | {snet:+.2f}u | {len(bg)} | {bwr:.1f}% | {lift:+.1f} pp |")
    # Structural sweep interaction against an exact matched market baseline.
    # Unlike the earlier unconditional background, this conditions the baseline
    # on the same causal sweep state as the signal, direction, trend, ADX band,
    # and volatility tertile. Descriptive only; no rule is selected here.
    lines += ["","## Sweep-conditioned exact matched baseline","",
      "Each signal is compared with non-signal candles in the same period, direction, EMA trend, ADX band, prior-120 ATR/close tertile, and aligned-sweep YES/NO state. Background windows use the identical next-open to fourth-close horizon. Cells below 20 background observations are omitted.",
      "| Period | Direction | Trend | ADX | Vol | Sweep | Signal n | W/L/D | Signal WR | Net | Background n | Background WR | Lift |",
      "|---|---|---|---|---|---|---:|---|---:|---:|---:|---:|---:|"]
    for p in ("TRAIN","VALIDATION","TEST"):
      for side in ("CALL","PUT"):
       for trend in ("UP","DOWN","FLAT"):
        for adxband in ("15-20","20-25","25+"):
         for vol in ("LOW","MID","HIGH"):
          for sweep in ("YES","NO"):
           key=f"{side.lower()}_aligned12"
           sig=[r for r in records if r["period"]==p and r["direction"]==side and
                r["features"]["trend"]==trend and r["features"]["adx_band"]==adxband and
                r["features"]["volatility"]==vol and r["features"]["aligned_sweep_12"]==sweep]
           bg=[b for b in background if b["period"]==p and not b["is_signal"] and
               b["trend"]==trend and b["adx_band"]==adxband and b["volatility"]==vol and
               ("YES" if b[key] else "NO")==sweep]
           if len(bg)<20 or not sig: continue
           sw,sl,sd,swr,snet=summarize(sig)
           bw=sum(b["call_win"] if side=="CALL" else b["put_win"] for b in bg)
           bd=sum(b["draw"] for b in bg); bl=len(bg)-bw-bd
           bwr=100*bw/(bw+bl) if bw+bl else float("nan")
           lines.append(f"| {p} | {side} | {trend} | {adxband} | {vol} | {sweep} | {len(sig)} | {sw}/{sl}/{sd} | {swr:.1f}% | {snet:+.2f}u | {len(bg)} | {bwr:.1f}% | {swr-bwr:+.1f} pp |")
    # Also compare 12- and 24-bar structural sweeps at the signal level.
    lines += ["","## 12 vs 24-bar aligned sweep consistency","",
      "| Period | Direction | Sweep 12 | Sweep 24 | n | W/L/D | WR | Net |",
      "|---|---|---|---|---:|---|---:|---:|"]
    for p in ("TRAIN","VALIDATION","TEST"):
      for side in ("CALL","PUT"):
       for s12,s24 in (("YES","YES"),("YES","NO"),("NO","YES"),("NO","NO")):
        sub=[r for r in records if r["period"]==p and r["direction"]==side and
             r["features"]["aligned_sweep_12"]==s12 and r["features"]["aligned_sweep_24"]==s24]
        if len(sub)>=10:
         w,l,d,wr,net=summarize(sub)
         lines.append(f"| {p} | {side} | {s12} | {s24} | {len(sub)} | {w}/{l}/{d} | {wr:.1f}% | {net:+.2f}u |")
    # Month diagnostics: use all periods; useful to locate instability, not a filter.
    lines += ["","## Month-by-month 20m results","",
              "| Month UTC | Direction | n | W/L/D | Decisive WR | Net |",
              "|---|---|---:|---:|---:|---:|"]
    for month in sorted({r["time"].strftime("%Y-%m") for r in records}):
      for side in ("CALL","PUT"):
       sub=[r for r in records if r["time"].strftime("%Y-%m")==month and r["direction"]==side]
       if sub: lines.append(f"| {month} | {side} | {fmt(sub)} |")
    # Loss anatomy: compare only predictors observable at signal close.
    # Positive Cohen's d means the feature is higher before LOSS than WIN.
    lines += ["", "## Loss anatomy — pre-entry feature differences", "",
      "For each chronological split and direction, compare signal-close features before LOSS versus WIN. Draws are excluded. Cohen's d is descriptive (positive = higher before losses); it is not a causal effect or a filter-selection score. Only groups with at least 20 wins and 20 losses are shown.",
      "| Period | Direction | Feature | Loss n | Win n | Loss median | Win median | Cohen d |",
      "|---|---|---|---:|---:|---:|---:|---:|"]
    loss_effects = {}
    for p in ("TRAIN", "VALIDATION", "TEST"):
      for side in ("CALL", "PUT"):
        group = [r for r in records if r["period"] == p and r["direction"] == side]
        effects = []
        for key in numeric:
          losses = [float(r["features"][key]) for r in group if r["outcome"] == "LOSS" and r["features"][key] is not None]
          wins = [float(r["features"][key]) for r in group if r["outcome"] == "WIN" and r["features"][key] is not None]
          if len(losses) < 20 or len(wins) < 20: continue
          ml, mw = statistics.mean(losses), statistics.mean(wins)
          vl = statistics.pvariance(losses) if len(losses) > 1 else 0.0
          vw = statistics.pvariance(wins) if len(wins) > 1 else 0.0
          pooled = math.sqrt(((len(losses)-1)*vl + (len(wins)-1)*vw) / max(1, len(losses)+len(wins)-2))
          d = (ml-mw)/pooled if pooled > 1e-12 else 0.0
          medl, medw = statistics.median(losses), statistics.median(wins)
          effects.append((abs(d), key, len(losses), len(wins), medl, medw, d))
        loss_effects[(p, side)] = {x[1]: x[-1] for x in effects}
        # Print every eligible numeric feature, sorted by absolute effect size.
        for _, key, nl, nw, medl, medw, d in sorted(effects, reverse=True):
          lines.append(f"| {p} | {side} | {key} | {nl} | {nw} | {medl:.4g} | {medw:.4g} | {d:+.3f} |")
    lines += ["", "## Loss-risk quartiles — TRAIN thresholds held fixed", "",
      "Each numeric feature is divided using quartile cutoffs learned on TRAIN only. Loss rate = LOSS/(LOSS+WIN), excluding draws. This table describes where losses concentrate; it does not authorize a filter.",
      "| Period | Direction | Feature | Bin | n | Losses | Loss rate | Net |",
      "|---|---|---|---|---:|---:|---:|---:|"]
    for p in ("TRAIN", "VALIDATION", "TEST"):
      for side in ("CALL", "PUT"):
        for key in numeric:
          if edges.get(key) is None: continue
          for q in ("Q1", "Q2", "Q3", "Q4"):
            sub = [r for r in records if r["period"] == p and r["direction"] == side and bucket(r["features"][key], edges[key]) == q and r["outcome"] != "DRAW"]
            if len(sub) < 20: continue
            losses = sum(r["outcome"] == "LOSS" for r in sub)
            wins = len(sub) - losses
            net = wins * PAYOUT - losses
            lines.append(f"| {p} | {side} | {key} | {q} | {len(sub)} | {losses} | {100*losses/len(sub):.1f}% | {net:+.2f}u |")
    lines += ["", "## Cross-period direction of loss associations", "",
      "For each numeric feature, report the sign of Cohen's d (loss mean minus win mean) in TRAIN / VALIDATION / TEST. Same sign in all three periods is more interesting than a large isolated effect, but still requires prospective confirmation.",
      "| Direction | Feature | TRAIN d | VALIDATION d | TEST d | Same sign all periods |",
      "|---|---|---:|---:|---:|---|"]
    for side in ("CALL", "PUT"):
      for key in numeric:
        vals = [loss_effects.get((p, side), {}).get(key) for p in ("TRAIN", "VALIDATION", "TEST")]
        if any(v is None for v in vals): continue
        same = all(v > 0 for v in vals) or all(v < 0 for v in vals)
        lines.append(f"| {side} | {key} | {vals[0]:+.3f} | {vals[1]:+.3f} | {vals[2]:+.3f} | {'YES' if same else 'NO'} |")
    lines += ["","## Guardrails","",
      "- A subgroup is not a deployable filter merely because its historical WR exceeds 52.08%.",
      "- Compare the same subgroup across TRAIN, VALIDATION and TEST; instability is evidence against it.",
      "- Small cells, serial dependence and repeated exploratory comparisons make nominal subgroup rates optimistic.",
      "- No strategy parameter or application behavior is changed by this audit.",""]
    a.out.parent.mkdir(parents=True,exist_ok=True); report="\n".join(lines); a.out.write_text(report+"\n",encoding="utf-8"); print(report)

if __name__=="__main__": main()
