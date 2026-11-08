#!/usr/bin/env python3
"""Causal M1 volatility-occurrence gate and conditional-direction audit.

The experiment asks two separate questions:
1) Can trailing M1 information identify periods likely to make a >=5-pip
   excursion during the next five minutes?
2) Once such periods are gated, does the recent direction predict CALL/PUT
   outcomes at 5/10/15-minute horizons?

No feature uses future data. Samples are spaced five minutes apart so the
primary five-minute target windows do not overlap within a continuous segment.
The gate is trained on TRAIN, its probability threshold is frozen from
VALIDATION, and TEST is evaluated once. Dukascopy BID is not Pocket Option.
"""
from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

PAYOUT = 0.92
PIP = 0.0001
MOVE_PIPS = 5.0
SAMPLE_STEP = 5
FEATURE_NAMES = [
    "absret_1", "absret_sum_5", "absret_sum_15", "absret_sum_30",
    "absret_sum_60", "range_5", "range_15", "range_30", "range_60",
    "vol_ratio_5_30", "vol_ratio_15_60", "momentum_5", "momentum_15",
    "momentum_30", "efficiency_15", "body_fraction", "close_location",
]


@dataclass
class Bar:
    ts: datetime
    open: float
    high: float
    low: float
    close: float


def read_bars(path: Path) -> list[Bar]:
    by_ts: dict[datetime, Bar] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"timestamp", "open", "high", "low", "close"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Unexpected CSV columns: {reader.fieldnames}")
        for row in reader:
            try:
                ts = datetime.fromtimestamp(int(float(row["timestamp"])) / 1000, tz=timezone.utc)
                o, h, l, c = (float(row[k]) for k in ("open", "high", "low", "close"))
            except (ValueError, TypeError, OverflowError):
                continue
            if not all(math.isfinite(x) and x > 0 for x in (o, h, l, c)):
                continue
            if h < max(o, l, c) or l > min(o, c):
                continue
            by_ts[ts] = Bar(ts, o, h, l, c)
    return [by_ts[t] for t in sorted(by_ts)]


def split_segments(bars: list[Bar]) -> list[list[Bar]]:
    out: list[list[Bar]] = []
    current: list[Bar] = []
    for bar in bars:
        if current and bar.ts - current[-1].ts != timedelta(minutes=1):
            if len(current) >= 70:
                out.append(current)
            current = []
        current.append(bar)
    if len(current) >= 70:
        out.append(current)
    return out


def safe_ratio(a: float, b: float) -> float:
    return a / b if b > 1e-12 else 0.0


def features_for(closes, highs, lows, opens, absrets, prefix, i: int) -> np.ndarray:
    def sum_abs(n: int) -> float:
        return float(prefix[i] - prefix[i-n]) if i >= n else float("nan")
    def span(n: int) -> float:
        return float((highs[i-n+1:i+1].max() - lows[i-n+1:i+1].min()) / closes[i]) if i + 1 >= n else float("nan")
    r1 = float(absrets[i-1])
    r5, r15, r30, r60 = (sum_abs(n) for n in (5, 15, 30, 60))
    s5, s15, s30, s60 = (span(n) for n in (5, 15, 30, 60))
    mom5 = closes[i] / closes[i-5] - 1
    mom15 = closes[i] / closes[i-15] - 1
    mom30 = closes[i] / closes[i-30] - 1
    path15 = sum_abs(15)
    eff15 = safe_ratio(abs(mom15), path15)
    candle_range = highs[i] - lows[i]
    body_fraction = safe_ratio(abs(closes[i] - opens[i]), candle_range)
    close_location = safe_ratio(closes[i] - lows[i], candle_range)
    return np.asarray([
        r1, r5, r15, r30, r60, s5, s15, s30, s60,
        safe_ratio(r5, r30), safe_ratio(r15, r60),
        mom5, mom15, mom30, eff15, body_fraction, close_location,
    ], dtype=float)


