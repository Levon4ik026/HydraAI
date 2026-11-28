#!/usr/bin/env python3
"""Frozen forward-only NY downside-shock CALL audit. No optimization."""
import argparse,csv,math,statistics,random
from collections import defaultdict
from datetime import datetime,date,time,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
NY=ZoneInfo("America/New_York"); UTC=timezone.utc
MIN_SOURCE_TS=datetime(2024,1,1,tzinfo=UTC)
CUTOFF=datetime(2026,11,13,21,59,tzinfo=UTC)
LOOKBACK=20; EXPIRY=30; PAYOUT=.92; REPS=5000; SEED=20261115

def parse_ts(v):
    v=v.strip()
    try:
        x=datetime.fromisoformat(v.replace("Z","+00:00"))
        if x.tzinfo is None: x=x.replace(tzinfo=UTC)
        return x.astimezone(UTC).replace(second=0,microsecond=0)
    except ValueError:
        n=float(v); n=n/1000 if n>1e12 else n
        return datetime.fromtimestamp(n,UTC).replace(second=0,microsecond=0)

def load(path):
    out={}; bad=0
    with path.open(encoding="utf-8-sig",newline="") as f:
        r=csv.DictReader(f); cols={x.lower().strip():x for x in (r.fieldnames or [])}
        tc=next((cols[x] for x in ("timestamp","datetime","date","time") if x in cols),None)
        if not tc or any(x not in cols for x in ("open","high","low","close")): raise ValueError("Expected timestamp/open/high/low/close columns")
        for row in r:
            try:
                ts=parse_ts(row[tc])
                if ts < MIN_SOURCE_TS: raise ValueError("timestamp predates requested Dukascopy range")
                o,h,l,c=[float(row[cols[k]]) for k in ("open","high","low","close")]
                if min(o,h,l,c)<=0 or not all(math.isfinite(x) for x in (o,h,l,c)) or h<max(o,c) or l>min(o,c): raise ValueError()
                out[ts]=(o,h,l,c)
            except Exception: bad+=1
    return dict(sorted(out.items())),bad

def starts(first,last):
    d=first.astimezone(NY).date()-timedelta(days=2); end=last.astimezone(NY).date()+timedelta(days=1)
    while d<=end:
        if d.weekday() in (6,0,1,2,3): yield datetime.combine(d,time(18),NY).astimezone(UTC)
        d+=timedelta(days=1)

def session(data,start):
    ts=[start+timedelta(minutes=i) for i in range(1380)]
    present=[t for t in ts if t in data]; gap=run=0
    for t in ts:
        run=0 if t in data else run+1; gap=max(gap,run)
    if len(present)/1380<.99 or gap>5 or ts[0] not in data or ts[-1] not in data: return None
    op=data[ts[0]][0]; cl=data[ts[-1]][3]
    return {"start":start,"ret":math.log(cl/op),"coverage":len(present)/1380} if op>0 and cl>0 else None

def outcome(data,start,side):
    ts=[start+timedelta(minutes=i) for i in range(EXPIRY)]
    if any(t not in data for t in ts): return None
    delta=data[ts[-1]][3]-data[ts[0]][0]
    if abs(delta)<1e-12: return "DRAW"
    return "WIN" if ((delta>0)==(side=="CALL")) else "LOSS"

def points(x): return PAYOUT if x=="WIN" else -1 if x=="LOSS" else 0

