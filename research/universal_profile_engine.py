#!/usr/bin/env python3
"""Fail-closed declarative profile engine over Hydra's shared M5 matrix."""
from __future__ import annotations
import argparse, csv, gzip, json
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
            for k in ("bar_index", "open", "high", "low", "close", "rsi14"):
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
            settle=settle_bar["timestamp"]+timedelta(minutes=5)
            p=period_for(sig["timestamp"],settle,d1,d2)
            if p is None:
                purged+=1; continue
            delta=settle_bar["close"]-entry["open"]
            base={"time":sig["timestamp"],"period":p,"segment":sid,"index":i,"state":sig}
            bg.append({**base,"outcome":win_loss(delta,side)})
            event=False
            if c["event_type"]=="rsi_bearish_level":
                event=sig["rsi14"] is not None and sig["rsi14"]>=70 and sig["close"]<sig["open"]
            elif c["event_type"]=="previous_week_low_sweep_reclaim_bullish":
                level=sig.get("previous_observed_utc_week_low")
                event=bool(level) and sig["low"]<float(level) and sig["close"]>float(level) and sig["close"]>sig["open"]
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

def profile_candidate(c, accepted, bg, purged):
    lines=["## "+c["id"]+" — "+c["name"],"",
      f"- Frozen event: {c['event_type']}; side={c['side']}; expiry={c['expiry_bars']*5}m; non-overlap={c['nonoverlap']}.",
      f"- Boundary-crossing outcomes purged: {purged}.",
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

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--matrix",type=Path,required=True)
    ap.add_argument("--manifest",type=Path,required=True)
    ap.add_argument("--config",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    m=json.loads(a.manifest.read_text(encoding="utf-8")); cfg=json.loads(a.config.read_text(encoding="utf-8"))
    if m["feature_version"]!="hydra_m5_causal_features_v1": raise SystemExit("Unsupported feature matrix version")
    checks={"m1_valid_rows":"expected_m1_rows","m5_complete_rows":"expected_m5_rows","source_sha256":"source_sha256"}
    for actual,expected in checks.items():
        if m[actual]!=cfg["dataset"][expected]:
            raise SystemExit(f"Dataset identity mismatch {actual}: {m[actual]} != {cfg['dataset'][expected]}")
    d1=parse_dt(cfg["split_boundaries_utc"]["train_end"]); d2=parse_dt(cfg["split_boundaries_utc"]["validation_end"])
    segments=read_matrix(a.matrix)
    report=["# Hydra universal market-situation profile engine — research-only","",
      f"- Source SHA-256: {m['source_sha256']}; M1={m['m1_valid_rows']:,}; M5={m['m5_complete_rows']:,}; segments={m['gap_separated_segments']:,}.",
      f"- Matrix SHA-256: {m['matrix_sha256']}; rows={m['matrix_rows']:,}.",
      "- 92% payout is a scenario only (+0.92/-1/0); break-even decisive WR 52.0833%.",
      "- Dukascopy BID is not Pocket Option executable pricing.",""]
    for c in cfg["candidates"]:
        accepted,bg,purged=build_candidate_events(c,segments,d1,d2)
        report += profile_candidate(c,accepted,bg,purged)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text("\n".join(report)+"\n",encoding="utf-8")
    print(f"Universal profile engine complete: {len(cfg['candidates'])} candidate definitions; {a.out}")

if __name__=="__main__":
    main()
