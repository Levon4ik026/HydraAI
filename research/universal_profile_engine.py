#!/usr/bin/env python3
"""Fail-closed declarative profile engine over Hydra's shared M5 matrix."""
from __future__ import annotations
import argparse, csv, gzip, json, hashlib
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

PAYOUT = 0.92
SPLITS = ("TRAIN", "VALIDATION", "TEST")

def parse_dt(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)

def read_matrix(path):
    groups = defaultdict(list)
    with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            sid = int(r["segment_id"])
            for k in ("bar_index", "open", "high", "low", "close", "rsi14", "ema20", "ema50"):
                r[k] = (int(r[k]) if k == "bar_index" else float(r[k])) if r.get(k) else None
            r["timestamp"] = parse_dt(r.pop("timestamp_utc"))
            groups[sid].append(r)
    for sid, rows in groups.items():
        rows.sort(key=lambda x: x["bar_index"])
        if [x["bar_index"] for x in rows] != list(range(len(rows))):
            raise ValueError(f"Bad bar index sequence in segment {sid}")
    return dict(groups)

def period_for(signal, settle, d1, d2):
    if signal < d1: return "TRAIN" if settle < d1 else None
    if signal < d2: return "VALIDATION" if settle < d2 else None
    return "TEST"

def win_loss(delta, side):
    if abs(delta) < 1e-12: return "D"
    return "W" if ((delta < 0) if side == "PUT" else (delta > 0)) else "L"

def stat(xs):
    w=sum(x["outcome"]=="W" for x in xs); l=sum(x["outcome"]=="L" for x in xs)
    d=sum(x["outcome"]=="D" for x in xs); dec=w+l
    return {"n":len(xs),"w":w,"l":l,"d":d,"wr":100*w/dec if dec else None,"net":w*PAYOUT-l}