def stats(rows):
    w=sum(r["outcome"]=="WIN" for r in rows); l=sum(r["outcome"]=="LOSS" for r in rows); d=len(rows)-w-l
    dec=w+l; net=w*PAYOUT-l; eq=peak=dd=0; streak=mx=0
    for r in rows:
        eq+=points(r["outcome"]); peak=max(peak,eq); dd=max(dd,peak-eq)
        streak=streak+1 if r["outcome"]=="LOSS" else 0; mx=max(mx,streak)
    return {"n":len(rows),"w":w,"l":l,"d":d,"wr":100*w/dec if dec else None,"net":net,
            "roi":100*net/len(rows) if rows else None,"pf":w*PAYOUT/l if l else (float("inf") if w else 0),"dd":dd,"streak":mx}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--out",type=Path,default=Path("research-artifacts/ny-downside-shock-call-forward/report.md"))
    ap.add_argument("--ledger",type=Path,default=Path("research-artifacts/ny-downside-shock-call-forward/trades.csv")); a=ap.parse_args()
    data,bad=load(a.data)
    if not data: raise SystemExit("No valid data")
    ss=[x for x in (session(data,t) for t in starts(next(iter(data)),next(reversed(data)))) if x]
    rows=[]; puts=[]; raw=0
    for i in range(LOOKBACK+1,len(ss)):
        # Exclude the just-completed shock session from its 20-session baseline.
        prev=ss[i-LOOKBACK-1:i-1]; cur=ss[i-1]; entry=ss[i]["start"]
        threshold=statistics.mean(abs(x["ret"]) for x in prev)
        if cur["ret"]<=-threshold:
            raw+=1
            if entry<=CUTOFF: continue
            call=outcome(data,entry,"CALL"); put=outcome(data,entry,"PUT")
            if call is None or put is None: continue
            rows.append({"prior_session_utc":cur["start"].isoformat(),"entry_utc":entry.isoformat(),
                         "prior20_mean_abs_log_return":f"{threshold:.12g}","shock_log_return":f"{cur['ret']:.12g}",
                         "session_coverage":f"{cur['coverage']:.6f}","outcome":call})
            puts.append({"entry_utc":entry.isoformat(),"outcome":put})
    rows.sort(key=lambda x:x["entry_utc"]); puts.sort(key=lambda x:x["entry_utc"])
    days=[]; d=CUTOFF.date()+timedelta(days=1); last=next(reversed(data)).date()
    while d<=last: days.append(d.isoformat()); d+=timedelta(days=1)
    daily=defaultdict(float)
    for r in rows: daily[r["entry_utc"][:10]]+=points(r["outcome"])
    vals=[daily[x] for x in days]; samples=[]; positive=0; rng=random.Random(SEED)
    if vals:
        for _ in range(REPS):
            v=sum(vals[rng.randrange(len(vals))] for _ in vals); samples.append(v); positive+=v>0
        samples.sort(); lo=samples[int(.025*REPS)]; hi=samples[int(.975*REPS)]; pp=100*positive/REPS
    else: lo=hi=pp=None
    s=stats(rows); p=stats(puts); active=len({r["entry_utc"][:10] for r in rows})
    a.ledger.parent.mkdir(parents=True,exist_ok=True)
    with a.ledger.open("w",newline="",encoding="utf-8") as f:
        fields=["prior_session_utc","entry_utc","prior20_mean_abs_log_return","shock_log_return","session_coverage","outcome"]
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    pct=lambda x:"n/a" if x is None else f"{x:.2f}%"
    pf=lambda x:"inf" if x==float("inf") else f"{x:.3f}"
    ci="n/a" if lo is None else f"[{lo:+.2f}, {hi:+.2f}]u"
    roi="n/a" if s["roi"] is None else f'{s["roi"]:+.2f}%'
    prob="n/a" if pp is None else f"{pp:.1f}%"
    lines=["# NY downside-shock CALL — locked forward audit","",
      f"Source: Dukascopy EURUSD M1 BID; valid unique rows={len(data):,}; invalid or pre-2024 rows excluded={bad:,}.",
      f"Coverage: {next(iter(data)).isoformat()} — {next(reversed(data)).isoformat()}.",
      f"Valid NY sessions={len(ss):,}; raw shock matches={raw:,}.",
      f"Frozen cutoff={CUTOFF.isoformat()} exclusive; only later entries scored.",
      "Frozen rule: 18:00–16:59 America/New_York completed session; >=99% minute coverage; no gap >5m; after 20 preceding valid sessions, current log return <= -1.0x their mean absolute return; CALL at next 18:00 NY open only.",
      "Expiry fixed 30m: entry M1 open, settlement close of entry+29m. All 30 bars required. No PUT signals.",
      f"Payout +{PAYOUT:.2f}/-1/0; break-even decisive WR=52.0833%. Matched PUT comparator is secondary only.",
      "Dukascopy BID is not Pocket Option executable pricing; spread, platform quotes, payout variation and latency are not modeled.","",
      "## Primary CALL results","",
      "| Trades | W/L/D | Decisive WR | Net | ROI/trade | PF | Max DD | Max loss streak | Active days | Daily bootstrap 95% CI | P(net>0) |",
      "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
      f'| {s["n"]} | {s["w"]}/{s["l"]}/{s["d"]} | {pct(s["wr"])} | {s["net"]:+.2f}u | {roi} | {pf(s["pf"])} | {s["dd"]:.2f}u | {s["streak"]} | {active} | {ci} | {prob} |',
      "","## Matched PUT comparator","",
      f'Trades={p["n"]}; W/L/D={p["w"]}/{p["l"]}/{p["d"]}; WR={pct(p["wr"])}; net={p["net"]:+.2f}u; PF={pf(p["pf"])}.',
      "","## Decision","",
      f'- {"At least" if s["n"]>=100 else "Fewer than"} 100 forward CALL trades; minimum statistical review threshold=100.',
      "- Under 100 trades is insufficient; no parameter, direction, expiry, session or filter may be changed during monitoring.",
      "- Monitoring only. No production approval, real trades, OTC or automatic execution."]
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(f"NY CALL forward audit: M1={len(data)} sessions={len(ss)} raw={raw} scored={s['n']} cutoff={CUTOFF.isoformat()}")
if __name__=="__main__": main()
