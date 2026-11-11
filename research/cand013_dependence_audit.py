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
from datetime import timedelta
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

def metrics(rows):
    s=stats([r["result"] for r in rows])
    return {"n":s[0],"w":s[1],"l":s[2],"d":s[3],"wr":s[4],"net":s[6],"dd":s[7],"streak":s[8]}

def fmt(m):
    wr="n/a" if m["wr"] is None else f'{m["wr"]:.2f}%'
    return f'N={m["n"]} W/L/D={m["w"]}/{m["l"]}/{m["d"]} WR={wr} Net={m["net"]:+.2f}u'

def day_block_sample(days, block, rng):
    n=len(days)
    if not n: return []
    out=[]
    while len(out)<n:
        start=rng.randrange(n)
        out.extend(days[(start+k)%n] for k in range(block))
    return out[:n]

def decisive_wr(rows):
    w=sum(r["result"]=="W" for r in rows)
    l=sum(r["result"]=="L" for r in rows)
    return 100*w/(w+l) if w+l else None

def bootstrap(rows, block, reps, seed):
    """Circular moving-block bootstrap over calendar days, retaining within-day clusters."""
    byday=defaultdict(list)
    for r in rows: byday[r["day"]].append(r)
    days=sorted(byday)
    if len(days)<block*2: return None
    rng=random.Random(seed)
    wrs=[]; nets=[]
    for _ in range(reps):
        sampled=day_block_sample(days,block,rng)
        sample=[r for d in sampled for r in byday[d]]
        m=metrics(sample)
        if m["wr"] is not None:
            wrs.append(m["wr"]); nets.append(m["net"])
    if not wrs:return None
    return (quantile(wrs,.025),quantile(wrs,.975),quantile(nets,.025),quantile(nets,.975))

