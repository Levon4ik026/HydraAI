#!/usr/bin/env python3
"""Timestamp-level parity audit: legacy candidate builders vs universal engine."""
from __future__ import annotations
import argparse, json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from reproduce_m5_bb_williams_adx import Bar
from universal_profile_engine import read_matrix, build_candidate_events, parse_dt, win_loss
from expanded_strategy_screen import make_events as legacy_expanded_events
from eighth_wave_market_situation_screen import events_for_segment as legacy_eighth_events
from ninth_wave_market_situation_screen import discover as legacy_ninth_events
from eleventh_wave_impulse_screen import build_events as legacy_eleventh_events

LEGACY = {
    "HYD-CAND-001": (legacy_expanded_events, "RSI14_70_REV_PUT"),
    "HYD-CAND-011": (legacy_eighth_events, "UP_SHOCK_SECOND_BAR_REVERSAL_PUT"),
    "HYD-CAND-012": (legacy_ninth_events, "EMA20_50_BEAR_CROSS_PUT"),
    "HYD-CAND-013": (legacy_eleventh_events, "BULL_IMPULSE_CONT_R2.0_C0.75"),
}

def boundaries(cfg, segments):
    d1_fixed=parse_dt(cfg["split_boundaries_utc"]["train_end"])
    d2_fixed=parse_dt(cfg["split_boundaries_utc"]["validation_end"])
    days=sorted({r["timestamp"].date() for rows in segments.values() for r in rows})
    return days, d1_fixed, d2_fixed

def derive_split_dates(c, days, d1_fixed, d2_fixed):
    scheme=c.get("split_scheme","fixed")
    if scheme=="fixed":
        return d1_fixed,d2_fixed
    if scheme=="observed_utc_date_quantiles_60_80":
        return (datetime.combine(days[int(.60*len(days))],datetime.min.time(),tzinfo=timezone.utc),
                datetime.combine(days[int(.80*len(days))],datetime.min.time(),tzinfo=timezone.utc))
    raise ValueError(f"Unsupported split scheme: {scheme}")

