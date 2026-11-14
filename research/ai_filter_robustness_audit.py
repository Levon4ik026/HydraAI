#!/usr/bin/env python3
"""Robustness diagnostics for the frozen logistic AI filter; research-only."""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import numpy as np

from ai_intelligence_engine_audit import (
    build_dataset, choose_threshold, metrics, model_factories, split_rows
)
from long_history_validation import read_duka
from reproduce_m5_bb_williams_adx import make_m5

BOOTSTRAPS = 5000
SEED = 20261108


def block_bootstrap(rows, keep, rng):
    grouped = defaultdict(list)
    for row, accepted in zip(rows, keep):
        if accepted:
            grouped[row["time"].date().isoformat()].append(row)
    days = list(grouped)
    if len(days) < 2:
        return None
    nets, wrs, counts = [], [], []
    for _ in range(BOOTSTRAPS):
        sample_days = rng.choice(days, size=len(days), replace=True)
        sample = [r for day in sample_days for r in grouped[day]]
        m = metrics(sample)
        nets.append(m["net"])
        wrs.append(m["wr"])
        counts.append(m["n"])
    return {
        "days": len(days),
        "net_ci": np.percentile(nets, [2.5, 50, 97.5]).tolist(),
        "wr_ci": np.percentile(wrs, [2.5, 50, 97.5]).tolist(),
        "count_ci": np.percentile(counts, [2.5, 50, 97.5]).tolist(),
        "positive_net_fraction": float(np.mean(np.asarray(nets) > 0)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("research/AI_FILTER_ROBUSTNESS.md"))
    args = ap.parse_args()

    m1 = read_duka(args.data)
    segments = make_m5(m1)
    rows, triggers = build_dataset(segments, 15)
    train, validation, test, d1, d2 = split_rows(rows)
    decisive_train = [r for r in train if r["outcome"] != "DRAW"]
    x_train = np.asarray([r["features"] for r in decisive_train], dtype=float)
    y_train = np.asarray([1 if r["outcome"] == "WIN" else 0 for r in decisive_train])
    x_val = np.asarray([r["features"] for r in validation], dtype=float)
    x_test = np.asarray([r["features"] for r in test], dtype=float)

    model = model_factories()["logistic"]()
    model.fit(x_train, y_train)
    p_val = model.predict_proba(x_val)[:, 1]
    selected = choose_threshold(validation, p_val)
    if selected is None:
        raise SystemExit("No validation threshold met minimum sample size.")
    threshold = selected["threshold"]
    p_test = model.predict_proba(x_test)[:, 1]

    lines = [
        "# HYDRA — Logistic AI filter robustness diagnostics", "",
        f"Raw M1 rows={len(m1):,}; M5 segments={len(segments):,}; trigger events={triggers:,}; eligible rows={len(rows):,}.",
        f"Same chronological split as primary AI audit: TRAIN={len(train)}, VALIDATION={len(validation)}, TEST={len(test)}; boundaries {d1} / {d2}.",
        f"Logistic threshold reselected on VALIDATION only: {threshold:.3f}; validation accepted={selected['metrics']['n']}/{len(validation)}, net={selected['metrics']['net']:+.2f}u.",
        "All following diagnostics are on the historical TEST and are descriptive, not confirmatory. The historical test has already been inspected in prior research.", "",
        "## Test threshold sensitivity", "",
        "| Threshold | Accepted | Coverage | W/L/D | Decisive WR | Net units | PF |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for t in (0.50, 0.525, 0.55, 0.575, 0.60, 0.625, 0.65):
        keep = p_test >= t
        m = metrics(test, keep)
        lines.append(f"| {t:.3f} | {m['n']} | {m['n']/len(test):.1%} | {m['w']}/{m['l']}/{m['d']} | {m['wr']:.2f}% | {m['net']:+.2f}u | {m['pf']:.3f} |")

    locked_keep = p_test >= threshold
    locked = metrics(test, locked_keep)
    boot = block_bootstrap(test, locked_keep, np.random.default_rng(SEED))
    lines += ["", "## Trading-day block bootstrap (locked validation threshold)", "",
      f"Accepted test trades={locked['n']}/{len(test)} ({locked['n']/len(test):.1%}); W/L/D={locked['w']}/{locked['l']}/{locked['d']}; WR={locked['wr']:.2f}%; net={locked['net']:+.2f}u; PF={locked['pf']:.3f}.",
      f"Accepted trading days={boot['days']}; {BOOTSTRAPS:,} bootstrap resamples, sampling whole UTC signal days with replacement (seed={SEED}).",
      f"- Net units percentile 2.5 / 50 / 97.5: {boot['net_ci'][0]:+.2f} / {boot['net_ci'][1]:+.2f} / {boot['net_ci'][2]:+.2f}u.",
      f"- Decisive WR percentile 2.5 / 50 / 97.5: {boot['wr_ci'][0]:.2f}% / {boot['wr_ci'][1]:.2f}% / {boot['wr_ci'][2]:.2f}%.",
      f"- Accepted trade count percentile 2.5 / 50 / 97.5: {boot['count_ci'][0]:.0f} / {boot['count_ci'][1]:.0f} / {boot['count_ci'][2]:.0f}.",
      f"- Fraction of bootstrap samples with positive net: {boot['positive_net_fraction']:.1%}.",
      "This day-cluster bootstrap partially respects within-day dependence, but cannot remove historical selection bias, regime drift, quote-source mismatch, or overlapping-horizon dependence across adjacent days.", "",
      "## Monthly test slices (locked threshold)", "",
      "| Month UTC | Accepted | W/L/D | Decisive WR | Net units |",
      "|---|---:|---:|---:|---:|"]
    monthly = defaultdict(list)
    for row, accepted in zip(test, locked_keep):
        if accepted:
            monthly[row["time"].strftime("%Y-%m")].append(row)
    for month in sorted({r["time"].strftime("%Y-%m") for r in test}):
        group = monthly.get(month, [])
        m = metrics(group)
        lines.append(f"| {month} | {m['n']} | {m['w']}/{m['l']}/{m['d']} | {m['wr']:.2f}% | {m['net']:+.2f}u |")
    lines += ["", "## Guardrails", "",
      "- Threshold sensitivity is a diagnostic only; do not choose a threshold from TEST.",
      "- Small monthly samples are highly noisy; a profitable month is not evidence of a stable edge.",
      "- No deployment, no local files changed, no automated trading.", ""]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    report = "\n".join(lines)
    args.out.write_text(report + "\n", encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
