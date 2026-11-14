#!/usr/bin/env python3
"""Regime and contiguous-calendar-block robustness audit for HYDRA two-stage M1 model."""
from __future__ import annotations
import argparse
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
try:
    from m1_move_occurrence_direction_audit import read_bars, split_segments, build_samples
except ImportError:
    from research.m1_move_occurrence_direction_audit import read_bars, split_segments, build_samples

H = 10
PAYOUTS = (.85, .90, .92)
SEED = 20261109

def outcome_stats(records, indices, probs, payout=.92):
    w = l = d = 0
    for i, p in zip(indices, probs):
        y = records[i]["outcomes"][H]
        if y == 0: d += 1
        elif (y > 0) == (p >= .5): w += 1
        else: l += 1
    ndec = w + l
    return len(indices), w, l, d, (100*w/ndec if ndec else float("nan")), w*payout-l

def block_bootstrap(daily, block_days, reps=10000):
    """Moving contiguous block bootstrap over every calendar day, including zero-trade days."""
    n = len(daily)
    if n < block_days * 3:
        return float("nan"), float("nan")
    rng = np.random.default_rng(SEED + block_days)
    nblocks = int(np.ceil(n / block_days))
    starts = rng.integers(0, n - block_days + 1, size=(reps, nblocks))
    samples = np.empty((reps, nblocks * block_days), dtype=float)
    offsets = np.arange(block_days)
    for j in range(nblocks):
        samples[:, j*block_days:(j+1)*block_days] = daily[starts[:, j, None] + offsets]
    means = samples[:, :n].mean(axis=1)
    lo, hi = np.quantile(means, [.025, .975])
    return float(lo), float(hi)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("research/M1_REGIME_BLOCK_AUDIT.md"))
    a = ap.parse_args()

    bars = read_bars(a.data)
    segments = split_segments(bars)
    X, event_y, records = build_samples(segments, 5.0)
    order = np.argsort(np.asarray([r["time"].timestamp() for r in records]))
    X, event_y = X[order], event_y[order]
    records = [records[k] for k in order]
    n = len(records); i1, i2 = int(n*.60), int(n*.80)
    t1, t2 = records[i1]["time"], records[i2]["time"]
    train = np.asarray([i for i,r in enumerate(records[:i1]) if r["time"]+timedelta(minutes=15)<t1], dtype=int)
    val = np.asarray([i for i,r in enumerate(records[i1:i2], start=i1) if r["time"]+timedelta(minutes=15)<t2], dtype=int)
    test = np.arange(i2, n, dtype=int)

    gate = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
        LogisticRegression(C=.1, max_iter=1200, solver="lbfgs", random_state=23))
    gate.fit(X[train], event_y[train])
    pv = gate.predict_proba(X[val])[:,1]; pt = gate.predict_proba(X[test])[:,1]
    event_cut = float(np.quantile(pv,.90))
    vg = val[pv >= event_cut]; tg = test[pt >= event_cut]

    train_dir = np.asarray([i for i in train if event_y[i] == 1 and records[i]["outcomes"][H] != 0], dtype=int)
    ydir = np.asarray([int(records[i]["outcomes"][H] > 0) for i in train_dir])
    direction = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
        LogisticRegression(C=.1, max_iter=1200, solver="lbfgs", class_weight="balanced", random_state=29))
    direction.fit(X[train_dir], ydir)
    pvg = direction.predict_proba(X[vg])[:,1]
    conf_cut = float(np.quantile(np.maximum(pvg,1-pvg), .75))
    ptg = direction.predict_proba(X[tg])[:,1]
    conf = np.maximum(ptg,1-ptg)
    keep = conf >= conf_cut
    selected = tg[keep]
    selected_probs = ptg[keep]
    primary = outcome_stats(records, selected.tolist(), selected_probs.tolist())

    # Regime boundaries are estimated only on TRAIN, then frozen for TEST.
    vol_q = np.quantile(X[train,3], [1/3,2/3])
    eff_q = np.quantile(X[train,14], [1/3,2/3])
    lines = [
        "# HYDRA — M1 regime and contiguous-block robustness audit", "",
        f"Rows={len(bars):,}; segments={len(segments):,}; samples={n:,}; TRAIN/VAL/TEST={len(train):,}/{len(val):,}/{len(test):,}.",
        "Chronological 60/20/20; 15m purge; models fit on TRAIN; event gate and confidence cutoff calibrated on VALIDATION.",
        f"Frozen event cutoff={event_cut:.6f}; TEST event-gated={len(tg):,}; frozen confidence cutoff={conf_cut:.6f}; primary TEST trades={len(selected):,}.",
        "Outcome: next M1 open to 10-minute close; Dukascopy EURUSD BID proxy, not Pocket Option quotes; no platform spread/latency.",
        f"Primary: W/L/D={primary[1]}/{primary[2]}/{primary[3]}, decisive WR={primary[4]:.2f}%, net @92%={primary[5]:+.2f}u.", "",
        "## Volatility regimes (boundaries from TRAIN trailing 30-bar absolute return sum)",
        f"TRAIN tertile cutoffs: low <= {vol_q[0]:.8f}; medium <= {vol_q[1]:.8f}; high > {vol_q[1]:.8f}.",
        "| TEST regime | Trades | W/L/D | WR | Net @85% | Net @90% | Net @92% |",
        "|---|---:|---:|---:|---:|---:|---:|"
    ]
    vol = X[selected,3]
    for name, mask in [
        ("LOW", vol <= vol_q[0]),
        ("MID", (vol > vol_q[0]) & (vol <= vol_q[1])),
        ("HIGH", vol > vol_q[1]),
    ]:
        inds = selected[mask].tolist(); probs = selected_probs[mask].tolist()
        s = outcome_stats(records, inds, probs)
        nets = [s[1]*p-s[2] for p in PAYOUTS]
        lines.append(f"| {name} | {s[0]} | {s[1]}/{s[2]}/{s[3]} | {s[4]:.2f}% | {nets[0]:+.2f}u | {nets[1]:+.2f}u | {nets[2]:+.2f}u |")

    lines += ["", "## Trend / range regimes (trailing 15-bar efficiency; TRAIN tertiles)",
        f"TRAIN efficiency cutoffs: range <= {eff_q[0]:.4f}; mixed <= {eff_q[1]:.4f}; trend > {eff_q[1]:.4f}.",
        "| TEST regime | Trades | W/L/D | WR | Net @92% |",
        "|---|---:|---:|---:|---:|"]
    eff = X[selected,14]
    for name, mask in [
        ("RANGE / LOW EFFICIENCY", eff <= eff_q[0]),
        ("MIXED", (eff > eff_q[0]) & (eff <= eff_q[1])),
        ("TREND / HIGH EFFICIENCY", eff > eff_q[1]),
    ]:
        s = outcome_stats(records, selected[mask].tolist(), selected_probs[mask].tolist())
        lines.append(f"| {name} | {s[0]} | {s[1]}/{s[2]}/{s[3]} | {s[4]:.2f}% | {s[5]:+.2f}u |")

    # Daily P&L vector spans every calendar day in TEST, zero-trade days included.
    first = records[int(test[0])]["time"].date()
    last = records[int(test[-1])]["time"].date()
    day_list = [first + timedelta(days=k) for k in range((last-first).days+1)]
    day_net = {d: 0.0 for d in day_list}
    for i,p in zip(selected.tolist(), selected_probs.tolist()):
        y = records[i]["outcomes"][H]
        if y == 0: continue
        won = (y > 0) == (p >= .5)
        day_net[records[i]["time"].date()] += .92 if won else -1.0
    daily = np.asarray([day_net[d] for d in day_list], dtype=float)
    lines += ["", "## Contiguous calendar-day block bootstrap (primary 75% confidence rule)",
        f"TEST calendar span: {len(day_list)} days; includes days with zero trades. Observed total net @92%={daily.sum():+.2f}u; mean per calendar day={daily.mean():+.4f}u.",
        "| Contiguous block length | 95% CI mean net per calendar day @92% |",
        "|---:|---:|"]
    for b in (3,5,10):
        lo,hi = block_bootstrap(daily,b)
        lines.append(f"| {b} days | {lo:+.4f} to {hi:+.4f}u |")
    lines += ["", "## Interpretation",
        "- Regime groups are descriptive TEST slices; their boundaries are frozen from TRAIN, not optimized on TEST.",
        "- Block bootstrap preserves short-range dependence across adjacent calendar days and includes zero-trade days; it does not remove all nonstationarity.",
        "- Regime slices and bootstrap are diagnostics on the same historical TEST segment, not a new untouched holdout.",
        "- No strategy integration is authorized. Prospective validation on fresh Pocket Option quotes and actual payout remains necessary."]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(f"Wrote {a.out}; primary={primary[0]}; calendar_days={len(day_list)}")

if __name__ == "__main__":
    main()
