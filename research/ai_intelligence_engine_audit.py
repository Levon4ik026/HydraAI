#!/usr/bin/env python3
"""Research-only chronological ML filter audit for Hydra's frozen M5 strategy.

The frozen signal generator and 20-minute settlement are imported unchanged.
Only signal-time and trailing features are predictors. Models train on TRAIN,
thresholds are selected on VALIDATION, and TEST is evaluated once afterward.
"""
from __future__ import annotations

import argparse
import math
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from long_history_validation import read_duka, make_events, PAYOUT
from reproduce_m5_bb_williams_adx import indicators, make_m5

HORIZON_BARS = 4
MIN_VALIDATION_TRADES = 40
THRESHOLDS = tuple(round(x, 2) for x in np.arange(0.50, 0.751, 0.025))


def feature_row(bars, ind, i, direction, ema20, ema50, atr, atr_history):
    cur = bars[i]
    av = atr[i]
    if av is None or av <= 0:
        return None
    prev = bars[i - 1]
    span = max(cur.high - cur.low, 1e-12)
    body = cur.close - cur.open
    upper_wick = cur.high - max(cur.open, cur.close)
    lower_wick = min(cur.open, cur.close) - cur.low
    x = ind[i]
    if any(x.get(k) is None for k in ("upper", "lower", "willr", "adx", "plus_di", "minus_di")):
        return None
    history = [v for v in atr_history[max(0, i - 120):i] if v is not None]
    current_atr_pct = av / cur.close
    vol_rank = sum(v <= current_atr_pct for v in history) / len(history) if len(history) >= 60 else 0.5
    e20, e50 = ema20[i], ema50[i]
    if e20 is None or e50 is None:
        return None
    # Everything below is known at the signal candle close or earlier.
    values = [
        1.0 if direction == "CALL" else 0.0,
        x["adx"], x["plus_di"] - x["minus_di"], x["willr"],
        (e20 - e50) / av,
        (cur.close - e20) / av, (cur.close - e50) / av,
        (cur.close - cur.open) / av, span / av,
        upper_wick / span, lower_wick / span,
        (x["upper"] - x["lower"]) / av,
        (cur.close - x["lower"]) / av, (x["upper"] - cur.close) / av,
        (cur.close - prev.close) / av,
        (cur.close - bars[i - 3].close) / av,
        (cur.close - bars[i - 6].close) / av,
        vol_rank,
        math.sin(2 * math.pi * cur.timestamp.hour / 24),
        math.cos(2 * math.pi * cur.timestamp.hour / 24),
        math.sin(2 * math.pi * cur.timestamp.weekday() / 7),
        math.cos(2 * math.pi * cur.timestamp.weekday() / 7),
    ]
    if not all(math.isfinite(v) for v in values):
        return None
    return values


def ema(values, period):
    out = [None] * len(values)
    if len(values) < period:
        return out
    state = sum(values[:period]) / period
    out[period - 1] = state
    alpha = 2.0 / (period + 1.0)
    for i in range(period, len(values)):
        state = values[i] * alpha + state * (1.0 - alpha)
        out[i] = state
    return out


def build_dataset(segments, adx_min):
    events = make_events(segments, adx_min)
    by_segment = defaultdict(list)
    for event in events:
        by_segment[event["segment"]].append(event)
    rows = []
    for seg_id, bars in enumerate(segments):
        if not by_segment[seg_id]:
            continue
        ind = indicators(bars)
        closes = [b.close for b in bars]
        e20, e50 = ema(closes, 20), ema(closes, 50)
        tr = [None] * len(bars)
        for i in range(1, len(bars)):
            b, p = bars[i], bars[i - 1]
            tr[i] = max(b.high - b.low, abs(b.high - p.close), abs(b.low - p.close))
        atr = [None] * len(bars)
        for i in range(14, len(bars)):
            vals = [v for v in tr[i - 13:i + 1] if v is not None]
            if len(vals) == 14:
                atr[i] = sum(vals) / 14.0
        atr_history = []
        for i, value in enumerate(atr):
            if value is None:
                atr_history.append(None)
            else:
                atr_history.append(value / bars[i].close if bars[i].close else None)
        # Use ATR/close history for a scale-free volatility percentile.
        for event in by_segment[seg_id]:
            i = event["bar_index"]
            if i < 50 or i + HORIZON_BARS >= len(bars):
                continue
            features = feature_row(bars, ind, i, event["direction"], e20, e50,
                                   atr, atr_history)
            if features is None:
                continue
            entry = bars[i + 1].open
            exit_price = bars[i + HORIZON_BARS].close
            delta = (exit_price - entry) * (1 if event["direction"] == "CALL" else -1)
            outcome = "DRAW" if abs(delta) < 1e-12 else "WIN" if delta > 0 else "LOSS"
            rows.append({"time": bars[i].timestamp, "direction": event["direction"],
                         "features": features, "outcome": outcome,
                         "settle_time": bars[i + HORIZON_BARS].timestamp})
    rows.sort(key=lambda r: r["time"])
    return rows, len(events)


