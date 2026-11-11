#!/usr/bin/env python3
"""Dependence-aware follow-up audit for frozen HYD-CAND-013 situation profile.

The May/October TEST seed profile and candidate definition are not refit here.
This audit reports calendar-month concentration and moving calendar-day block
bootstrap intervals for analogs and their same-split non-analog candidate controls.
Research only; no production or execution changes.
"""
from __future__ import annotations
import argparse, math, random
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from statistics import median

from expanded_strategy_screen import read_m1, outcome, stats
from long_history_validation import make_m5
from eleventh_wave_impulse_screen import build_events

NAME = "BULL_IMPULSE_CONT_R2.0_C0.75"
H = 4
PAYOUT = 0.92
SEED_MONTHS = {"2026-05", "2026-10"}
FEATURES = ("efficiency_12","return_12_atr","volatility_12_vs_prior60",
            "range_position_24","ema20_gap_atr","ema20_slope6_atr")

def quantile(xs, q):
    ys=sorted(float(x) for x in xs if math.isfinite(float(x)))
    if not ys: return float("nan")
    p=(len(ys)-1)*q; lo=int(p); hi=min(lo+1,len(ys)-1)
    return ys[lo]+(ys[hi]-ys[lo])*(p-lo)

def ema_series(values, period=20):
    alpha=2.0/(period+1.0); out=[]; value=None
    for x in values:
        value=float(x) if value is None else alpha*float(x)+(1-alpha)*value
        out.append(value)
    return out

def causal_features(bars,i,tr,ema20):
    if i<72: return None
    atr20=sum(tr[i-20:i])/20.0
    if atr20<=0: return None
    net12=bars[i-1].close-bars[i-13].close
    path12=sum(abs(bars[j].close-bars[j-1].close) for j in range(i-12,i))
    hi24=max(b.high for b in bars[i-24:i]); lo24=min(b.low for b in bars[i-24:i])
    span24=hi24-lo24; prior60=sum(tr[i-72:i-12])/60.0
    recent12=sum(tr[i-12:i])/12.0
    if span24<=0 or prior60<=0: return None
    return {"efficiency_12":abs(net12)/path12 if path12>0 else 0.0,
            "return_12_atr":net12/atr20,
            "volatility_12_vs_prior60":recent12/prior60,
            "range_position_24":(bars[i-1].close-lo24)/span24,
            "ema20_gap_atr":(bars[i-1].close-ema20[i-1])/atr20,
            "ema20_slope6_atr":(ema20[i-1]-ema20[i-7])/atr20}

def metrics(rows, outcome_key="result"):
    vals = [r[outcome_key] for r in rows]
    s = stats(vals)
    n, w, l, d, wr, ci, net, dd, streak = s
    pf = (w * PAYOUT / l) if l else (float("inf") if w else None)
    return {
        "n": n, "w": w, "l": l, "d": d, "wr": wr, "ci": ci,
        "w_all": (100.0 * w / n) if n else None,
        "net": net, "roi": (100.0 * net / n) if n else None,
        "pf": pf, "dd": dd, "streak": streak,
    }


def fmt(m):
    wr = "n/a" if m["wr"] is None else f'{m["wr"]:.2f}%'
    ci = "n/a" if m["ci"] is None else f'[{m["ci"][0]:.2f},{m["ci"][1]:.2f}]%'
    wall = "n/a" if m["w_all"] is None else f'{m["w_all"]:.2f}%'
    roi = "n/a" if m["roi"] is None else f'{m["roi"]:+.2f}%'
    pf = "n/a" if m["pf"] is None else ("inf" if math.isinf(m["pf"]) else f'{m["pf"]:.2f}')
    return (f'N={m["n"]} W/L/D={m["w"]}/{m["l"]}/{m["d"]} '
            f'WR={wr} Wilson95={ci} W/all={wall} Net={m["net"]:+.2f}u '
            f'ROI={roi} PF={pf} MaxDD={m["dd"]:.2f}u MaxLossStreak={m["streak"]}')


def calendar_days(start, end):
    if end < start:
        return []
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def day_block_sample(days, block, rng):
    """Sample non-wrapping contiguous blocks from a complete calendar-day grid."""
    n = len(days)
    if block < 1 or n < block:
        raise ValueError("calendar grid must contain at least one full block")
    out = []
    while len(out) < n:
        start = rng.randrange(0, n - block + 1)
        out.extend(days[start:start + block])
    return out[:n]


def decisive_wr(rows, outcome_key="result"):
    w = sum(r[outcome_key] == "W" for r in rows)
    l = sum(r[outcome_key] == "L" for r in rows)
    return 100.0 * w / (w + l) if w + l else None


