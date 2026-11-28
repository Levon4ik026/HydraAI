#!/usr/bin/env python3
"""Predeclared causal sequence-state audit for frozen CALL/PUT signals."""
import argparse
from pathlib import Path
try:
 from .win_loss_feature_audit import SPLIT_DATE,load_m1,make_m5,parse_time,build_ledger
except ImportError:
 from win_loss_feature_audit import SPLIT_DATE,load_m1,make_m5,parse_time,build_ledger
def sg(x): return 1 if x>0 else -1 if x<0 else 0
def sequence_states(bars):
 out=[]
 for i,b in enumerate(bars):
  r={k:None for k in ("flip_state_6","trade_alignment_3","trade_alignment_6","last_bar_reversal","impulse_followthrough","range_rejection")}
  if i>=6:
   d=[bars[j].close-bars[j-1].close for j in range(i-5,i+1)]; z=[sg(x) for x in d]
   f=sum(a!=0 and c!=0 and a!=c for a,c in zip(z,z[1:]))
   r["flip_state_6"]="CALM_0_1" if f<=1 else "MIXED_2_3" if f<=3 else "CHAOTIC_4_5"
   prior=bars[i-1].close-bars[i-6].close
   r["last_bar_reversal"]=bool(sg(prior) and sg(d[-1]) and sg(prior)!=sg(d[-1]))
   p=sum(d[:3]); q=sum(d[3:])
   r["impulse_followthrough"]="CONTINUE" if sg(p) and sg(q)==sg(p) else "REVERSE" if sg(p) and sg(q)==-sg(p) else "NO_CLEAR_MOVE"
   r["trade_alignment_6"]=sum(z)
  if i>=3: r["trade_alignment_3"]=sum(sg(bars[j].close-bars[j-1].close) for j in range(i-2,i+1))
  span=b.high-b.low
  if span>0:
   loc=(b.close-b.low)/span
   r["range_rejection"]="LOWER_REJECTION" if loc>=.75 else "UPPER_REJECTION" if loc<=.25 else "MID_RANGE"
  out.append(r)
 return out
def orient(v,d):
 if v is None:return None
 if isinstance(v,(int,float)):return -v if d=="PUT" else v
 if v=="LOWER_REJECTION":return "AGAINST_TRADE" if d=="PUT" else "WITH_TRADE"
 if v=="UPPER_REJECTION":return "WITH_TRADE" if d=="PUT" else "AGAINST_TRADE"
 return v
def build_report(ledger,fmap,split):
 lines=["# Sequence-state audit: predeclared OHLC patterns","",f"Events={len(ledger)}; chronological split={split}; payout=92%; next M5 candle settlement.","All states use only the closed signal candle and earlier candles. Fixed bins; no threshold selection.","Exploratory only: small cells, serial dependence, and previously inspected holdout prevent confirmatory claims.",""]
 keys=("flip_state_6","trade_alignment_3","trade_alignment_6","last_bar_reversal","impulse_followthrough","range_rejection")
 for direction in ("CALL","PUT"):
  for period in ("TRAIN","HOLDOUT"):
   chosen=[x for x in ledger if x["direction"]==direction and x["period"]==period]
   lines += [f"## {direction} / {period} (n={len(chosen)})",""]
   for key in keys:
    groups={}
    for x in chosen:
     v=orient(fmap[x["signal_time"]][key],direction)
     if v is not None:groups.setdefault(str(v),[]).append(x["outcome"])
    lines += [f"### {key}","| State | W | L | D | Decisive WR | Net units |","|---|---:|---:|---:|---:|---:|"]
    for state,ys in sorted(groups.items()):
     w,l,d=ys.count("WIN"),ys.count("LOSS"),ys.count("DRAW")
     lines.append(f"| {state} | {w} | {l} | {d} | {w/(w+l):.1%} | {(.92*w-l):+.2f} |" if w+l else f"| {state} | {w} | {l} | {d} | — | {(.92*w-l):+.2f} |")
    lines.append("")
 lines += ["## Reading guide","","- Compare the same state in TRAIN and HOLDOUT; do not infer an edge from one small cell.","- No filters are selected. Any promising state requires frozen prospective validation.","- Trade alignment is positive when recent price movement agrees with the trade direction.","- Descriptive counts only; no independent statistical significance is claimed."]
 return "\n".join(lines)+"\n"
def main():
 p=argparse.ArgumentParser();p.add_argument("--data",type=Path,default=Path("eurusd_history_extended.csv"));p.add_argument("--split-date",default=SPLIT_DATE);p.add_argument("--adx-min",type=float,default=15);p.add_argument("--out",type=Path,default=Path("research/SEQUENCE_STATE_AUDIT.md"));a=p.parse_args()
 m=load_m1(a.data);segs=make_m5(m);ledger=build_ledger(segs,parse_time(a.split_date),a.adx_min);fm={}
 for seg in segs:
  for bar,row in zip(seg,sequence_states(seg)):fm[bar.timestamp.isoformat()]=row
 report=build_report(ledger,fm,a.split_date);a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(report,encoding="utf-8");print(report)
if __name__=="__main__":main()