def build_candidate_events(c, segments, d1, d2):
    h=int(c["expiry_bars"]); side=c["side"]
    raw=[]; bg=[]; purged=0
    for sid,bars in segments.items():
        for i in range(60,len(bars)-13):
            sig,entry,settle_bar=bars[i],bars[i+1],bars[i+h]
            if entry["timestamp"]-sig["timestamp"] != timedelta(minutes=5): continue
            settlement_mode=c.get("split_settlement","bar_close")
            if settlement_mode=="bar_close":
                settle=settle_bar["timestamp"]+timedelta(minutes=5)
            elif settlement_mode=="bar_open":
                settle=settle_bar["timestamp"]
            else:
                raise ValueError(f"Unsupported split_settlement: {settlement_mode}")
            p=period_for(sig["timestamp"],settle,d1,d2)
            if p is None:
                purged+=1; continue
            delta=settle_bar["close"]-entry["open"]
            base={"time":sig["timestamp"],"period":p,"segment":sid,"index":i,"state":sig}
            required_level=c.get("background_requires_level")
            if not required_level or sig.get(required_level) not in (None, ""):
                bg.append({**base,"outcome":win_loss(delta,side)})
            event=False
            if c["event_type"]=="rsi_bearish_level":
                event=sig["rsi14"] is not None and sig["rsi14"]>=70 and sig["close"]<sig["open"]
            elif c["event_type"]=="previous_week_low_sweep_reclaim_bullish":
                level=sig.get("previous_observed_utc_week_low")
                event=bool(level) and sig["low"]<float(level) and sig["close"]>float(level) and sig["close"]>sig["open"]
            elif c["event_type"]=="previous_day_high_sweep_reclaim_bearish":
                level=sig.get("previous_observed_utc_day_high")
                event=bool(level) and sig["high"]>float(level) and sig["close"]<float(level) and sig["close"]<sig["open"]
            elif c["event_type"]=="previous_day_low_close_breakout":
                level=sig.get("previous_observed_utc_day_low")
                prev_close=bars[i-1]["close"] if i>0 else None
                event=bool(level) and prev_close is not None and prev_close>=float(level) and sig["close"]<float(level)
            elif c["event_type"]=="ema20_bearish_cross":
                prev=bars[i-1] if i>0 else {}
                event=(prev.get("ema20") is not None and prev.get("ema50") is not None
                       and sig.get("ema20") is not None and sig.get("ema50") is not None
                       and prev["ema20"]>=prev["ema50"] and sig["ema20"]<sig["ema50"]
                       and sig["close"]<sig["ema20"])
            elif c["event_type"]=="donchian50_bullish_breakout":
                prior=bars[max(0,i-50):i]
                event=(len(prior)==50 and sig["close"]>max(x["high"] for x in prior)
                       and sig["close"]>sig["open"])
            elif c["event_type"]=="bullish_abnormal_impulse":
                prior_tr=[]
                for j in range(max(1,i-20),i):
                    prev_close=bars[j-1]["close"]
                    x=bars[j]
                    prior_tr.append(max(x["high"]-x["low"],abs(x["high"]-prev_close),abs(x["low"]-prev_close)))
                rng=sig["high"]-sig["low"]
                body=abs(sig["close"]-sig["open"])/rng if rng else 0.0
                close_loc=(sig["close"]-sig["low"])/rng if rng else 0.0
                mean_tr=sum(prior_tr)/len(prior_tr) if len(prior_tr)==20 else None
                event=(mean_tr is not None and rng>=2.0*mean_tr and body>=0.60
                       and sig["close"]>sig["open"] and close_loc>=0.75)
            elif c["event_type"]=="up_shock_second_bar_reversal":
                prior_tr=[]
                for j in range(max(1,i-21),i-1):
                    prev_close=bars[j-1]["close"]
                    x=bars[j]
                    prior_tr.append(max(x["high"]-x["low"],abs(x["high"]-prev_close),abs(x["low"]-prev_close)))
                shock=bars[i-1]
                shock_prev_close=bars[i-2]["close"] if i>=2 else None
                shock_tr=(max(shock["high"]-shock["low"],abs(shock["high"]-shock_prev_close),
                              abs(shock["low"]-shock_prev_close)) if shock_prev_close is not None else None)
                med_tr=sorted(prior_tr)[len(prior_tr)//2] if len(prior_tr)==20 else None
                if med_tr is not None and len(prior_tr)==20 and len(prior_tr)%2==0:
                    med_tr=(sorted(prior_tr)[9]+sorted(prior_tr)[10])/2.0
                event=(med_tr is not None and shock_tr is not None and med_tr>0
                       and shock_tr>=2.0*med_tr and shock["close"]>shock["open"]
                       and sig["close"]<sig["open"] and sig["close"]<shock["close"])
            else:
                raise ValueError("Unsupported event type: "+c["event_type"])
            if event: raw.append({**base,"outcome":win_loss(delta,side)})
    accepted=[]
    for sid in sorted(segments):
        for p in SPLITS:
            xs=sorted((x for x in raw if x["segment"]==sid and x["period"]==p),key=lambda x:x["index"])
            next_ok=-1
            for x in xs:
                if not c["nonoverlap"] or x["index"]>=next_ok:
                    accepted.append(x); next_ok=x["index"]+h
    event_keys={(x["segment"],x["index"]) for x in raw}
    bg=[x for x in bg if (x["segment"],x["index"]) not in event_keys]
    return accepted,bg,purged

def profile_candidate(c, accepted, bg, purged, d1, d2):
    lines=["## "+c["id"]+" — "+c["name"],"",
      f"- Frozen event: {c['event_type']}; side={c['side']}; expiry={c['expiry_bars']*5}m; non-overlap={c['nonoverlap']}.",
      f"- Candidate-specific chronological splits: TRAIN < {d1.date()}; VALIDATION {d1.date()} through {d2.date()-timedelta(days=1)}; TEST >= {d2.date()}.",
      f"- Split scheme: {c.get('split_scheme', 'fixed')}; eligible M5 bars excluded at split boundaries: {purged}.",
      "- Features are measured at the completed signal-bar close; entry is the next M5 open.",
      "- Background is all eligible M5 bars excluding raw candidate trigger timestamps; descriptive and overlapping, not matched non-overlap controls.","",
      "| Split | Actual n | W/L/D | WR | Net u | Expected n (W/L/D) | Gate |",
      "|---|---:|---|---:|---:|---|---|"]
    passed=True
    for p in SPLITS:
        s=stat([x for x in accepted if x["period"]==p]); e=c["expected"][p]
        ok=all(s[k]==e[k] for k in ("n","w","l","d")); passed &= ok
        wr=f"{s['wr']:.2f}%" if s["wr"] is not None else "n/a"
        lines.append(f"| {p} | {s['n']} | {s['w']}/{s['l']}/{s['d']} | {wr} | {s['net']:+.2f} | {e['n']} ({e['w']}/{e['l']}/{e['d']}) | {'PASS' if ok else 'FAIL — STOP'} |")
    if not passed:
        return lines+["","PROFILE BLOCKED: exact frozen cohort reproduction failed. Do not interpret subgroup results.",""]
    lines += ["","### Predeclared one-dimensional profile map","","| Split | Feature | Bin | Candidate n | W/L/D | WR | Background n | Background WR | Lift pp | Net u |","|---|---|---|---:|---|---:|---:|---:|---:|---:|"]
    for feature in c["profile_dimensions"]:
        bins=sorted({x["state"].get(feature,"") for x in accepted if x["state"].get(feature,"")})
        for p in SPLITS:
            for bname in bins:
                cs=[x for x in accepted if x["period"]==p and x["state"].get(feature)==bname]
                if len(cs)<4: continue
                bs=[x for x in bg if x["period"]==p and x["state"].get(feature)==bname]
                a,z=stat(cs),stat(bs)
                lift=a["wr"]-z["wr"] if a["wr"] is not None and z["wr"] is not None else None
                lines.append(f"| {p} | {feature} | {bname} | {a['n']} | {a['w']}/{a['l']}/{a['d']} | {a['wr']:.2f}% | {z['n']} | {z['wr']:.2f}% | {lift:+.2f} | {a['net']:+.2f} |" if lift is not None else f"| {p} | {feature} | {bname} | {a['n']} | {a['w']}/{a['l']}/{a['d']} | n/a | {z['n']} | n/a | n/a | {a['net']:+.2f} |")
    for combo in c.get("predeclared_combinations",[]):
        lines += ["","### Predeclared combination: "+combo["name"],"",
                  "| Split | n | W/L/D | WR | Background n | Background WR | Lift pp | Net u |",
                  "|---|---:|---|---:|---:|---:|---:|---:|"]
        for p in SPLITS:
            cond=combo["conditions"]
            cs=[x for x in accepted if x["period"]==p and all(x["state"].get(k)==v for k,v in cond.items())]
            bs=[x for x in bg if x["period"]==p and all(x["state"].get(k)==v for k,v in cond.items())]
            a,z=stat(cs),stat(bs); lift=a["wr"]-z["wr"] if a["wr"] is not None and z["wr"] is not None else None
            lines.append(f"| {p} | {a['n']} | {a['w']}/{a['l']}/{a['d']} | {a['wr']:.2f}% | {z['n']} | {z['wr']:.2f}% | {lift:+.2f} | {a['net']:+.2f} |" if lift is not None else f"| {p} | {a['n']} | {a['w']}/{a['l']}/{a['d']} | n/a | {z['n']} | n/a | n/a | {a['net']:+.2f} |")
    lines += ["","- Descriptive profiling only; no threshold optimization or confirmation.",
              "- TEST has prior exposure and is not pristine. Independent prospective validation is still required.",""]
    return lines

def file_sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--matrix",type=Path,required=True)
    ap.add_argument("--manifest",type=Path,required=True)
    ap.add_argument("--config",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    m=json.loads(a.manifest.read_text(encoding="utf-8")); cfg=json.loads(a.config.read_text(encoding="utf-8"))
    if m["feature_version"]!="hydra_m5_causal_features_v1": raise SystemExit("Unsupported feature matrix version")
    actual_matrix_hash=file_sha256(a.matrix)
    if actual_matrix_hash != m["matrix_sha256"]:
        raise SystemExit(f"Feature matrix SHA-256 mismatch: {actual_matrix_hash} != {m['matrix_sha256']}")
    checks={"m1_valid_rows":"expected_m1_rows","m5_complete_rows":"expected_m5_rows","source_sha256":"source_sha256"}
    for actual,expected in checks.items():
        if m[actual]!=cfg["dataset"][expected]:
            raise SystemExit(f"Dataset identity mismatch {actual}: {m[actual]} != {cfg['dataset'][expected]}")
    fixed_d1=parse_dt(cfg["split_boundaries_utc"]["train_end"]); fixed_d2=parse_dt(cfg["split_boundaries_utc"]["validation_end"])
    segments=read_matrix(a.matrix)
    observed_days=sorted({row["timestamp"].date() for rows in segments.values() for row in rows})
    if len(observed_days)<30:
        raise SystemExit("Insufficient observed UTC dates for chronological split derivation")
    matrix_rows=sum(len(x) for x in segments.values())
    if matrix_rows != m["matrix_rows"]:
        raise SystemExit(f"Feature matrix row-count mismatch: {matrix_rows} != {m['matrix_rows']}")
    if len(segments) != m["gap_separated_segments"]:
        raise SystemExit(f"Segment-count mismatch: {len(segments)} != {m['gap_separated_segments']}")
    report=["# Hydra universal market-situation profile engine — research-only","",
      f"- Source SHA-256: {m['source_sha256']}; M1={m['m1_valid_rows']:,}; M5={m['m5_complete_rows']:,}; segments={m['gap_separated_segments']:,}.",
      f"- Matrix SHA-256: {m['matrix_sha256']}; rows={m['matrix_rows']:,}.",
      "- 92% payout is a scenario only (+0.92/-1/0); break-even decisive WR 52.0833%.",
      "- Dukascopy BID is not Pocket Option executable pricing.",""]
    for c in cfg["candidates"]:
        scheme=c.get("split_scheme","fixed")
        if scheme=="fixed":
            d1,d2=fixed_d1,fixed_d2
        elif scheme=="observed_utc_date_quantiles_60_80":
            d1=datetime.combine(observed_days[int(0.60*len(observed_days))],datetime.min.time(),tzinfo=timezone.utc)
            d2=datetime.combine(observed_days[int(0.80*len(observed_days))],datetime.min.time(),tzinfo=timezone.utc)
        else:
            raise SystemExit(f"Unknown split scheme for {c['id']}: {scheme}")
        accepted,bg,purged=build_candidate_events(c,segments,d1,d2)
        report += profile_candidate(c,accepted,bg,purged,d1,d2)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text("\n".join(report)+"\n",encoding="utf-8")
    print(f"Universal profile engine complete: {len(cfg['candidates'])} candidate definitions; {a.out}")

if __name__=="__main__":
    main()