def metrics(rows, keep=None):
    chosen = [r for j, r in enumerate(rows) if keep is None or keep[j]]
    w = sum(r["outcome"] == "WIN" for r in chosen)
    l = sum(r["outcome"] == "LOSS" for r in chosen)
    d = len(chosen) - w - l
    decisive = w + l
    wr = 100.0 * w / decisive if decisive else float("nan")
    net = w * PAYOUT - l
    gross_win, gross_loss = w * PAYOUT, l
    pf = gross_win / gross_loss if gross_loss else (float("inf") if gross_win else 0.0)
    equity = peak = max_dd = 0.0
    streak = max_streak = 0
    for r in chosen:
        equity += PAYOUT if r["outcome"] == "WIN" else -1.0 if r["outcome"] == "LOSS" else 0.0
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        streak = streak + 1 if r["outcome"] == "LOSS" else 0
        max_streak = max(max_streak, streak)
    all_wr = 100.0 * w / len(chosen) if chosen else float("nan")
    roi = 100.0 * net / len(chosen) if chosen else float("nan")
    return {"n": len(chosen), "w": w, "l": l, "d": d, "decisive": decisive,
            "wr": wr, "all_wr": all_wr, "net": net, "roi": roi,
            "pf": pf, "dd": max_dd, "streak": max_streak}


def split_rows(rows):
    days = sorted({r["time"].date() for r in rows})
    if len(days) < 30:
        raise SystemExit("Insufficient signal days for chronological ML split.")
    d1, d2 = days[int(len(days) * .60)], days[int(len(days) * .80)]
    train, validation, test = [], [], []
    # Purge any sample whose 20-minute outcome window touches the next split.
    for i, r in enumerate(rows):
        day = r["time"].date()
        if day < d1 and r["settle_time"].date() >= d1:
            continue
        if d1 <= day < d2 and r["settle_time"].date() >= d2:
            continue
        if day < d1:
            train.append(r)
        elif day < d2:
            validation.append(r)
        else:
            test.append(r)
    return train, validation, test, d1, d2


def choose_threshold(y_rows, probabilities):
    best = None
    for threshold in THRESHOLDS:
        keep = probabilities >= threshold
        result = metrics(y_rows, keep)
        coverage = result["n"] / max(1, len(y_rows))
        if result["n"] < MIN_VALIDATION_TRADES:
            continue
        # Select on validation net expectancy, with coverage as a tie-breaker.
        score = (result["net"], result["wr"], coverage)
        if best is None or score > best["score"]:
            best = {"threshold": threshold, "score": score,
                    "metrics": result, "coverage": coverage}
    return best


def model_factories():
    return {
        "logistic": lambda: make_pipeline(
            SimpleImputer(strategy="median"), StandardScaler(),
            LogisticRegression(C=0.25, class_weight="balanced", max_iter=2000,
                               random_state=2026)),
        "hist_gradient_boosting": lambda: make_pipeline(
            SimpleImputer(strategy="median"),
            HistGradientBoostingClassifier(max_iter=120, learning_rate=0.05,
                                           max_leaf_nodes=7, l2_regularization=2.0,
                                           min_samples_leaf=25, random_state=2026)),
        "random_forest": lambda: make_pipeline(
            SimpleImputer(strategy="median"),
            RandomForestClassifier(n_estimators=400, max_depth=4,
                                   min_samples_leaf=20, max_features=0.8,
                                   class_weight="balanced_subsample",
                                   random_state=2026, n_jobs=-1)),
    }