def paired_difference_bootstrap(rows, block, reps, seed):
    """Analog minus non-analog decisive WR on the same sampled calendar blocks."""
    byday=defaultdict(list)
    for r in rows: byday[r["day"]].append(r)
    days=sorted(byday)
    if len(days)<block*2:return None
    rng=random.Random(seed); diffs=[]
    for _ in range(reps):
        sampled=day_block_sample(days,block,rng)
        sample=[r for d in sampled for r in byday[d]]
        a=[r for r in sample if r["analog"]]
        c=[r for r in sample if not r["analog"]]
        wa,wc=decisive_wr(a),decisive_wr(c)
        if wa is not None and wc is not None: diffs.append(wa-wc)
    if not diffs:return None
    return quantile(diffs,.025),quantile(diffs,.975),sum(d>0 for d in diffs)/len(diffs)*100

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--data",type=Path,required=True); p.add_argument("--out",type=Path,required=True)
    p.add_argument("--reps",type=int,default=10000); a=p.parse_args()
    m1=read_m1(a.data); segments=make_m5(m1)
    dates=sorted({b.timestamp.date() for seg in segments for b in seg})
    d1,d2=dates[int(.60*len(dates))],dates[int(.80*len(dates))]
    rows=[]
    for sid,bars in enumerate(segments):
        events=build_events(bars); closes=[b.close for b in bars]; ema20=ema_series(closes)
        tr=[]
        for i,b in enumerate(bars):
            if i==0:tr.append(b.high-b.low)
            else:
                prev=bars[i-1].close
                tr.append(max(b.high-b.low,abs(b.high-prev),abs(b.low-prev)))
        raw=[]
        for i,_side in events.get(NAME,[]):
            if i+H>=len(bars):continue
            ts=bars[i].timestamp; settle_day=(bars[i+H].timestamp+timedelta(minutes=5)).date()
            day=ts.date()
            split="TRAIN" if day<d1 else "VALIDATION" if day<d2 else "TEST"
            if (split=="TRAIN" and settle_day>=d1) or (split=="VALIDATION" and settle_day>=d2):continue
            f=causal_features(bars,i,tr,ema20)
            if f is None:continue
            raw.append({"i":i,"ts":ts,"day":day,"month":ts.strftime("%Y-%m"),"split":split,
                        "result":outcome(bars,i,"PUT",H),"features":f,"segment":sid})
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
    analog=[r for r in historical if r["analog"]]
    control=[r for r in historical if not r["analog"]]
    lines=["# HYD-CAND-013 — dependence-aware situation audit","",
      f"Data: Dukascopy EUR/USD M1 BID; M1={len(m1):,}; M5={sum(map(len,segments)):,}; segments={len(segments)}.",
      f"Splits: TRAIN < {d1}; VALIDATION {d1}–{d2}; TEST >= {d2}; boundary-crossing outcomes purged.",
      "Frozen candidate/profile: same R2.0/C0.75 inverse PUT, 20m expiry, next-M5-open entry, 92% assumed payout; seed profile and radius unchanged from prior audit.",
      f"Seed: May+October 2026 TEST; N={len(seeds)}; profile radius={radius:.6f}. These seed months are exploratory and not independent confirmation.",
      "Bootstrap: circular moving blocks of calendar days; 10,000 replicates by default. 5-day and 10-day blocks preserve within-day clustering and short-range serial dependence; intervals are percentile intervals, not a cure for selection bias.",
      "Control: candidate events outside the frozen analog radius, same split and execution rules. Control count is small; compare cautiously.",
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
    lines += ["", "## Split performance and day-block bootstrap","",
      "| Split/cohort | N | WR | Net u | 5d WR 95% CI | 10d WR 95% CI | 5d net 95% CI | 10d net 95% CI |",
      "|---|---:|---:|---:|---|---|---|---|"]
    cohorts=[("TRAIN analog",[r for r in analog if r["split"]=="TRAIN"]),
             ("VALIDATION analog",[r for r in analog if r["split"]=="VALIDATION"]),
             ("TRAIN+VALIDATION analog",analog),
             ("TRAIN+VALIDATION control",control)]
    for idx,(name,rs) in enumerate(cohorts):
        m=metrics(rs); b5=bootstrap(rs,5,a.reps,1000+idx);b10=bootstrap(rs,10,a.reps,2000+idx)
        def ci(b,k1,k2):
            return "n/a" if b is None else f"[{b[k1]:.2f},{b[k2]:.2f}]"
        wr="n/a" if m["wr"] is None else f'{m["wr"]:.2f}%'
        lines.append(f'| {name} | {m["n"]} | {wr} | {m["net"]:+.2f} | {ci(b5,0,1)} | {ci(b10,0,1)} | {ci(b5,2,3)} | {ci(b10,2,3)} |')
    lines += ["", "## Paired analog-vs-control day-block comparison","",
      "| Split | Observed WR gap (pp) | 5d bootstrap 95% CI | 10d bootstrap 95% CI | P(gap>0) 5d / 10d |",
      "|---|---:|---|---|---:|"]
    for idx,sp in enumerate(("TRAIN","VALIDATION","TRAIN+VALIDATION")):
        rs=[r for r in historical if sp=="TRAIN+VALIDATION" or r["split"]==sp]
        ma=metrics([r for r in rs if r["analog"]]);mc=metrics([r for r in rs if not r["analog"]])
        gap=(ma["wr"]-mc["wr"]) if ma["wr"] is not None and mc["wr"] is not None else float("nan")
        b5=paired_difference_bootstrap(rs,5,a.reps,3000+idx)
        b10=paired_difference_bootstrap(rs,10,a.reps,4000+idx)
        def fmtb(b):return "n/a" if b is None else f"[{b[0]:.2f},{b[1]:.2f}]"
        prob="n/a" if b5 is None or b10 is None else f"{b5[2]:.1f}% / {b10[2]:.1f}%"
        lines.append(f"| {sp} | {gap:+.2f} | {fmtb(b5)} | {fmtb(b10)} | {prob} |")
    lines += ["", "## Interpretation guardrails","",
      "- A Validation result that is strong but absent in TRAIN is period-dependent evidence, not a confirmed stable situation-strategy pair.",
      "- Monthly rows expose concentration; sparse months are not standalone evidence.",
      "- Day-block bootstrap intervals quantify sampling variability under short-range dependence, but do not correct retrospective seed selection, broad candidate search, or market-feed mismatch.",
      "- A positive paired analog-control gap is useful only if both groups have adequate representation across dates; control N and active days must be considered.",
      "- May/October seed cohorts remain contaminated for independent confirmation because they defined the profile.",
      "- Next legitimate confirmation must use a future untouched period or prospective Pocket Option demo quote capture; no changes to the candidate/profile before that.",""]
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text("\n".join(lines),encoding="utf-8")
    print(f"HYD-CAND-013 dependence audit complete: historical={len(historical)} analog={len(analog)} control={len(control)} report={a.out}")

if __name__=="__main__":main()