def _sample_rows_by_split(rows, block, rng, split_ranges):
    """Resample full UTC calendar-day grids separately within each chronological split."""
    by_split_day = defaultdict(list)
    for r in rows:
        by_split_day[(r["split"], r["day"])].append(r)
    sampled_rows = []
    for split in sorted({r["split"] for r in rows}):
        if split not in split_ranges:
            raise ValueError(f"missing calendar range for split {split}")
        start, end = split_ranges[split]
        days = calendar_days(start, end)
        if len(days) < 2 * block:
            return None
        for day in day_block_sample(days, block, rng):
            sampled_rows.extend(by_split_day.get((split, day), []))
    return sampled_rows


def bootstrap(rows, block, reps, seed, split_ranges, outcome_key="result"):
    """Moving-block bootstrap over actual UTC calendar days, including zero-trade days."""
    if not rows:
        return None
    rng = random.Random(seed)
    wrs, nets = [], []
    for _ in range(reps):
        sample = _sample_rows_by_split(rows, block, rng, split_ranges)
        if sample is None:
            return None
        m = metrics(sample, outcome_key)
        if m["wr"] is not None:
            wrs.append(m["wr"])
            nets.append(m["net"])
    if not wrs:
        return None
    return (quantile(wrs, .025), quantile(wrs, .975),
            quantile(nets, .025), quantile(nets, .975))


