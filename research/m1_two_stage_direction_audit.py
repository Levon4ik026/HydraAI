#!/usr/bin/env python3
"""Two-stage causal M1 audit: event gate, then conditional direction model.

Stage 1 reuses the frozen causal excursion detector. Stage 2 is trained only
on TRAIN rows whose future excursion label is positive, to predict the sign
of the 10-minute close outcome. The event and confidence thresholds are
frozen from VALIDATION and evaluated once on TEST. Research only.
"""
from __future__ import annotations

import argparse
from datetime import timedelta
from pathlib import Path

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss, accuracy_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

try:
    from m1_move_occurrence_direction_audit import (
        PAYOUT, MOVE_PIPS, read_bars, split_segments, build_samples
    )
except ImportError:
    from research.m1_move_occurrence_direction_audit import (
        PAYOUT, MOVE_PIPS, read_bars, split_segments, build_samples
    )


def fixed_payout_stats(rows, indices, side_probs=None):
    wins = losses = draws = 0
    for j, idx in enumerate(indices):
        outcome = rows[idx]["outcomes"][10]
        if outcome == 0:
            draws += 1
            continue
        if side_probs is None:
            predicted_up = rows[idx]["momentum_sign"] > 0
        else:
            predicted_up = side_probs[j] >= 0.5
        if (outcome > 0) == predicted_up:
            wins += 1
        else:
            losses += 1
    decisive = wins + losses
    wr = 100 * wins / decisive if decisive else float("nan")
    net = wins * PAYOUT - losses
    return len(indices), wins, losses, draws, wr, net


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("research/M1_TWO_STAGE_DIRECTION_AUDIT.md"))
    ap.add_argument("--move-pips", type=float, default=MOVE_PIPS)
    a = ap.parse_args()

    bars = read_bars(a.data)
    segments = split_segments(bars)
    X, event_y, records = build_samples(segments, a.move_pips)
    order = np.argsort(np.asarray([r["time"].timestamp() for r in records]))
    X, event_y = X[order], event_y[order]
    records = [records[k] for k in order]

    n = len(records)
    i1, i2 = int(n * .60), int(n * .80)
    t1, t2 = records[i1]["time"], records[i2]["time"]
    train = np.asarray([i for i, r in enumerate(records[:i1]) if r["time"] + timedelta(minutes=15) < t1], dtype=int)
    val = np.asarray([i for i, r in enumerate(records[i1:i2], start=i1) if r["time"] + timedelta(minutes=15) < t2], dtype=int)
    test = np.arange(i2, n, dtype=int)
    if min(len(train), len(val), len(test)) < 300:
        raise RuntimeError(f"Insufficient split sizes: train={len(train)}, validation={len(val)}, test={len(test)}")

    # Stage 1: causal event probability model, fit only on TRAIN.
    event_model = make_pipeline(
        SimpleImputer(strategy="median"), StandardScaler(),
        LogisticRegression(C=.1, max_iter=1200, solver="lbfgs", random_state=23),
    )
    event_model.fit(X[train], event_y[train])
    p_val_event = event_model.predict_proba(X[val])[:, 1]
    p_test_event = event_model.predict_proba(X[test])[:, 1]
    event_cut = float(np.quantile(p_val_event, .90))
    val_gate = val[p_val_event >= event_cut]
    test_gate = test[p_test_event >= event_cut]

    # Stage 2: direction classifier sees only TRAIN excursion events.
    # Label is 10-minute close direction from the next M1 open; draws are omitted.
    train_dir = np.asarray([
        i for i in train if event_y[i] == 1 and records[i]["outcomes"][10] != 0
    ], dtype=int)
    if len(train_dir) < 100 or len(set(1 if records[i]["outcomes"][10] > 0 else 0 for i in train_dir)) < 2:
        raise RuntimeError(f"Insufficient conditional direction training rows: {len(train_dir)}")
    y_dir_train = np.asarray([1 if records[i]["outcomes"][10] > 0 else 0 for i in train_dir], dtype=int)
    direction_model = make_pipeline(
        SimpleImputer(strategy="median"), StandardScaler(),
        LogisticRegression(C=.1, max_iter=1200, solver="lbfgs", class_weight="balanced", random_state=29),
    )
    direction_model.fit(X[train_dir], y_dir_train)

    # Validation-only confidence cutoff: upper quartile of confidence among
    # samples selected by the frozen event gate. Do not condition on future event.
    if len(val_gate) < 50:
        raise RuntimeError(f"Too few validation rows pass frozen event gate: {len(val_gate)}")
    p_val_up = direction_model.predict_proba(X[val_gate])[:, 1]
    val_confidence = np.maximum(p_val_up, 1 - p_val_up)
    confidence_cut = float(np.quantile(val_confidence, .75))

    p_test_up = direction_model.predict_proba(X[test_gate])[:, 1] if len(test_gate) else np.asarray([])
    test_confidence = np.maximum(p_test_up, 1 - p_test_up) if len(test_gate) else np.asarray([])
    confident_mask = test_confidence >= confidence_cut
    confident_test = test_gate[confident_mask]
    confident_probs = p_test_up[confident_mask]

    # Simple momentum and contrarian baselines on the same event-gated test rows.
    def rule_stats(indices, contrarian=False):
        wins = losses = draws = 0
        for idx in indices:
            outcome = records[idx]["outcomes"][10]
            if outcome == 0:
                draws += 1
                continue
            predicted_up = records[idx]["momentum_sign"] > 0
            if contrarian:
                predicted_up = not predicted_up
            if (outcome > 0) == predicted_up:
                wins += 1
            else:
                losses += 1
        decisive = wins + losses
        return len(indices), wins, losses, draws, (100*wins/decisive if decisive else float("nan")), wins*PAYOUT-losses

    ml_stats = fixed_payout_stats(records, confident_test.tolist(), confident_probs.tolist())
    mom_stats = rule_stats(test_gate.tolist(), False)
    contra_stats = rule_stats(test_gate.tolist(), True)
    all_gate_stats = rule_stats(test_gate.tolist(), False)

    test_labels = np.asarray([1 if records[i]["outcomes"][10] > 0 else 0 for i in test_gate if records[i]["outcomes"][10] != 0], dtype=int)
    test_probs_for_auc = np.asarray([p for i,p in zip(test_gate,p_test_up) if records[i]["outcomes"][10] != 0], dtype=float)
    direction_auc = roc_auc_score(test_labels, test_probs_for_auc) if len(set(test_labels.tolist())) == 2 else float("nan")
    direction_brier = brier_score_loss(test_labels, test_probs_for_auc) if len(test_labels) else float("nan")

    lines = [
        "# HYDRA — two-stage M1 event-gate + conditional-direction audit", "",
        f"Data: Dukascopy EURUSD M1 BID; raw rows={len(bars):,}; continuous segments={len(segments):,}; samples={n:,}.",
        f"Sampling every 5 minutes; event target >= {a.move_pips:g} pips in next 5 M1 bars; direction target is 10-minute close from next M1 open.",
        "Features use only trailing information at decision time. Chronological 60/20/20 split; 15-minute purge at TRAIN/VALIDATION boundaries.",
        f"Payout assumption {PAYOUT:.0%}: WIN +{PAYOUT:.2f}u, LOSS -1u, DRAW 0u. External BID proxy, not Pocket Option quotes.",
        "", "## Stage 1 — frozen event gate", "",
        f"TRAIN={len(train):,}; VALIDATION={len(val):,}; TEST={len(test):,}.",
        f"Validation 90th-percentile event threshold={event_cut:.6f}; TEST gated={len(test_gate):,}/{len(test):,} ({100*len(test_gate)/len(test):.2f}%).",
        f"TEST event rate all={100*event_y[test].mean():.2f}%; gated={100*event_y[test_gate].mean():.2f}%." if len(test_gate) else "No TEST rows passed event gate.",
        "", "## Stage 2 — conditional direction model", "",
        f"Direction model training: {len(train_dir):,} TRAIN rows with event label=1 and non-draw 10m outcome.",
        f"Validation event-gated rows={len(val_gate):,}; confidence threshold (validation 75th percentile)={confidence_cut:.6f}.",
        f"TEST direction AUC on event-gated rows={direction_auc:.4f}; Brier={direction_brier:.4f}.",
        "", "## TEST outcomes at 10 minutes", "",
        "| Method | n | W/L/D | Decisive WR | Net @92% |",
        "|---|---:|---:|---:|---:|",
        f"| Momentum on all event-gated rows | {mom_stats[0]} | {mom_stats[1]}/{mom_stats[2]}/{mom_stats[3]} | {mom_stats[4]:.2f}% | {mom_stats[5]:+.2f}u |",
        f"| Contrarian on all event-gated rows | {contra_stats[0]} | {contra_stats[1]}/{contra_stats[2]}/{contra_stats[3]} | {contra_stats[4]:.2f}% | {contra_stats[5]:+.2f}u |",
        f"| ML direction + frozen confidence filter | {ml_stats[0]} | {ml_stats[1]}/{ml_stats[2]}/{ml_stats[3]} | {ml_stats[4]:.2f}% | {ml_stats[5]:+.2f}u |",
        "", "## Interpretation guardrails", "",
        "- Event and direction models are trained only on TRAIN. Both thresholds are selected only on VALIDATION and frozen before TEST.",
        "- The direction model is trained only on TRAIN event-positive samples; it does not receive future event labels at inference.",
        "- Direction metrics are conditional on the frozen event probability gate; they do not establish that a binary-options strategy is profitable.",
        "- Test event-gated 10m outcomes are serially dependent; the ML confidence filter reduces sample size and is not a pristine prospective holdout.",
        "- Dukascopy BID is not Pocket Option's quote stream; no spread, platform latency, or variable payout is modeled. No application integration or live trade.",
    ]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {a.out}; test_gate={len(test_gate)}; confident_test={len(confident_test)}")


if __name__ == "__main__":
    main()