def format_candidate_row(
    cid, legacy_builder_raw_count, legacy_eligible_raw_count,
    engine_eligible_raw_count, engine_accepted_count, legacy_accepted_count,
    raw_parity, accepted_parity, outcomes_ok,
):
    ok = raw_parity and accepted_parity and outcomes_ok
    return (
        f"| {cid} | {legacy_builder_raw_count} | {legacy_eligible_raw_count} | "
        f"{engine_eligible_raw_count} | {engine_accepted_count} | {legacy_accepted_count} | "
        f"{'PASS' if raw_parity else 'FAIL'} | {'PASS' if accepted_parity else 'FAIL'} | "
        f"{'PASS' if outcomes_ok else 'FAIL'} | {'PASS' if ok else 'FAIL'} |"
    )


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--matrix",type=Path,required=True)
    ap.add_argument("--manifest",type=Path,required=True)
    ap.add_argument("--config",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    manifest=json.loads(a.manifest.read_text(encoding="utf-8"))
    if manifest.get("feature_version")!="hydra_m5_causal_features_v1":
        raise SystemExit("Unsupported feature matrix version")
    segments_rows=read_matrix(a.matrix)
    bars_by_segment={
        sid:[Bar(r["timestamp"],float(r["open"]),float(r["high"]),float(r["low"]),float(r["close"])) for r in rows]
        for sid,rows in segments_rows.items()
    }
    cfg=json.loads(a.config.read_text(encoding="utf-8"))
    days,d1_fixed,d2_fixed=boundaries(cfg,segments_rows)
    report=[
        "# Legacy vs universal engine — timestamp parity audit","",
        f"- Dataset SHA-256: {manifest['source_sha256']}",
        f"- Feature matrix SHA-256: {manifest['matrix_sha256']}",
        "- The legacy event builders and universal engine receive the same reconstructed, gap-separated M5 OHLC segments.",
        "- This audit compares raw trigger timestamps, accepted non-overlap timestamps, and outcomes; it does not validate profitability.","",
        "| Candidate | Legacy builder raw (pre-guard) | Legacy eligible raw | Engine eligible raw | Engine accepted | Legacy accepted | Eligible raw timestamp parity | Accepted timestamp parity | Outcome parity | Result |",
        "|---|---:|---:|---:|---:|---:|---|---|---|---|"
    ]
    failures=0
    for c in cfg["candidates"]:
        cid=c["id"]
        if cid not in LEGACY:
            continue
        builder,event_name=LEGACY[cid]
        d1,d2=derive_split_dates(c,days,d1_fixed,d2_fixed)
        engine_accepted,_,_,engine_eligible_raw=build_candidate_events(c,segments_rows,d1,d2,include_raw=True)
        legacy_raw=[]
        for sid,bars in bars_by_segment.items():
            found=builder(bars).get(event_name,[])
            for i,original_side in found:
                legacy_raw.append((sid,i,original_side))
        h=int(c["expiry_bars"])
        min_index=int(c.get("min_signal_index",60))
        tail_guard=int(c.get("tail_guard",13))
        legacy_eligible=[]
        for sid,i,original_side in legacy_raw:
            bars=bars_by_segment[sid]
            if i<min_index or i>=len(bars)-tail_guard or i+h>=len(bars):
                continue
            if bars[i+1].timestamp-bars[i].timestamp != timedelta(minutes=5):
                continue
            settle=bars[i+h].timestamp
            if c.get("split_settlement","bar_close")=="bar_close":
                settle += timedelta(minutes=5)
            if settle < d1:
                period="TRAIN" if bars[i].timestamp<d1 else None
            elif bars[i].timestamp<d1:
                period=None
            elif bars[i].timestamp<d2:
                period="VALIDATION" if settle<d2 else None
            else:
                period="TEST"
            if period is None:
                continue
            legacy_eligible.append((sid,i,period))
        # Apply the exact historical one-position-per-segment/split schedule.
        legacy_accepted=[]
        for sid in sorted(bars_by_segment):
            for period in ("TRAIN","VALIDATION","TEST"):
                next_allowed=-1
                for ss,i,pp in sorted(x for x in legacy_eligible if x[0]==sid and x[2]==period):
                    if not c["nonoverlap"] or i>=next_allowed:
                        legacy_accepted.append((ss,i,pp))
                        next_allowed=i+h
        engine_keys={(x["segment"],x["index"],x["period"]) for x in engine_accepted}
        legacy_keys=set(legacy_accepted)
        legacy_raw_keys={(sid,i,p) for sid,i,p in legacy_eligible}
        engine_eligible_raw_keys={(x["segment"],x["index"],x["period"]) for x in engine_eligible_raw}
        raw_parity=(legacy_raw_keys==engine_eligible_raw_keys)
        accepted_parity=(engine_keys==legacy_keys)
        engine_out={(x["segment"],x["index"],x["period"]):x["outcome"] for x in engine_accepted}
        outcomes_ok=True
        for sid,i,p in legacy_accepted:
            bars=bars_by_segment[sid]
            delta=bars[i+h].close-bars[i+1].open
            expected=win_loss(delta,c["side"])
            if engine_out.get((sid,i,p))!=expected:
                outcomes_ok=False
        ok=raw_parity and accepted_parity and outcomes_ok
        failures += 0 if ok else 1
        report.append(format_candidate_row(
            cid=cid,
            legacy_builder_raw_count=len(legacy_raw),
            legacy_eligible_raw_count=len(legacy_raw_keys),
            engine_eligible_raw_count=len(engine_eligible_raw),
            engine_accepted_count=len(engine_accepted),
            legacy_accepted_count=len(legacy_accepted),
            raw_parity=raw_parity,
            accepted_parity=accepted_parity,
            outcomes_ok=outcomes_ok,
        ))
        if not accepted_parity:
            missing=sorted(legacy_keys-engine_keys)[:8]
            extra=sorted(engine_keys-legacy_keys)[:8]
            report += ["",f"### {cid} first timestamp differences",
                       f"- Legacy-only (segment,index,split): `{missing}`",
                       f"- Engine-only (segment,index,split): `{extra}`",""]
    report += ["","## Interpretation","",
        "- PASS means the accepted timestamps and per-trade outcomes agree with the original legacy builder on this exact current data snapshot.",
        "- This does not recreate or validate the unavailable historical raw CSV used for the old registry counts.",
        "- A parity PASS with a historical TEST cohort mismatch means the rules agree on the current snapshot; the old/new data difference remains unresolved.",
        "- No strategy is confirmed by this software-parity audit.",""]
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text("\n".join(report),encoding="utf-8")
    print(f"Legacy/universal parity audit complete: candidates=4; failures={failures}; report={a.out}")
    if failures:
        raise SystemExit(1)

if __name__=="__main__":
    main()
