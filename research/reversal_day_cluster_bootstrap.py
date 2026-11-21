#!/usr/bin/env python3
"""Day-cluster bootstrap for the TRAIN-frozen exact-reversal cohort."""
from __future__ import annotations
import argparse, random
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from reversal_strategy_audit import MIN_TRAIN_TRADES, MAX_TRAIN_WR, invert_outcome, build_records
from standalone_strategy_screen import make_m5, read_m1, summarize

B=5000
SEED=20261109

def pnl(value):
    return 0.92 if value=="W" else -1.0 if value=="L" else 0.0

def quantile(xs, q):
    ys=sorted(xs)
    pos=(len(ys)-1)*q
    lo=int(pos); hi=min(lo+1,len(ys)-1)
    return ys[lo]+(ys[hi]-ys[lo])*(pos-lo)

def write_report(path: Path, lines: list[str]) -> None:
    """Write a Markdown report with real line breaks."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--out",type=Path,default=Path("research/REVERSAL_DAY_BOOTSTRAP.md"))
    args=ap.parse_args()
    m1=read_m1(args.data); segments=make_m5(m1)
    d1,d2,accepted=build_records(segments)
    train={(n,h):summarize([r[6] for r in rows]) for (n,h,p),rows in accepted.items() if p=="TRAIN"}
    frozen=sorted(k for k,s in train.items() if s["n"]>=MIN_TRAIN_TRADES and s["wr"] is not None and s["wr"]<=MAX_TRAIN_WR and s["net"]<0)
    bars={sid:seg for sid,seg in enumerate(segments)}
    split_start={"TRAIN":m1[0].timestamp.date(),"VALIDATION":d1,"TEST":d2}
    split_end={"TRAIN":d1-timedelta(days=1),"VALIDATION":d2-timedelta(days=1),"TEST":m1[-1].timestamp.date()}
    lines=[
      "# Day-cluster bootstrap for exact reversals","",
      f"Source: {len(m1):,} valid M1; {sum(map(len,segments)):,} complete M5; coverage {m1[0].timestamp.isoformat()} to {m1[-1].timestamp.isoformat()}.",
      f"Frozen TRAIN-only cohort: n >= {MIN_TRAIN_TRADES}, original WR <= {MAX_TRAIN_WR:.4f}%, original net < 0.",
      f"Bootstrap: {B:,} resamples; resample UTC calendar days with replacement within each split; zero-trade days retained; seed={SEED}.",
      "Each day's P&L sums all exact inverse trades signalled that day. This preserves within-day clustering, but assumes daily clusters are exchangeable; multi-day dependence is not removed.",
      "Payout 92%; WIN +0.92u, LOSS -1u, DRAW 0u. Discovery screened 120 distinct strategy/expiry variants across 3 splits (360 variant/split rows); bootstrap does not correct this multiple-testing bias.",
      "",
      "| Strategy | Expiry | Split | Trades | Active days / calendar days | Net | Bootstrap 95% CI total net | P(net > 0) |",
      "|---|---:|---|---:|---:|---:|---:|---:|"
    ]
    rng=random.Random(SEED)
    for name,h in frozen:
      for period in ("TRAIN","VALIDATION","TEST"):
        rows=accepted.get((name,h,period),[])
        if not rows: continue
        start=split_start[period]; end=split_end[period]
        n_days=(end-start).days+1
        day_net=defaultdict(float)
        for row in rows:
          day=bars[row[2]][row[3]].timestamp.date()
          day_net[day]+=pnl(invert_outcome(row[6]))
        vals=[day_net.get(start+timedelta(days=i),0.0) for i in range(n_days)]
        total=sum(vals); sims=[]
        for _ in range(B):
          sims.append(sum(vals[rng.randrange(n_days)] for __ in range(n_days)))
        lo=quantile(sims,.025); hi=quantile(sims,.975)
        prob=sum(x>0 for x in sims)/B*100
        lines.append(f"| {name} | {h*5}m | {period} | {len(rows)} | {sum(x!=0 for x in vals)} / {n_days} | {total:+.2f}u | [{lo:+.2f}, {hi:+.2f}]u | {prob:.1f}% |")
    lines += ["","## Interpretation","",
      "- A confidence interval spanning zero means this resampling exercise does not establish positive average performance for that split.",
      "- The bootstrap is not a substitute for a genuinely untouched forward period; candidate selection was performed on TRAIN and 120 distinct strategy/expiry variants (360 variant/split rows) were screened.",
      "- The BID feed, platform quote differences, payout variation, latency, and execution costs are not modeled.",
      "- No live strategy is approved and no trades are executed.",""]
    write_report(args.out, lines)
    print(f"Wrote {args.out}; frozen_candidates={len(frozen)}; bootstrap={B}")
if __name__=="__main__": main()
