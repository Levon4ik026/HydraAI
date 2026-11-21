#!/usr/bin/env python3
"""Predeclared causal volatility/trend regime audit for frozen M5 signals.

Regimes are defined without using trade outcomes: volatility is ranked against
the preceding 120 completed M5 bars; ADX bands and EMA20/EMA50 bias are fixed.
This is a descriptive stratification, not a filter-selection procedure.
"""
from __future__ import annotations
import argparse
from pathlib import Path
try:
    from .win_loss_feature_audit import SPLIT_DATE, load_m1, make_m5, parse_time, build_ledger, feature_rows
except ImportError:
    from win_loss_feature_audit import SPLIT_DATE, load_m1, make_m5, parse_time, build_ledger, feature_rows

VOL_LOOKBACK = 120

def classify_regimes(bars, features):
    out = []
    for i, row in enumerate(features):
        atr = row["atr14_close"]
        adx = row["adx14"]
        ema = row["ema20_50_atr"]
        if i < VOL_LOOKBACK or atr is None:
            vol = None
        else:
            hist = [x["atr14_close"] for x in features[i-VOL_LOOKBACK:i]
                    if x["atr14_close"] is not None]
            if len(hist) < VOL_LOOKBACK:
                vol = None
            else:
                rank = sum(x <= atr for x in hist) / len(hist)
                vol = "LOW_VOL" if rank <= 1/3 else "MID_VOL" if rank <= 2/3 else "HIGH_VOL"
        strength = None if adx is None else (
            "WEAK_ADX" if adx < 20 else "MODERATE_ADX" if adx < 30 else "STRONG_ADX")
        bias = None if ema is None else (
            "UP_BIAS" if ema > 0 else "DOWN_BIAS" if ema < 0 else "FLAT_BIAS")
        out.append({"volatility": vol, "trend_strength": strength, "trend_bias": bias,
                    "regime": None if vol is None or strength is None else f"{vol}|{strength}"})
    return out

def summarize(rows):
    w = sum(x["outcome"] == "WIN" for x in rows)
    l = sum(x["outcome"] == "LOSS" for x in rows)
    d = sum(x["outcome"] == "DRAW" for x in rows)
    decisive = w + l
    net = .92*w - l
    roi = 100*net/len(rows) if rows else 0.0
    wr = f"{w/decisive:.1%}" if decisive else "—"
    return w,l,d,wr,net,roi

def build_report(ledger, states, split):
    lines = [
        "# Causal market-regime audit",
        "",
        f"Events={len(ledger)}; split={split}; payout=92%; next M5 candle settlement.",
        f"Volatility regime: current ATR14/close ranked against prior {VOL_LOOKBACK} completed M5 bars (tertiles).",
        "Trend strength: ADX <20 / 20–<30 / >=30. Trend bias: EMA20-EMA50 sign.",
        "All regime variables are known at signal close. No outcomes are used to define states.",
        "Exploratory descriptive stratification only; previously inspected holdout is not independent confirmation.",
        "Small cells are shown, not optimized. No filter is selected.",
        "",
    ]
    for direction in ("CALL", "PUT"):
        for period in ("TRAIN", "HOLDOUT"):
            chosen = [x for x in ledger if x["direction"] == direction and x["period"] == period]
            lines += [f"## {direction} / {period} (n={len(chosen)})", "",
                      "### Volatility × trend strength",
                      "| Regime | n | W/L/D | Decisive WR | Net u | ROI |",
                      "|---|---:|---:|---:|---:|---:|"]
            groups = {}
            for x in chosen:
                state = states[x["signal_time"]]["regime"]
                if state is not None:
                    groups.setdefault(state, []).append(x)
            for name in sorted(groups):
                group = groups[name]
                w,l,d,wr,net,roi = summarize(group)
                lines.append(f"| {name} | {len(group)} | {w}/{l}/{d} | {wr} | {net:+.2f} | {roi:+.1f}% |")
            lines += ["", "### Directional bias (EMA20−EMA50)", 
                      "| Bias | n | W/L/D | Decisive WR | Net u | ROI |",
                      "|---|---:|---:|---:|---:|---:|"]
            groups = {}
            for x in chosen:
                state = states[x["signal_time"]]["trend_bias"]
                if state is not None:
                    groups.setdefault(state, []).append(x)
            for name in sorted(groups):
                group = groups[name]
                w,l,d,wr,net,roi = summarize(group)
                lines.append(f"| {name} | {len(group)} | {w}/{l}/{d} | {wr} | {net:+.2f} | {roi:+.1f}% |")
            lines.append("")
    lines += [
        "## Interpretation",
        "",
        "- At 92% payout, break-even decisive WR is 52.08%; net units and ROI are also reported.",
        "- A cell with fewer than 10 decisive outcomes is highly unstable; do not use its WR as evidence.",
        "- Compare the same predeclared regime across train and holdout, keeping CALL and PUT separate.",
        "- Do not select or deploy a filter from this historical screen. Any hypothesis requires a frozen prospective test on new continuous non-OTC data.",
        "- These descriptive cells do not adjust uncertainty for serial dependence.",
    ]
    return "\n".join(lines) + "\n"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path("eurusd_history_extended.csv"))
    ap.add_argument("--split-date", default=SPLIT_DATE)
    ap.add_argument("--adx-min", type=float, default=15.0)
    ap.add_argument("--out", type=Path, default=Path("research/MARKET_REGIME_AUDIT.md"))
    args = ap.parse_args()
    m1 = load_m1(args.data)
    segments = make_m5(m1)
    ledger = build_ledger(segments, parse_time(args.split_date), args.adx_min)
    state_map = {}
    for segment in segments:
        feats = feature_rows(segment)
        states = classify_regimes(segment, feats)
        for bar, state in zip(segment, states):
            state_map[bar.timestamp.isoformat()] = state
    report = build_report(ledger, state_map, args.split_date)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(report)

if __name__ == "__main__":
    main()
