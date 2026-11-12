#!/usr/bin/env python3
"""Deterministic matched-control comparison with calendar-day block bootstrap."""
from __future__ import annotations
import argparse, json, hashlib, random
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from universal_profile_engine import PAYOUT, SPLITS, parse_dt, read_matrix, build_candidate_events

BOOTSTRAPS=10000
BLOCK_DAYS=5
MATCH_WINDOW_DAYS=14

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def split_dates(c,cfg,segments):
    d1=parse_dt(cfg["split_boundaries_utc"]["train_end"])
    d2=parse_dt(cfg["split_boundaries_utc"]["validation_end"])
    if c.get("split_scheme","fixed")=="fixed": return d1,d2
    if c["split_scheme"]=="observed_utc_date_quantiles_60_80":
        days=sorted({x["timestamp"].date() for rows in segments.values() for x in rows})
        from datetime import datetime,timezone
        return (datetime.combine(days[int(.60*len(days))],datetime.min.time(),tzinfo=timezone.utc),
                datetime.combine(days[int(.80*len(days))],datetime.min.time(),tzinfo=timezone.utc))
    raise ValueError("Unsupported split scheme: "+c["split_scheme"])

def net(outcome):
    return PAYOUT if outcome=="W" else -1.0 if outcome=="L" else 0.0

def counts(rows):
    w=sum(x["outcome"]=="W" for x in rows); l=sum(x["outcome"]=="L" for x in rows)
    d=sum(x["outcome"]=="D" for x in rows); dec=w+l
    return w,l,d,(100*w/dec if dec else None),w*PAYOUT-l

def match_controls(c,accepted,background):
    h=int(c["expiry_bars"]); pools=defaultdict(list)
    for row in background:
        t=row["time"]; pools[(row["segment"],row["period"],t.weekday(),t.hour)].append(row)
    for rows in pools.values(): rows.sort(key=lambda x:(x["time"],x["index"]))
    used=set(); selected_by_pool=defaultdict(list); selected_by_segment_split=defaultdict(list); pairs=[]; window=timedelta(days=MATCH_WINDOW_DAYS)
    event_indexes=defaultdict(list)
    for event in accepted: event_indexes[(event["segment"],event["period"])].append(event["index"])
    for event in sorted(accepted,key=lambda x:(x["period"],x["time"],x["segment"],x["index"])):
        t=event["time"]; key=(event["segment"],event["period"],t.weekday(),t.hour)
        best=None
        for control in pools.get(key,()):
            delta=abs(control["time"]-t)
            if delta>window or abs(control["index"]-event["index"])<h: continue
            if any(abs(control["index"]-idx)<h for idx in event_indexes[(event["segment"],event["period"])]): continue
            ck=(control["segment"],control["period"],control["index"])
            if ck in used: continue
            if c["nonoverlap"] and any(abs(control["index"]-idx)<h for idx in selected_by_segment_split[(control["segment"],control["period"])]): continue
            rank=(delta,control["time"],control["index"])
            if best is None or rank<best[0]: best=(rank,control)
        if best is not None:
            control=best[1]; used.add((control["segment"],control["period"],control["index"]))
            selected_by_pool[key].append(control["index"]); selected_by_segment_split[(control["segment"],control["period"])].append(control["index"]); pairs.append((event,control))
    return pairs

def calendar_dates(segments,d1,d2,split):
    observed=[]
    for rows in segments.values():
        for row in rows:
            t=row["timestamp"]
            if ((split=="TRAIN" and t<d1) or
                (split=="VALIDATION" and d1<=t<d2) or
                (split=="TEST" and t>=d2)):
                observed.append(t.date())
    if not observed:
        return []
    lo,hi=min(observed),max(observed)
    dates=[]
    day=lo
    while day<=hi:
        dates.append(day)
        day+=timedelta(days=1)
    return dates

def bootstrap_ci(pairs,dates,seed):
    if not pairs or not dates: return None
    daily={d:[0.0,0] for d in dates}
    for a,b in pairs:
        daily[a["time"].date()][0]+=net(a["outcome"])-net(b["outcome"])
        daily[a["time"].date()][1]+=1
    days=sorted(daily); active=sum(daily[d][1]>0 for d in days)
    if len(pairs)<30 or active<10: return {"active":active,"days":len(days),"ci":None}
    values=[daily[d] for d in days]; n=len(values); block=min(BLOCK_DAYS,n)
    rng=random.Random(seed); samples=[]
    for _ in range(BOOTSTRAPS):
        diff=0.0; count=0; collected=0
        while collected<n:
            start=rng.randrange(n); take=min(block,n-collected)
            for j in range(take):
                x,y=values[(start+j)%n]; diff+=x; count+=y
            collected+=take
        if count: samples.append(diff/count)
    samples.sort()
    mean=sum(net(a["outcome"])-net(b["outcome"]) for a,b in pairs)/len(pairs)
    return {"active":active,"days":len(days),"mean":mean,
            "ci":(samples[int(.025*(len(samples)-1))],samples[int(.975*(len(samples)-1))])}