def paired_difference_bootstrap(rows, block, reps, seed, split_ranges, outcome_key="result"):
    """Paired analog-minus-control WR on identical sampled calendar blocks."""
    if not rows:
        return None
    rng = random.Random(seed)
    diffs = []
    for _ in range(reps):
        sample = _sample_rows_by_split(rows, block, rng, split_ranges)
        if sample is None:
            return None
        analog_rows = [r for r in sample if r["analog"]]
        control_rows = [r for r in sample if not r["analog"]]
        wa = decisive_wr(analog_rows, outcome_key)
        wc = decisive_wr(control_rows, outcome_key)
        if wa is not None and wc is not None:
            diffs.append(wa - wc)
    if not diffs:
        return None
    return (quantile(diffs, .025), quantile(diffs, .975),
            100.0 * sum(d > 0 for d in diffs) / len(diffs))


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--data",type=Path,required=True); p.add_argument("--out",type=Path,required=True)
    p.add_argument("--reps",type=int,default=10000); a=p.parse_args()
    m1=read_m1(a.data); segments=make_m5(m1)
    dates=sorted({b.timestamp.date() for seg in segments for b in seg})
    if not dates: raise SystemExit("No complete M5 dates in source data")
    # Keep the previously frozen chronological split boundaries exactly.
    d1,d2=date(2025,9,17),date(2026,4,14)
    rows=[]
    eligible_bars=defaultdict(int)
    for sid,bars in enumerate(segments):
        events=build_events(bars); closes=[b.close for b in bars]; ema20=ema_series(closes)
        tr=[]
        for i,b in enumerate(bars):
            if i==0:tr.append(b.high-b.low)
            else:
                prev=bars[i-1].close
                tr.append(max(b.high-b.low,abs(b.high-prev),abs(b.low-prev)))
        raw=[]
        # Denominator for candidate signal frequency: all feature-ready M5
        # signal bars with a valid 20m settlement inside the same split/segment.
        for i in range(72, len(bars)-H):
            day=bars[i].timestamp.date()
            split="TRAIN" if day<d1 else "VALIDATION" if day<d2 else "TEST"
            settle_day=(bars[i+H].timestamp+timedelta(minutes=5)).date()
            if (split=="TRAIN" and settle_day>=d1) or (split=="VALIDATION" and settle_day>=d2):
                continue
            eligible_bars[split]+=1
        for i,_side in events.get(NAME,[]):
            if i+H>=len(bars):continue
            ts=bars[i].timestamp; settle_day=(bars[i+H].timestamp+timedelta(minutes=5)).date()
            day=ts.date()
            split="TRAIN" if day<d1 else "VALIDATION" if day<d2 else "TEST"
            if (split=="TRAIN" and settle_day>=d1) or (split=="VALIDATION" and settle_day>=d2):continue
            f=causal_features(bars,i,tr,ema20)
            if f is None:continue
            put_result=outcome(bars,i,"PUT",H)
            call_result={"W":"L","L":"W","D":"D"}[put_result]
            raw.append({"i":i,"ts":ts,"day":day,"month":ts.strftime("%Y-%m"),"split":split,
                        "result":put_result,"result_call":call_result,"features":f,"segment":sid})
        for split in ("TRAIN","VALIDATION","TEST"):
            nxt=-1
            for r in sorted((x for x in raw if x["split"]==split),key=lambda x:x["i"]):
                if r["i"]<nxt:continue
                nxt=r["i"]+H; rows.append(r)
    seeds=[r for r in rows if r["split"]=="TEST" and r["month"] in SEED_MONTHS]
    train=[r for r in rows if r["split"]=="TRAIN"]
    val=[r for r in rows if r["split"]=="VALIDATION"]
    if len(seeds)<30 or len(train)<100 or len(val)<50:raise SystemExit("Insufficient seed/train/validation data")
    scale={}
    for f in FEATURES:
        q1=quantile([r["features"][f] for r in train],.25);q3=quantile([r["features"][f] for r in train],.75)
        scale[f]=max(q3-q1,1e-6)
    center={f:median([r["features"][f] for r in seeds]) for f in FEATURES}
    def dist(r):return math.sqrt(sum(((r["features"][f]-center[f])/scale[f])**2 for f in FEATURES)/len(FEATURES))
    radius=quantile([dist(r) for r in seeds],.90)
    historical=[r for r in rows if r["split"] in ("TRAIN","VALIDATION")]
    for r in historical:r["analog"]=dist(r)<=radius
    split_ranges={
        "TRAIN":(dates[0],d1-timedelta(days=1)),
        "VALIDATION":(d1,d2-timedelta(days=1)),
        "TEST":(d2,dates[-1]),
    }
    analog=[r for r in historical if r["analog"]]
    control=[r for r in historical if not r["analog"]]
    lines=["# HYD-CAND-013 — dependence-aware situation audit","",
      f"Data: Dukascopy EUR/USD M1 BID; M1={len(m1):,}; M5={sum(map(len,segments)):,}; segments={len(segments)}.",
      f"Splits: TRAIN < {d1}; VALIDATION {d1}–{d2}; TEST >= {d2}; boundary-crossing outcomes purged.",
      "Frozen candidate/profile: same R2.0/C0.75 inverse PUT, 20m expiry, next-M5-open entry, 92% assumed payout; seed profile and radius unchanged from prior audit.",
      f"Seed: May+October 2026 TEST; N={len(seeds)}; profile radius={radius:.6f}. These seed months are exploratory and not independent confirmation.",
      "Bootstrap: non-wrapping moving blocks over complete UTC calendar-day grids, including zero-event dates; TRAIN and VALIDATION are resampled separately in combined estimates. 5-day and 10-day blocks preserve within-day clustering and short-range calendar dependence; intervals are percentile intervals, not a cure for selection bias.",
      f"Historical candidate-event analog coverage: {len(analog)}/{len(historical)} ({100*len(analog)/len(historical):.2f}%); control share={100*len(control)/len(historical):.2f}%. The small control cohort limits matched comparisons.",
      "Control: candidate events outside the frozen analog radius, same split and execution rules. This is a candidate-event control, not a matched all-market baseline.",
      "No month/weekday filtering or candidate parameter changes. Dukascopy BID proxy; fixed 92% payout; no Pocket Option execution model.","",
      "## Seed cohort (feature-complete events)",""]
    for mo in sorted(SEED_MONTHS):
        lines.append(f"- {mo}: {fmt(metrics([r for r in seeds if r['month']==mo]))}")
    lines += ["", "## Monthly analog breakdown (historical TRAIN + VALIDATION)","",
      "| Month | Split | N | W/L/D | WR | Net u |",
      "|---|---|---:|---|---:|---:|"]
    monthly=defaultdict(list)
    for r in analog:monthly[(r["month"],r["split"])].append(r)
    for (mo,sp),rs in sorted(monthly.items()):
        m=metrics(rs);wr="n/a" if m["wr"] is None else f'{m["wr"]:.2f}%'
        lines.append(f'| {mo} | {sp} | {m["n"]} | {m["w"]}/{m["l"]}/{m["d"]} | {wr} | {m["net"]:+.2f} |')
    lines += ["", "## Split performance by direction and activity","",
      "| Split/cohort | Side | N | W/L/D | Decisive WR [Wilson 95%] | W/all | Net | ROI | PF | MaxDD | Loss streak | Signal freq | WAIT | Active/calendar days |",
      "|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    cohorts=[
        ("TRAIN analog",[r for r in analog if r["split"]=="TRAIN"],("TRAIN",)),
        ("VALIDATION analog",[r for r in analog if r["split"]=="VALIDATION"],("VALIDATION",)),
        ("TRAIN+VALIDATION analog",analog,("TRAIN","VALIDATION")),
        ("TRAIN+VALIDATION control",control,("TRAIN","VALIDATION")),
    ]
    for name,rs,splits in cohorts:
        denominator=sum(eligible_bars[s] for s in splits)
        calendar_count=sum(len(calendar_days(*split_ranges[s])) for s in splits)
        active_days=len({r["day"] for r in rs})
        for side,key in (("PUT inverse","result"),("CALL original","result_call")):
            m=metrics(rs,key)
            freq=100.0*m["n"]/denominator if denominator else 0.0
            wait=max(0.0,100.0-freq)
            ci="n/a" if m["ci"] is None else f'[{m["ci"][0]:.2f},{m["ci"][1]:.2f}]%'
            wr="n/a" if m["wr"] is None else f'{m["wr"]:.2f}%'
            wall="n/a" if m["w_all"] is None else f'{m["w_all"]:.2f}%'
            roi="n/a" if m["roi"] is None else f'{m["roi"]:+.2f}%'
            pf="n/a" if m["pf"] is None else ("inf" if math.isinf(m["pf"]) else f'{m["pf"]:.2f}')
            lines.append(f'| {name} | {side} | {m["n"]} | {m["w"]}/{m["l"]}/{m["d"]} | {wr} {ci} | {wall} | {m["net"]:+.2f}u | {roi} | {pf} | {m["dd"]:.2f}u | {m["streak"]} | {freq:.3f}% | {wait:.3f}% | {active_days}/{calendar_count} |')
    lines += ["", "## PUT inverse day-block bootstrap","",
      "| Split/cohort | N | WR 5d 95% CI | WR 10d 95% CI | Net 5d 95% CI | Net 10d 95% CI |",
      "|---|---:|---|---|---|---|"]
    for idx,(name,rs,_splits) in enumerate(cohorts):
        b5=bootstrap(rs,5,a.reps,1000+idx,split_ranges)
        b10=bootstrap(rs,10,a.reps,2000+idx,split_ranges)
        def ci(b,k1,k2):
            return "n/a" if b is None else f"[{b[k1]:.2f},{b[k2]:.2f}]"
        lines.append(f'| {name} | {len(rs)} | {ci(b5,0,1)} | {ci(b10,0,1)} | {ci(b5,2,3)}u | {ci(b10,2,3)}u |')
    lines += ["", "## Paired analog-vs-control calendar-block comparison","",
      "| Split | Side | Observed WR gap (pp) | 5d bootstrap 95% CI | 10d bootstrap 95% CI | P(gap>0) 5d / 10d |",
      "|---|---|---:|---|---|---:|"]
    for idx,sp in enumerate(("TRAIN","VALIDATION","TRAIN+VALIDATION")):
        rs=[r for r in historical if sp=="TRAIN+VALIDATION" or r["split"]==sp]
        ma=metrics([r for r in rs if r["analog"]],"result")
        mc=metrics([r for r in rs if not r["analog"]],"result")
        for side,key,sign in (("PUT inverse","result",1),("CALL original","result_call",-1)):
            ma_side=metrics([r for r in rs if r["analog"]],key)
            mc_side=metrics([r for r in rs if not r["analog"]],key)
            gap=(ma_side["wr"]-mc_side["wr"]) if ma_side["wr"] is not None and mc_side["wr"] is not None else float("nan")
            b5=paired_difference_bootstrap(rs,5,a.reps,3000+idx,split_ranges,key)
            b10=paired_difference_bootstrap(rs,10,a.reps,4000+idx,split_ranges,key)
            def fmtb(b):return "n/a" if b is None else f"[{b[0]:.2f},{b[1]:.2f}]"
            prob="n/a" if b5 is None or b10 is None else f"{b5[2]:.1f}% / {b10[2]:.1f}%"
            lines.append(f"| {sp} | {side} | {gap:+.2f} | {fmtb(b5)} | {fmtb(b10)} | {prob} |")
    lines += ["", "## Interpretation guardrails","",
      "- A Validation result that is strong but absent in TRAIN is period-dependent evidence, not a confirmed stable situation-strategy pair.",
      "- Monthly rows expose concentration; sparse months are not standalone evidence.",
      "- Calendar-day blocks include zero-event days. These intervals quantify sampling variability under short-range dependence, but do not correct retrospective seed selection, broad candidate search, or market-feed mismatch.",
      "- A positive paired analog-control gap is useful only if both groups have adequate representation across dates; control N and active days must be considered.",
      "- May/October seed cohorts remain contaminated for independent confirmation because they defined the profile.",
      "- Next legitimate confirmation must use a future untouched period or prospective Pocket Option demo quote capture; no changes to the candidate/profile before that.",""]
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text("\n".join(lines),encoding="utf-8")
    print(f"HYD-CAND-013 dependence audit complete: historical={len(historical)} analog={len(analog)} control={len(control)} analog_share={100*len(analog)/len(historical):.2f}% report={a.out}")

if __name__=="__main__":main()