def build_samples(segments: list[list[Bar]], threshold_pips: float):
    xs, ys, records = [], [], []
    threshold = threshold_pips * PIP
    for seg_id, seg in enumerate(segments):
        closes = np.asarray([b.close for b in seg], dtype=float)
        highs = np.asarray([b.high for b in seg], dtype=float)
        lows = np.asarray([b.low for b in seg], dtype=float)
        opens = np.asarray([b.open for b in seg], dtype=float)
        absrets = np.abs(np.diff(np.log(closes)))
        prefix = np.concatenate(([0.0], np.cumsum(absrets)))
        # i is the last fully closed candle known at decision time.
        for i in range(60, len(seg) - 15, SAMPLE_STEP):
            entry = seg[i+1].open
            future = seg[i+1:i+6]
            up = max(b.high for b in future) - entry
            down = entry - min(b.low for b in future)
            event = int(max(up, down) >= threshold)
            x = features_for(closes, highs, lows, opens, absrets, prefix, i)
            if not np.isfinite(x).all():
                continue
            # Directional returns settle at the close after 5/10/15 full M1 bars.
            outcomes = {}
            for h in (5, 10, 15):
                delta = seg[i+h].close - entry
                outcomes[h] = 0 if abs(delta) < 1e-12 else (1 if delta > 0 else -1)
            mom_sign = 1 if seg[i].close >= seg[i-5].close else -1
            xs.append(x)
            ys.append(event)
            records.append({
                "time": seg[i].ts,
                "segment": seg_id,
                "event": event,
                "momentum_sign": mom_sign,
                "outcomes": outcomes,
            })
    if not xs:
        raise RuntimeError("No eligible samples were generated")
    return np.vstack(xs), np.asarray(ys, dtype=int), records


def payout_stats(rows, side_key, horizon):
    w = l = d = 0
    for row in rows:
        outcome = row["outcomes"][horizon]
        side = row[side_key]
        score = outcome * side
        if score > 0:
            w += 1
        elif score < 0:
            l += 1
        else:
            d += 1
    decisive = w + l
    wr = 100.0 * w / decisive if decisive else float("nan")
    net = w * PAYOUT - l
    return len(rows), w, l, d, wr, net


