#!/usr/bin/env python3
"""Post-signal path audit for aligned 12-bar liquidity sweeps.

This is an outcome-path diagnostic, NOT a predictive filter: all path metrics
are measured after entry and are never used to generate or select signals.
"""
from __future__ import annotations
import argparse, statistics
from collections import defaultdict
from pathlib import Path

from long_history_validation import read_duka, make_events, PAYOUT, m5_close_time
from reproduce_m5_bb_williams_adx import make_m5

HORIZON = 4
WARMUP = 50

def qtile(values, q):
    xs = sorted(x for x in values if x is not None)
    if not xs:
        return float("nan")
    return xs[min(len(xs)-1, int((len(xs)-1)*q))]

def summarize(rows, key):
    vals = [r[key] for r in rows if r.get(key) is not None]
    if not vals:
        return "n/a"
    return f"{statistics.median(vals):.3f} [{qtile(vals,.25):.3f}, {qtile(vals,.75):.3f}]"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("research/POST_SWEEP_PATH_AUDIT.md"))
    args = ap.parse_args()

    m1 = read_duka(args.data)
    segments = make_m5(m1)
    events = make_events(segments, 15)
    days = sorted({e["signal_time"].date() for e in events})
    d1, d2 = days[int(len(days)*.60)], days[int(len(days)*.80)]
    byseg = defaultdict(list)
    for e in events:
        byseg[e["segment"]].append(e)

    rows = []
    excluded = 0
    for sid, bars in enumerate(segments):
        if not byseg[sid]:
            continue
        for e in byseg[sid]:
            i = e["bar_index"]
            if i < WARMUP or i + HORIZON >= len(bars):
                excluded += 1
                continue
            side = e["direction"]
            cur = bars[i]
            prior = bars[i-12:i]
            if len(prior) != 12:
                excluded += 1
                continue
            if side == "CALL":
                level = min(b.low for b in prior)
                aligned_sweep = cur.low < level and cur.close > level
                signed = 1.0
            else:
                level = max(b.high for b in prior)
                aligned_sweep = cur.high > level and cur.close < level
                signed = -1.0
            if not aligned_sweep:
                continue

            entry = bars[i+1].open
            atr_ranges = []
            for j in range(i-13, i+1):
                if j <= 0:
                    continue
                b, p = bars[j], bars[j-1]
                atr_ranges.append(max(b.high-b.low, abs(b.high-p.close), abs(b.low-p.close)))
            if len(atr_ranges) != 14:
                continue
            atr = sum(atr_ranges)/14
            if atr <= 0:
                continue

            future = bars[i+1:i+HORIZON+1]
            favorable = []
            adverse = []
            for b in future:
                if side == "CALL":
                    favorable.append(max(0.0, b.high-entry))
                    adverse.append(max(0.0, entry-b.low))
                else:
                    favorable.append(max(0.0, entry-b.low))
                    adverse.append(max(0.0, b.high-entry))
            mfe = max(favorable)
            mae = max(adverse)
            exit_signed = signed * (future[-1].close-entry)
            outcome = "DRAW" if abs(exit_signed) < 1e-12 else "WIN" if exit_signed > 0 else "LOSS"

            close_path = {}
            for n in (1, 2, 3, 4):
                b = future[n-1]
                close_path[f"close_{n}_atr"] = signed*(b.close-entry)/atr
                close_path[f"favorable_close_{n}"] = 1 if close_path[f"close_{n}_atr"] > 0 else 0

            # A retest is a later candle trading back within 0.10 ATR of the
            # swept level. It is descriptive and does not imply trade failure.
            tolerance = 0.10*atr
            retest = False
            retest_holds = False
            for b in future:
                if b.low <= level+tolerance and b.high >= level-tolerance:
                    retest = True
                    if (b.close > level if side == "CALL" else b.close < level):
                        retest_holds = True
                    break

            signal_day = cur.timestamp.date()
            period = "TRAIN" if signal_day < d1 else "VALIDATION" if signal_day < d2 else "TEST"
            rows.append({
                "period": period, "side": side, "outcome": outcome,
                "mfe_atr": mfe/atr, "mae_atr": mae/atr,
                "mfe_mae_ratio": mfe/mae if mae > 0 else None,
                "retest": int(retest), "retest_holds": int(retest_holds),
                **close_path,
            })

    if not rows:
        raise SystemExit("No eligible aligned sweep paths.")
    lines = [
        "# HYDRA — post-sweep price-path audit", "",
        f"Source: Dukascopy EURUSD M1 BID; raw M1={len(m1):,}; complete M5={sum(map(len,segments)):,}; segments={len(segments)}.",
        f"Coverage: {m1[0].timestamp.isoformat()} — {m1[-1].timestamp.isoformat()}.",
        f"Eligible aligned 12-bar sweeps with {WARMUP}-bar warmup and full 20m path: {len(rows):,}; excluded before sweep/path checks={excluded:,}.",
        f"Chronological split boundaries: TRAIN < {d1}; VALIDATION < {d2}; TEST >= {d2}.",
        "Frozen trigger unchanged: BB(20,2) re-entry + Williams %R(14) cross + ADX>=15; entry next M5 open, exit fourth M5 close; payout +0.92/-1/0.",
        "IMPORTANT: all path metrics below occur AFTER entry. They explain realized trade paths and are not causal pre-entry predictors; they must not be used as filters.",
        "Retest = any of the next four M5 candles trades within 0.10 signal-ATR of the swept level. Intrabar ordering is unknown from OHLC.",
        "External Dukascopy BID proxy, not Pocket Option quotes. Overlapping trades and serial dependence remain.", "",
        "## Outcome counts", "",
        "| Split | Side | W/L/D | Decisive WR | Net units |",
        "|---|---|---:|---:|---:|",
    ]
    for p in ("TRAIN","VALIDATION","TEST"):
        for side in ("ALL","CALL","PUT"):
            sub=[r for r in rows if r["period"]==p and (side=="ALL" or r["side"]==side)]
            w=sum(r["outcome"]=="WIN" for r in sub)
            l=sum(r["outcome"]=="LOSS" for r in sub)
            d=len(sub)-w-l
            wr=100*w/(w+l) if w+l else float("nan")
            net=w*PAYOUT-l
            lines.append(f"| {p} | {side} | {w}/{l}/{d} | {wr:.2f}% | {net:+.2f}u |")

    metrics=("mfe_atr","mae_atr","mfe_mae_ratio","close_1_atr","close_2_atr","close_3_atr","close_4_atr")
    for p in ("TRAIN","VALIDATION","TEST"):
        lines += ["",f"## Realized path by final outcome — {p}","",
                  "| Side/outcome | n | MFE ATR median [Q1,Q3] | MAE ATR median [Q1,Q3] | MFE/MAE median | Close +1 bar ATR | +2 bars ATR | +3 bars ATR | +4 bars ATR |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for side in ("ALL","CALL","PUT"):
            for outcome in ("WIN","LOSS","DRAW"):
                sub=[r for r in rows if r["period"]==p and r["outcome"]==outcome and (side=="ALL" or r["side"]==side)]
                if len(sub)<5:
                    continue
                lines.append("| "+f"{side} {outcome} | {len(sub)} | "+" | ".join(summarize(sub,k) for k in metrics)+" |")

    lines += ["", "## Retest behavior", "",
              "| Split | Side | n | Retest within 0.10 ATR | Retest closes on reclaimed side |",
              "|---|---|---:|---:|---:|"]
    for p in ("TRAIN","VALIDATION","TEST"):
        for side in ("ALL","CALL","PUT"):
            sub=[r for r in rows if r["period"]==p and (side=="ALL" or r["side"]==side)]
            if not sub:
                continue
            ret=sum(r["retest"] for r in sub)
            holds=sum(r["retest_holds"] for r in sub)
            lines.append(f"| {p} | {side} | {len(sub)} | {100*ret/len(sub):.1f}% | {100*holds/len(sub):.1f}% |")

    lines += ["", "## Interpretation guardrails", "",
              "- MFE/MAE and post-entry closes are realized-path descriptors, not information available at signal time.",
              "- A post-entry pattern cannot be inserted into the entry filter; it may motivate a separately specified exit-management experiment only.",
              "- Do not infer a predictive edge from differences between winners and losers: outcome groups are defined by the same future path.",
              "- Any exit rule must be predeclared and tested on a separate untouched chronological period, including payout and execution assumptions."]
    args.out.parent.mkdir(parents=True,exist_ok=True)
    report="\n".join(lines)+"\n"
    args.out.write_text(report,encoding="utf-8")
    print(report)

if __name__ == "__main__":
    main()