def summarize(pairs):
    aa=[a for a,b in pairs]; bb=[b for a,b in pairs]
    return aa,bb,counts(aa),counts(bb)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--matrix",type=Path,required=True); ap.add_argument("--manifest",type=Path,required=True)
    ap.add_argument("--config",type=Path,required=True); ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args(); m=json.loads(a.manifest.read_text(encoding="utf-8")); cfg=json.loads(a.config.read_text(encoding="utf-8"))
    if sha256(a.matrix)!=m["matrix_sha256"]: raise SystemExit("Feature matrix SHA-256 mismatch")
    if m["source_sha256"]!=cfg["dataset"]["source_sha256"]: raise SystemExit("Dataset identity mismatch")
    segments=read_matrix(a.matrix)
    report=["# Matched controls and calendar-day block bootstrap","",
      "- Baseline: "+cfg.get("baseline_version","unspecified"),
      "- Source SHA-256: "+m["source_sha256"],"- Matrix SHA-256: "+m["matrix_sha256"],
      "- Payout scenario: +0.92/-1/0; not guaranteed platform payout.",
      f"- Matching: same segment, split, UTC weekday and hour; nearest unused control within ±{MATCH_WINDOW_DAYS} days.",
      "- Control timestamps exclude this candidate's raw event triggers; candidate/control trade intervals do not overlap.",
      f"- Uncertainty: circular {BLOCK_DAYS}-calendar-day moving-block bootstrap, {BOOTSTRAPS:,} replicates; full calendar span includes zero-event days.",
      "- Paired diagnostic only; not a randomized experiment or correction for multiple searches.","",
      "| Candidate | Split | Events | Pairs | Coverage | Candidate W/L/D | WR | Net u | Control W/L/D | WR | Net u | Mean paired Δ u/trade | 95% block CI |",
      "|---|---|---:|---:|---:|---|---:|---:|---|---:|---:|---:|---|"]
    for c in cfg["candidates"]:
        d1,d2=split_dates(c,cfg,segments)
        accepted,bg,_,raw=build_candidate_events(c,segments,d1,d2,include_raw=True)
        pairs=match_controls(c,accepted,bg)
        for split in SPLITS:
            eligible=[x for x in accepted if x["period"]==split]
            ps=[(x,y) for x,y in pairs if x["period"]==split]
            ca,co,cs,bs=summarize(ps)
            dates=calendar_dates(segments,d1,d2,split)
            ci=bootstrap_ci(ps,dates,sum(ord(z) for z in c["id"]+split))
            coverage=100*len(ps)/len(eligible) if eligible else 0.0
            wr1=f"{cs[3]:.2f}%" if cs[3] is not None else "n/a"
            wr2=f"{bs[3]:.2f}%" if bs[3] is not None else "n/a"
            delta=(cs[4]-bs[4])/len(ps) if ps else None
            ci_text=f"[{ci['ci'][0]:+.4f}, {ci['ci'][1]:+.4f}]" if ci and ci["ci"] else "insufficient"
            report.append(f"| {c['id']} | {split} | {len(eligible)} | {len(ps)} | {coverage:.1f}% | {cs[0]}/{cs[1]}/{cs[2]} | {wr1} | {cs[4]:+.2f} | {bs[0]}/{bs[1]}/{bs[2]} | {wr2} | {bs[4]:+.2f} | {delta:+.4f} | {ci_text} |" if delta is not None else f"| {c['id']} | {split} | {len(eligible)} | 0 | 0.0% | 0/0/0 | n/a | +0.00 | 0/0/0 | n/a | +0.00 | n/a | insufficient |")
        for combo in c.get("predeclared_combinations",[]):
            cond=combo["conditions"]
            for split in SPLITS:
                ps=[(x,y) for x,y in pairs if x["period"]==split and all(x["state"].get(k)==v for k,v in cond.items())]
                ca,co,cs,bs=summarize(ps)
                dates=calendar_dates(segments,d1,d2,split)
                ci=bootstrap_ci(ps,dates,sum(ord(z) for z in c["id"]+split)+101)
                delta=(cs[4]-bs[4])/len(ps) if ps else None
                report += ["",f"### Predeclared combination — {c['id']} / {combo['name']} / {split}",
                    f"- Conditions: {json.dumps(cond,sort_keys=True)}",
                    f"- Matched pairs: {len(ps)}; candidate W/L/D {cs[0]}/{cs[1]}/{cs[2]}; control W/L/D {bs[0]}/{bs[1]}/{bs[2]}.",
                    f"- Candidate net {cs[4]:+.2f}u; control net {bs[4]:+.2f}u; paired mean Δ {delta:+.4f}u/trade." if delta is not None else "- No matched pairs.",
                    f"- 95% block-bootstrap CI: [{ci['ci'][0]:+.4f}, {ci['ci'][1]:+.4f}]." if ci and ci["ci"] else "- 95% block-bootstrap CI: insufficient matched events."]
    report += ["","## Guardrails","",
      "- Positive paired lift is relative to this matching rule, not proof of positive executable expectancy.",
      "- CI crossing zero is inconclusive; even a positive CI remains exploratory after candidate/regime search.",
      "- Do not tune filters from TEST. TEST has prior exposure and is descriptive only.",
      "- Dukascopy BID bars are not Pocket Option executable quotes.",""]
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text("\\n".join(report),encoding="utf-8")
    print(f"Matched-control bootstrap complete: candidates={len(cfg['candidates'])}; output={a.out}")

if __name__=="__main__": main()
