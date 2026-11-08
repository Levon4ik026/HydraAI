#!/usr/bin/env python3
"""Matched-control test: does the locked NY 08-12 PUT signal add information
beyond the same day/hour and the same ADX/DMI/momentum state?

Controls are non-signal M5 bars in the exact same New York local date and hour,
with the same causal state. Each selected candidate is matched to one control
without replacement, with overlapping 20m outcome windows prohibited. Matching
uses nearest standardized ADX, DI spread and 12-bar momentum. This is a locked
diagnostic; no thresholds are tuned.
"""
from __future__ import annotations
import argparse, math, random
from collections import defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo
from long_history_validation import read_duka, make_events, m5_close_time
from reproduce_m5_bb_williams_adx import make_m5, indicators

NY = ZoneInfo("America/New_York")
H = 4
PAYOUT = 0.92
REPS = 10000
SEED = 271828

def outcome(bars, i):
    delta = bars[i+H].close - bars[i+1].open
    return "DRAW" if abs(delta) < 1e-12 else "WIN" if delta < 0 else "LOSS"

def net(rows):
    return sum(PAYOUT if r["outcome"] == "WIN" else -1.0 if r["outcome"] == "LOSS" else 0.0 for r in rows)

def stats(rows):
    w=sum(r["outcome"]=="WIN" for r in rows)
    l=sum(r["outcome"]=="LOSS" for r in rows)
    d=sum(r["outcome"]=="DRAW" for r in rows)
    dec=w+l
    wr=100*w/dec if dec else float("nan")
    if dec:
        p=w/dec; z=1.959963984540054; den=1+z*z/dec
        mid=(p+z*z/(2*dec))/den
        half=z*math.sqrt(p*(1-p)/dec+z*z/(4*dec*dec))/den
        ci=f"[{100*(mid-half):.2f},{100*(mid+half):.2f}]"
    else: ci="n/a"
    return w,l,d,wr,ci,net(rows), (w*PAYOUT/l if l else (float("inf") if w else 0.0))

def period(ts, end, d1, d2):
    if ts.date() < d1: return None if end.date() >= d1 else "TRAIN"
    if ts.date() < d2: return None if end.date() >= d2 else "VALIDATION"
    return "TEST"

def bootstrap_days(pairs, reps=REPS, block=5, seed=SEED):
    byday=defaultdict(list)
    for p in pairs: byday[p["date"]].append(p["diff"])
    days=sorted(byday)
    if not days: return float("nan"),float("nan"),float("nan"),float("nan")
    rng=random.Random(seed); samples=[]
    for _ in range(reps):
        chosen=[]
        while len(chosen)<len(days):
            k=rng.randrange(len(days))
            chosen.extend(days[(k+j)%len(days)] for j in range(block))
        vals=[v for day in chosen[:len(days)] for v in byday[day]]
        samples.append(sum(vals)/len(vals) if vals else 0.0)
    samples.sort()
    allv=[v for day in days for v in byday[day]]
    return sum(allv)/len(allv), samples[int(.025*reps)], samples[int(.975*reps)], len(days)

def cluster_signflip_p(pairs, reps=REPS, seed=SEED+1):
    byday=defaultdict(list)
    for p in pairs: byday[p["date"]].append(p["diff"])
    vals=[sum(x) for x in byday.values()]
    if not vals: return float("nan")
    observed=sum(vals)
    rng=random.Random(seed); exceed=0
    for _ in range(reps):
        s=sum(v if rng.random()<0.5 else -v for v in vals)
        if s >= observed-1e-12: exceed+=1
    return (exceed+1)/(reps+1)

