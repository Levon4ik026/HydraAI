#!/usr/bin/env python3
"""Predeclared low-dimensional interaction screen; discovery is train-only.

No holdout statistic is used to choose an interaction, cutpoint, or cell.
The selected train rule is frozen and evaluated once on chronological holdout.
"""
from __future__ import annotations

import argparse
import math
import statistics
from collections import defaultdict
from pathlib import Path

from win_loss_feature_audit import (
    SPLIT_DATE, parse_time, load_m1, make_m5, build_ledger,
)

PAYOUT = 0.92
MIN_TRAIN_CELL = 8
MIN_TRAIN_LIFT_PP = 8.0
# Small, predeclared set; no exhaustive feature-pair search.
INTERACTIONS = (
    ("atr14_close", "body_range", "volatility x body"),
    ("atr14_close", "upper_wick_range", "volatility x upper wick"),
    ("atr14_close", "lower_wick_range", "volatility x lower wick"),
    ("range_atr", "body_range", "bar range x body"),
    ("ema20_50_atr", "body_range", "trend separation x body"),
    ("ema20_50_atr", "upper_wick_range", "trend separation x upper wick"),
    ("di_spread", "return3_atr", "DMI spread x 3-bar impulse"),
)


def median(values):
    return statistics.median(values) if values else None


def stats(records):
    wins = sum(r["outcome"] == "WIN" for r in records)
    losses = sum(r["outcome"] == "LOSS" for r in records)
    draws = sum(r["outcome"] == "DRAW" for r in records)
    decisive = wins + losses
    net = wins * PAYOUT - losses
    equity = peak = max_dd = 0.0
    losing_streak = current = 0
    for r in sorted(records, key=lambda x: x["signal_time"]):
        if r["outcome"] == "WIN":
            equity += PAYOUT
            current = 0
        elif r["outcome"] == "LOSS":
            equity -= 1
            current += 1
            losing_streak = max(losing_streak, current)
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    return {
        "n": len(records), "w": wins, "l": losses, "d": draws,
        "wr": 100 * wins / decisive if decisive else None,
        "net": net, "roi": 100 * net / len(records) if records else None,
        "pf": wins * PAYOUT / losses if losses else (math.inf if wins else None),
        "mdd": max_dd, "max_ls": losing_streak,
    }


def cell_key(x, y, xcut, ycut):
    if x is None or y is None:
        return None
    return ("H" if x > xcut else "L") + ("H" if y > ycut else "L")