def wilson(w, n):
    if n == 0:
        return (float("nan"), float("nan"))
    z = 1.959963984540054
    p = w / n
    den = 1 + z*z/n
    center = (p + z*z/(2*n)) / den
    radius = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / den
    return 100*(center-radius), 100*(center+radius)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("research/AI_INTELLIGENCE_ENGINE_AUDIT.md"))
    ap.add_argument("--adx-min", type=float, default=15)
    args = ap.parse_args()

    m1 = read_duka(args.data)
    segments = make_m5(m1)
    rows, trigger_count = build_dataset(segments, args.adx_min)
    train, validation, test, d1, d2 = split_rows(rows)
    if min(len(train), len(validation), len(test)) < 80:
        raise SystemExit(f"Too few samples after purge: train={len(train)}, validation={len(validation)}, test={len(test)}")

    feature_names = ["direction_call", "adx", "di_spread", "willr", "ema_spread_atr",
      "close_ema20_atr", "close_ema50_atr", "body_atr", "range_atr", "upper_wick_ratio",
      "lower_wick_ratio", "bb_width_atr", "close_lower_band_atr", "upper_band_close_atr",
      "momentum1_atr", "momentum3_atr", "momentum6_atr", "atr_percentile",
      "hour_sin", "hour_cos", "weekday_sin", "weekday_cos"]
    X_train = np.asarray([r["features"] for r in train], dtype=float)
    X_val = np.asarray([r["features"] for r in validation], dtype=float)
    X_test = np.asarray([r["features"] for r in test], dtype=float)
    y_train = np.asarray([1 if r["outcome"] == "WIN" else 0 for r in train if r["outcome"] != "DRAW"])
    train_decisive = [r for r in train if r["outcome"] != "DRAW"]
    # Exclude draws from model fitting and keep scoring on the original event set.
    X_train = np.asarray([r["features"] for r in train_decisive], dtype=float)
    y_train = np.asarray([1 if r["outcome"] == "WIN" else 0 for r in train_decisive])
    if len(set(y_train.tolist())) < 2:
        raise SystemExit("Training labels contain only one class.")

    total_m5 = sum(map(len, segments))
    raw_signal_pct = 100.0 * trigger_count / max(1, total_m5)
    lines = ["# HYDRA — AI Intelligence Engine chronological audit", "",
      f"Source: Dukascopy EURUSD M1 BID; raw rows={len(m1):,}; complete M5 bars={total_m5:,}; continuous segments={len(segments)}.",
      f"Coverage: {m1[0].timestamp.isoformat()} — {m1[-1].timestamp.isoformat()}.",
      f"Raw frozen-trigger events={trigger_count:,}; raw trigger frequency={raw_signal_pct:.3f}% of complete M5 bars; raw WAIT share={100-raw_signal_pct:.3f}%.",
      f"Eligible feature/outcome rows={len(rows):,}; {trigger_count-len(rows):,} raw events excluded by 50-bar warmup, feature availability, or complete 20-minute path requirements.",
      f"Chronological split: TRAIN < {d1}; VALIDATION {d1} through {d2 - timedelta(days=1)}; TEST >= {d2}.",
      f"After 20-minute boundary purge: TRAIN={len(train)}, VALIDATION={len(validation)}, TEST={len(test)}.",
      "Frozen trigger unchanged: BB(20,2) re-entry + Williams %R(14) cross + ADX(14)>=15. Signal on closed M5; entry next M5 open; settlement at fourth M5 close; payout WIN +0.92u / LOSS -1u / DRAW 0u.",
      "Models receive only signal-close/trailing features. Draws are excluded from fitting and decisive WR denominator; draws remain in scored trade counts. Thresholds are selected on VALIDATION and frozen before TEST.",
      "External Dukascopy BID feed, not Pocket Option's exact quote stream; no spread/platform execution model. Research-only; no live integration.", "",
      "## Baseline before AI filtering", "",
      "| Split | Direction | n | W/L/D | Decisive WR | Wilson 95% CI | Wins / all | Net | ROI | PF | Max DD | Max loss streak |",
      "|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for label, subset in (("TRAIN", train), ("VALIDATION", validation), ("TEST", test)):
        for side in ("ALL", "CALL", "PUT"):
            side_rows = subset if side == "ALL" else [r for r in subset if r["direction"] == side]
            m = metrics(side_rows)
            ci = wilson(m["w"], m["decisive"])
            ci_txt = f"[{ci[0]:.2f}, {ci[1]:.2f}]" if m["decisive"] else "n/a"
            pf_txt = "inf" if math.isinf(m["pf"]) else f"{m['pf']:.3f}"
            lines.append(f"| {label} | {side} | {m['n']} | {m['w']}/{m['l']}/{m['d']} | {m['wr']:.2f}% | {ci_txt} | {m['all_wr']:.2f}% | {m['net']:+.2f}u | {m['roi']:+.2f}% | {pf_txt} | {m['dd']:.2f}u | {m['streak']} |")

    lines += ["", "## Model comparison", "",
      "Each model is fitted only on TRAIN decisive outcomes. Its threshold is selected only on VALIDATION from the fixed grid 0.50–0.75, requiring at least 40 accepted validation trades. The selected threshold is then frozen for TEST. Rejected model signals are WAIT.",
      "| Model | Threshold | VAL accepted | VAL W/L/D | VAL WR | VAL net | TEST accepted | TEST W/L/D | TEST WR | TEST Wilson 95% CI | TEST net | TEST ROI | TEST PF | TEST maxDD | TEST max loss streak |",
      "|---|---:|---:|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|",
      "", "## Direction and WAIT-filter diagnostics", "",
      "| Model | Split | Direction | Accepted / base signals | WAIT count (%) | W/L/D | Decisive WR | Wilson 95% CI | Wins / all | Net | ROI | PF | Max DD | Max loss streak |",
      "|---|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name, factory in model_factories().items():
        model = factory()
        model.fit(X_train, y_train)
        p_val = model.predict_proba(X_val)[:, 1]
        selected = choose_threshold(validation, p_val)
        if selected is None:
            lines.append(f"| {name} | — | — | no threshold met minimum validation sample | — | — | — | — | — | — | — | — | — | — |")
            continue
        p_test = model.predict_proba(X_test)[:, 1]
        val_keep = p_val >= selected["threshold"]
        test_keep = p_test >= selected["threshold"]
        vm = metrics(validation, val_keep)
        tm = metrics(test, test_keep)
        tci = wilson(tm["w"], tm["decisive"])
        tci_txt = f"[{tci[0]:.2f}, {tci[1]:.2f}]" if tm["decisive"] else "n/a"
        pf_txt = "inf" if math.isinf(tm["pf"]) else f"{tm['pf']:.3f}"
        lines.append(f"| {name} | {selected['threshold']:.3f} | {vm['n']}/{len(validation)} | {vm['w']}/{vm['l']}/{vm['d']} | {vm['wr']:.2f}% | {vm['net']:+.2f}u | {tm['n']}/{len(test)} | {tm['w']}/{tm['l']}/{tm['d']} | {tm['wr']:.2f}% | {tci_txt} | {tm['net']:+.2f}u | {tm['roi']:+.2f}% | {pf_txt} | {tm['dd']:.2f}u | {tm['streak']} |")
        for split_name, subset_rows, keep in (("VALIDATION", validation, val_keep), ("TEST", test, test_keep)):
            for side in ("ALL", "CALL", "PUT"):
                indices = [i for i, r in enumerate(subset_rows) if side == "ALL" or r["direction"] == side]
                side_rows = [subset_rows[i] for i in indices]
                side_keep = [bool(keep[i]) for i in indices]
                sm = metrics(side_rows, side_keep)
                base_n = len(side_rows)
                rejected = base_n - sm["n"]
                wait_pct = 100.0 * rejected / base_n if base_n else float("nan")
                ci = wilson(sm["w"], sm["decisive"])
                ci_txt = f"[{ci[0]:.2f}, {ci[1]:.2f}]" if sm["decisive"] else "n/a"
                pf_side = "inf" if math.isinf(sm["pf"]) else f"{sm['pf']:.3f}"
                lines.append(f"| {name} | {split_name} | {side} | {sm['n']}/{base_n} | {rejected} ({wait_pct:.2f}%) | {sm['w']}/{sm['l']}/{sm['d']} | {sm['wr']:.2f}% | {ci_txt} | {sm['all_wr']:.2f}% | {sm['net']:+.2f}u | {sm['roi']:+.2f}% | {pf_side} | {sm['dd']:.2f}u | {sm['streak']} |")
    lines += ["", "## Interpretation guardrails", "",
      f"- 92% payout break-even decisive WR = {100/(1+PAYOUT):.4f}%. A higher WR alone is insufficient; compare net, ROI, drawdown, coverage, and confidence intervals.",
      "- The raw signal-frequency denominator is all complete M5 bars; raw WAIT includes bars without a trigger. In model tables, WAIT means a triggered event rejected by the model.",
      "- Wilson intervals describe decisive outcomes and assume independent Bernoulli trials; overlapping 20-minute outcomes and market clustering violate that assumption and can make intervals too narrow.",
      "- A filter may appear better by rejecting most trades. Always read accepted count and WAIT share alongside WR/net.",
      "- This historical TEST has already been used in repeated exploratory research. It is not an untouched independent confirmation.",
      "- Model/threshold selection across several candidates introduces selection bias. A genuinely prospective validation on fresh Pocket Option candles is required before any production use.",
      "- No model is deployed or connected to Hydra Desktop; no trade execution exists.", ""]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    report = "\n".join(lines)
    args.out.write_text(report + "\n", encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