def fmt_stats(s):
    n, w, l, d, wr, net = s
    return f"{n} | {w}/{l}/{d} | {wr:.2f}% | {net:+.2f}u"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("M1_MOVE_OCCURRENCE_DIRECTION_AUDIT.md"))
    ap.add_argument("--move-pips", type=float, default=MOVE_PIPS)
    a = ap.parse_args()

    bars = read_bars(a.data)
    segments = split_segments(bars)
    X, y, records = build_samples(segments, a.move_pips)
    order = np.argsort(np.asarray([r["time"].timestamp() for r in records]))
    X, y = X[order], y[order]
    records = [records[k] for k in order]
    n = len(records)
    i1, i2 = int(n * 0.60), int(n * 0.80)
    # Purge samples whose 15-minute outcome would cross a split boundary.
    t1, t2 = records[i1]["time"], records[i2]["time"]
    train_idx = [i for i, r in enumerate(records[:i1]) if r["time"] + timedelta(minutes=15) < t1]
    val_idx = [i for i, r in enumerate(records[i1:i2], start=i1) if r["time"] + timedelta(minutes=15) < t2]
    test_idx = list(range(i2, n))
    if len(train_idx) < 1000 or len(val_idx) < 300 or len(test_idx) < 300:
        raise RuntimeError(f"Insufficient split sizes: train={len(train_idx)}, validation={len(val_idx)}, test={len(test_idx)}")

    model = make_pipeline(
        SimpleImputer(strategy="median"),
        StandardScaler(),
        LogisticRegression(C=0.1, max_iter=1000, solver="lbfgs", random_state=17),
    )
    model.fit(X[train_idx], y[train_idx])
    p_val = model.predict_proba(X[val_idx])[:, 1]
    threshold = float(np.quantile(p_val, 0.90))
    p_test = model.predict_proba(X[test_idx])[:, 1]
    y_test = y[test_idx]
    pred_test = p_test >= threshold

    def auc(y_true, probs):
        return roc_auc_score(y_true, probs) if len(set(y_true.tolist())) == 2 else float("nan")
    base = float(y_test.mean())
    gated_rate = float(y_test[pred_test].mean()) if pred_test.any() else float("nan")
    top_rows = [records[idx] for idx, keep in zip(test_idx, pred_test) if keep]
    all_rows = [records[idx] for idx in test_idx]

    lines = [
        "# HYDRA — M1 move-occurrence and conditional-direction audit", "",
        f"Source: Dukascopy EURUSD M1 BID; raw rows={len(bars):,}; continuous segments={len(segments):,}; eligible samples={n:,}.",
        f"Sampling: one decision every {SAMPLE_STEP} M1 bars; trailing 60-bar features; next {SAMPLE_STEP} bars define a >= {a.move_pips:g}-pip excursion label.",
        "Features: trailing absolute returns/ranges, volatility ratios, normalized momentum, path efficiency and last-candle shape. No time-of-day features.",
        "Split: chronological 60/20/20; model fitted on TRAIN only; probability gate is 90th percentile of VALIDATION probabilities, frozen for TEST.",
        "Purge: TRAIN and VALIDATION samples whose longest 15m outcome crosses the next split boundary are excluded.",
        f"Outcome accounting: entry next M1 open; close-to-close directional outcome at 5/10/15m; WIN +{PAYOUT:.2f}u, LOSS -1u, DRAW 0u.",
        "External Dukascopy BID proxy, not Pocket Option quotes; no spread, quote latency or variable platform payout model. Exploratory only.", "",
        "## Occurrence prediction", "",
        "| Period | n | Event rate | AUC | Brier |", "|---|---:|---:|---:|---:|",
    ]
    for name, idx in (("TRAIN", train_idx), ("VALIDATION", val_idx), ("TEST", test_idx)):
        probs = model.predict_proba(X[idx])[:, 1]
        rate = float(y[idx].mean())
        lines.append(f"| {name} | {len(idx):,} | {rate*100:.2f}% | {auc(y[idx], probs):.4f} | {brier_score_loss(y[idx], probs):.4f} |")
    lines += [
        "", "## Frozen validation gate on TEST", "",
        f"Validation 90th-percentile probability threshold: {threshold:.6f}.",
        f"TEST selected: {int(pred_test.sum()):,}/{len(test_idx):,} ({pred_test.mean()*100:.2f}%).",
        f"TEST base excursion rate: {base*100:.2f}%; gated excursion rate: {gated_rate*100:.2f}%; lift: {gated_rate/base:.2f}x." if base > 0 else "TEST base excursion rate is zero; lift undefined.",
        "", "## Direction after the gate", "",
        "Direction rules are frozen and deliberately simple: MOMENTUM follows the sign of the prior 5m return; CONTRARIAN takes the opposite side.",
        "| Gate | Rule | Horizon | n | W/L/D | Decisive WR | Net at 92% |",
        "|---|---|---:|---:|---|---:|---:|",
    ]
    for gate_name, rows in (("ALL TEST", all_rows), ("FROZEN TOP-PROBABILITY GATE", top_rows)):
        for rule, key in (("MOMENTUM", "momentum_sign"), ("CONTRARIAN", "contrarian_sign")):
            for row in rows:
                row["contrarian_sign"] = -row["momentum_sign"]
            for h in (5, 10, 15):
                s = payout_stats(rows, key, h)
                lines.append(f"| {gate_name} | {rule} | {h}m | {s[0]} | {s[1]}/{s[2]}/{s[3]} | {s[4]:.2f}% | {s[5]:+.2f}u |")
    lines += [
        "", "## Interpretation guardrails", "",
        "- AUC measures ranking of future range events, not CALL/PUT accuracy or profitability.",
        "- A high occurrence rate does not imply a directional edge; momentum and contrarian outcomes are reported separately.",
        "- Samples are spaced five minutes apart, but 10m/15m outcome windows overlap; their rows are descriptive, not independent.",
        "- The probability threshold is chosen on VALIDATION, never on TEST. The TEST period is still historically explored and is not a pristine prospective holdout.",
        "- Do not integrate a filter into HYDRA unless it beats simple baselines, survives a fresh untouched sample, and is checked against actual Pocket Option quotes and payout.",
    ]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {a.out}; samples={n}; train={len(train_idx)}; validation={len(val_idx)}; test={len(test_idx)}")


if __name__ == "__main__":
    main()