def fmt(s):
    if s["wr"] is None:
        wr = "n/a"
    else:
        wr = f'{s["wr"]:.2f}%'
    pf = "inf" if s["pf"] == math.inf else ("n/a" if s["pf"] is None else f'{s["pf"]:.2f}')
    roi = "n/a" if s["roi"] is None else f'{s["roi"]:.2f}%'
    return (f'n={s["n"]} W/L/D={s["w"]}/{s["l"]}/{s["d"]}; '
            f'decisive WR={wr}; net={s["net"]:+.2f}u; ROI={roi}; PF={pf}; '
            f'MDD={s["mdd"]:.2f}u; max losing streak={s["max_ls"]}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path("eurusd_history_extended.csv"))
    ap.add_argument("--out", type=Path, default=Path("research/INTERACTION_SCREEN.md"))
    args = ap.parse_args()
    m1 = load_m1(args.data)
    segments = make_m5(m1)
    ledger = build_ledger(segments, parse_time(SPLIT_DATE), 15.0)
    train = [r for r in ledger if r["period"] == "TRAIN"]
    holdout = [r for r in ledger if r["period"] == "HOLDOUT"]
    lines = [
        "# Train-only interaction screen: frozen CALL / PUT M5 rule", "",
        f"Source: {args.data}; M1 rows={len(m1)}; complete M5 bars={sum(map(len, segments))}; segments={len(segments)}.",
        f"Eligible signal events={len(ledger)}; train={len(train)}; chronological holdout={len(holdout)}.",
        "Frozen base trigger: BB(20,2) re-entry + Williams %R(14) cross; ADX(14)>=15; signal at closed M5 close, entry next M5 open, settle at that next candle close.",
        "Payout 92%; WIN +0.92u, LOSS -1u, DRAW 0u. Draws excluded from decisive WR.",
        "Discovery protocol: only 7 predeclared pairs; each feature split at its TRAIN median; four 2x2 cells per pair; minimum 8 TRAIN observations per cell; select at most one cell per direction only if train decisive-WR lift >=8 percentage points and train net >0.",
        "The selected pair, cutpoints and cell are frozen before holdout evaluation. Holdout is evaluated once and never used to revise the rule. This remains exploratory; cell selection across 56 direction/cell candidates creates substantial selection bias, and the small dataset cannot establish edge.",
        "", "## Baselines", f"- CALL train: {fmt(stats([r for r in train if r['direction']=='CALL']))}",
        f"- CALL holdout: {fmt(stats([r for r in holdout if r['direction']=='CALL']))}",
        f"- PUT train: {fmt(stats([r for r in train if r['direction']=='PUT']))}",
        f"- PUT holdout: {fmt(stats([r for r in holdout if r['direction']=='PUT']))}",
        "", "## Train discovery (full table; no holdout columns used for selection)",
    ]
    frozen = {}
    for direction in ("CALL", "PUT"):
        candidates = []
        base = [r for r in train if r["direction"] == direction and r["outcome"] != "DRAW"]
        base_wr = 100 * sum(r["outcome"] == "WIN" for r in base) / len(base) if base else 0
        lines += [f"", f"### {direction}"]
        for xname, yname, label in INTERACTIONS:
            xvals = [r["features"][xname] for r in train if r["direction"] == direction and r["features"][xname] is not None]
            yvals = [r["features"][yname] for r in train if r["direction"] == direction and r["features"][yname] is not None]
            xcut, ycut = median(xvals), median(yvals)
            if xcut is None or ycut is None:
                continue
            groups = defaultdict(list)
            for r in train:
                if r["direction"] != direction:
                    continue
                key = cell_key(r["features"][xname], r["features"][yname], xcut, ycut)
                if key:
                    groups[key].append(r)
            for key in ("LL", "LH", "HL", "HH"):
                group = groups[key]
                st = stats(group)
                decisive = st["w"] + st["l"]
                lift = (st["wr"] - base_wr) if st["wr"] is not None else None
                eligible = len(group) >= MIN_TRAIN_CELL and decisive > 0 and st["net"] > 0 and lift is not None and lift >= MIN_TRAIN_LIFT_PP
                lines.append(f"- {label} [{xname} {'>' if key[0]=='H' else '<='} {xcut:.8g}; {yname} {'>' if key[1]=='H' else '<='} {ycut:.8g}; cell={key}]: {fmt(st)}; lift={lift if lift is not None else float('nan'):+.2f}pp; eligible={eligible}")
                if eligible:
                    # Ranking uses train net per observation, then train WR lift, then count.
                    candidates.append((st["net"] / len(group), lift, len(group), label, xname, yname, xcut, ycut, key, st))
        if candidates:
            chosen = max(candidates, key=lambda c: (c[0], c[1], c[2]))
            frozen[direction] = chosen
            lines.append(f"**FROZEN TRAIN PICK:** {chosen[3]} / {chosen[8]} | {chosen[4]} median={chosen[5] if False else chosen[6]:.8g}; {chosen[5]} median={chosen[7]:.8g}.")
        else:
            lines.append("**NO TRAIN CANDIDATE:** no predeclared cell met all minimum criteria.")
    lines += ["", "## Frozen rule evaluated on holdout", "No threshold or feature selection was performed on holdout."]
    for direction in ("CALL", "PUT"):
        chosen = frozen.get(direction)
        if not chosen:
            lines.append(f"- {direction}: no rule frozen; holdout candidate result = not applicable.")
            continue
        _, _, _, label, xname, yname, xcut, ycut, key, train_stats = chosen
        selected = [r for r in holdout if r["direction"] == direction and cell_key(r["features"][xname], r["features"][yname], xcut, ycut) == key]
        lines.append(f"- {direction} frozen {label} cell={key}: x={xname} median {xcut:.8g}; y={yname} median {ycut:.8g}.")
        lines.append(f"  - TRAIN selected cell: {fmt(train_stats)}.")
        lines.append(f"  - HOLDOUT selected cell: {fmt(stats(selected))}.")
        lines.append(f"  - HOLDOUT coverage: {len(selected)}/{sum(r['direction']==direction for r in holdout)} direction signals ({100*len(selected)/max(1,sum(r['direction']==direction for r in holdout)):.1f}%).")
    lines += ["", "## Verdict", "A positive train cell is only a discovery hypothesis. The holdout is small and has already been inspected in earlier research, so it is not truly untouched. No interaction rule is approved for the desktop math core. Prospective, frozen-parameter validation is required before any production change."]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"Report written: {args.out}")


if __name__ == "__main__":
    main()