def fmt(label, rows):
    w,l,d,wr,ci,n,pf=stats(rows)
    return f"| {label} | {len(rows)} | {w}/{l}/{d} | {wr:.2f}% | {ci} | {n:+.2f}u | {pf:.2f} |"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--out",type=Path,default=Path("research/NY_PUT_MATCHED_CONTROL_AUDIT.md"))
    args=ap.parse_args()
    m1=read_duka(args.data); segments=make_m5(m1); events=make_events(segments,15)
    event_map={(e["segment"],e["bar_index"]):e for e in events}
    event_keys=set(event_map)
    days=sorted({e["signal_time"].date() for e in events})
    d1,d2=days[int(.60*len(days))],days[int(.80*len(days))]
    candidates=[]; controls=[]
    for sid,bars in enumerate(segments):
        ind=indicators(bars)
        for i in range(50,len(bars)-H):
            ts=bars[i].timestamp; local=ts.astimezone(NY)
            if not 8 <= local.hour < 13: continue
            x=ind[i]
            if x["adx"] is None or x["plus_di"] is None or x["minus_di"] is None: continue
            if not (x["adx"]>=25 and x["plus_di"]>x["minus_di"] and bars[i].close>bars[i-12].close): continue
            end=m5_close_time(bars[i+H].timestamp)
            p=period(ts,end,d1,d2)
            if p is None: continue
            mom=10000.0*(bars[i].close-bars[i-12].close)/bars[i].close
            r={"sid":sid,"i":i,"date":local.date(),"hour":local.hour,"period":p,
               "adx":x["adx"],"di_gap":x["plus_di"]-x["minus_di"],"mom":mom,
               "outcome":outcome(bars,i)}
            if (sid,i) in event_keys:
                # Only PUT signals are candidates; CALL signals are not controls.
                e=event_map.get((sid,i))
                if e and e["direction"]=="PUT": candidates.append(r)
            else:
                controls.append(r)

    # One-position candidate schedule, globally per continuous segment.
    chosen=[]; byseg=defaultdict(list)
    for r in candidates: byseg[r["sid"]].append(r)
    for sid,rs in byseg.items():
        allowed=-1
        for r in sorted(rs,key=lambda z:z["i"]):
            if r["i"]>=allowed:
                chosen.append(r); allowed=r["i"]+H

    # Exclude control bars whose 20m outcomes overlap any candidate signal
    # window. Then match greedily within the same NY date/hour and split.
    all_cand_intervals=defaultdict(list)
    for r in candidates: all_cand_intervals[r["sid"]].append((r["i"],r["i"]+H))
    def overlaps_any(r):
        return any(not (r["i"]+H < a or r["i"] > b)
                   for a,b in all_cand_intervals[r["sid"]])
    ctrl_pool=[r for r in controls if not overlaps_any(r)]
    features=("adx","di_gap","mom")
    pool_values={k:[r[k] for r in chosen+ctrl_pool] for k in features}
    scales={}
    for k,vs in pool_values.items():
        mean=sum(vs)/len(vs) if vs else 0.0
        sd=math.sqrt(sum((v-mean)**2 for v in vs)/len(vs)) if vs else 1.0
        scales[k]=sd or 1.0
    used=set(); pairs=[]
    ctrl_by_key=defaultdict(list)
    for c in ctrl_pool: ctrl_by_key[(c["date"],c["hour"],c["period"],c["sid"])].append(c)
    for c in sorted(chosen,key=lambda z:(z["date"],z["hour"],z["sid"],z["i"])):
        key=(c["date"],c["hour"],c["period"],c["sid"])
        options=[]
        for q in ctrl_by_key.get(key,[]):
            qid=(q["sid"],q["i"])
            if qid in used or q["i"] < c["i"]-H or q["i"] > c["i"]+H: continue
            # Also prohibit overlapping control expiry windows with previous controls.
            if any(q["sid"]==p["control"]["sid"] and not (q["i"]+H < p["control"]["i"] or q["i"] > p["control"]["i"]+H) for p in pairs):
                continue
            dist=sum(((c[k]-q[k])/scales[k])**2 for k in features)
            options.append((dist,q))
        if not options: continue
        _,q=min(options,key=lambda z:z[0])
        used.add((q["sid"],q["i"]))
        pairs.append({"date":c["date"],"period":c["period"],"candidate":c,"control":q,
                      "diff":(PAYOUT if c["outcome"]=="WIN" else -1 if c["outcome"]=="LOSS" else 0) -
                             (PAYOUT if q["outcome"]=="WIN" else -1 if q["outcome"]=="LOSS" else 0)})

    lines=["# HYDRA — New York PUT matched-control audit","",
      f"Data: Dukascopy EURUSD M1 BID; rows={len(m1):,}; M5 bars={sum(map(len,segments)):,}; segments={len(segments):,}.",
      f"Coverage: {m1[0].timestamp.isoformat()} — {m1[-1].timestamp.isoformat()}.",
      f"Split: TRAIN < {d1}; VALIDATION < {d2}; TEST >= {d2}. New York local time via America/New_York (DST-aware).",
      "Locked candidate: frozen BB/Williams/ADX PUT event, NY 08:00-12:59, ADX>=25, +DI>-DI, close[i]>close[i-12].",
      "Control: non-signal bar in the same continuous segment, same NY calendar date, same NY clock hour, same split, same ADX/DMI/momentum state; matched nearest on standardized ADX, DI gap and 12-bar momentum.",
      "Entry next M5 open; settle fourth following M5 close (20m); PUT direction evaluated from BID close. Payout 92%.",
      "Both candidate and control schedules are non-overlapping; controls are not reused and are excluded if their expiry overlaps any candidate expiry. Greedy matching is chronological, with no outcome-based matching.",
      "This tests incremental signal information conditional on local date/hour and coarse state; it does not establish Pocket Option execution profitability.","",
      "## Matched sample performance","",
      "| Split / sample | n | W/L/D | WR | Wilson 95% CI | Net @92% | PF |",
      "|---|---:|---:|---:|---:|---:|---:|"]
    for p in ("TRAIN","VALIDATION","TEST","ALL"):
        ps=[x for x in pairs if p=="ALL" or x["period"]==p]
        cr=[x["candidate"] for x in ps]; qr=[x["control"] for x in ps]
        lines.append(fmt(f"{p} candidate",cr)); lines.append(fmt(f"{p} matched control",qr))
    lines += ["","## Paired incremental effect","",
      "| Split | Matched pairs | Mean candidate-minus-control net per pair | 5-day block bootstrap 95% CI | Active days | Cluster sign-flip p (one-sided) |",
      "|---|---:|---:|---:|---:|---:|"]
    for p in ("TRAIN","VALIDATION","TEST","ALL"):
        ps=[x for x in pairs if p=="ALL" or x["period"]==p]
        mean,lo,hi,nd=bootstrap_days(ps,seed=SEED+len(ps))
        pv=cluster_signflip_p(ps,seed=SEED+len(ps)+1)
        lines.append(f"| {p} | {len(ps)} | {mean:+.3f}u | [{lo:+.3f},{hi:+.3f}] | {nd} | {pv:.4f} |")
    lines += ["","## Pair-level outcomes","",
      "| Split | Candidate win / control loss | Candidate loss / control win | Same outcome |",
      "|---|---:|---:|---:|"]
    for p in ("TRAIN","VALIDATION","TEST","ALL"):
        ps=[x for x in pairs if p=="ALL" or x["period"]==p]
        a=sum(x["candidate"]["outcome"]=="WIN" and x["control"]["outcome"]=="LOSS" for x in ps)
        b=sum(x["candidate"]["outcome"]=="LOSS" and x["control"]["outcome"]=="WIN" for x in ps)
        s=len(ps)-a-b
        lines.append(f"| {p} | {a} | {b} | {s} |")
    lines += ["","## Monthly TEST paired differences","",
      "| Month | Pairs | Mean net difference / pair | Sum difference |",
      "|---|---:|---:|---:|"]
    months=defaultdict(list)
    for x in pairs:
        if x["period"]=="TEST": months[x["date"].strftime("%Y-%m")].append(x)
    for mon,ps in sorted(months.items()):
        lines.append(f"| {mon} | {len(ps)} | {sum(x['diff'] for x in ps)/len(ps):+.3f}u | {sum(x['diff'] for x in ps):+.2f}u |")
    lines += ["","## Interpretation limits","",
      "- A positive paired difference with a block-bootstrap interval above zero and a small cluster sign-flip p-value is evidence that the frozen signal adds information beyond matched same-day/hour/state controls.",
      "- Small or unmatched samples are inconclusive; do not optimize matching variables or thresholds on these results.",
      "- The candidate was found in prior exploratory work; this remains retrospective validation, not an untouched prospective test.",
      "- Dukascopy BID is not Pocket Option's exact quote feed. No production or local files changed; no orders were placed.",""]
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text("\n".join(lines),encoding="utf-8")
    print(f"candidate_events={len(candidates)}; nonoverlap_candidates={len(chosen)}; matched_pairs={len(pairs)}; wrote {args.out}")

if __name__=="__main__": main()
