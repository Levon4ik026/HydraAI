#!/usr/bin/env python3
"""Non-indicator price-action/context audit focused on distinguishing losses.

Every feature is computed only from the signal candle and candles before it.
The next M5 candle is used solely for the already-defined outcome label.
No thresholds are selected and no candidate filter is promoted.
"""
from __future__ import annotations

import argparse
import statistics
from pathlib import Path

try:
    from .win_loss_feature_audit import (
        SPLIT_DATE, load_m1, make_m5, parse_time, build_ledger,
        mann_whitney_p, cliff_delta, benjamini_hochberg,
    )
except ImportError:
    from win_loss_feature_audit import (
        SPLIT_DATE, load_m1, make_m5, parse_time, build_ledger,
        mann_whitney_p, cliff_delta, benjamini_hochberg,
    )

CONTEXT_FEATURES = (
    "efficiency_6", "efficiency_12", "path_flips_6",
    "range_overlap_3", "range_compression_3v12",
    "close_location", "position_in_prior_12_range",
    "distance_to_prior_high_atr", "distance_to_prior_low_atr",
    "body_direction_agreement_3", "median_range_to_true_range_6",
    "same_color_run",
)


def context_rows(bars):
    """Return causal context features aligned to bars; unavailable warmups are None."""
    rows = []
    ranges = [b.high - b.low for b in bars]
    true_ranges = []
    for i, b in enumerate(bars):
        tr = ranges[i] if i == 0 else max(
            ranges[i], abs(b.high - bars[i-1].close),
            abs(b.low - bars[i-1].close))
        true_ranges.append(tr)

    for i, b in enumerate(bars):
        out = {name: None for name in CONTEXT_FEATURES}
        span = ranges[i]
        if span > 0:
            out["close_location"] = (b.close - b.low) / span
        if i >= 6:
            diffs = [bars[j].close - bars[j-1].close for j in range(i-5, i+1)]
            path = sum(abs(x) for x in diffs)
            out["efficiency_6"] = abs(sum(diffs)) / path if path else 0.0
            signs = [1 if x > 0 else -1 if x < 0 else 0 for x in diffs]
            out["path_flips_6"] = sum(
                signs[k] != 0 and signs[k-1] != 0 and signs[k] != signs[k-1]
                for k in range(1, len(signs)))
            base = statistics.median(true_ranges[i-5:i+1])
            out["median_range_to_true_range_6"] = (
                statistics.median(ranges[i-5:i+1]) / base if base > 0 else None)
        if i >= 12:
            diffs = [bars[j].close - bars[j-1].close for j in range(i-11, i+1)]
            path = sum(abs(x) for x in diffs)
            out["efficiency_12"] = abs(sum(diffs)) / path if path else 0.0
            recent = bars[i-2:i+1]
            prior = bars[i-11:i-2]
            overlaps = []
            for left, right in zip(recent[1:], recent[:-1]):
                denom = min(left.high-left.low, right.high-right.low)
                if denom > 0:
                    overlaps.append(max(0.0, min(left.high, right.high) -
                                         max(left.low, right.low)) / denom)
            out["range_overlap_3"] = statistics.mean(overlaps) if overlaps else None
            prior_ranges = [x.high-x.low for x in prior]
            recent_ranges = [x.high-x.low for x in recent]
            prior_mean = statistics.mean(prior_ranges) if prior_ranges else 0.0
            out["range_compression_3v12"] = (
                statistics.mean(recent_ranges) / prior_mean if prior_mean > 0 else None)
            lo = min(x.low for x in bars[i-12:i])
            hi = max(x.high for x in bars[i-12:i])
            width = hi - lo
            if width > 0:
                out["position_in_prior_12_range"] = (b.close-lo)/width
            atr = statistics.mean(true_ranges[i-13:i+1]) if i >= 13 else None
            if atr and atr > 0:
                out["distance_to_prior_high_atr"] = (hi-b.close)/atr
                out["distance_to_prior_low_atr"] = (b.close-lo)/atr
            signs = [1 if bars[j].close > bars[j-1].close else
                     -1 if bars[j].close < bars[j-1].close else 0
                     for j in range(i-2, i+1)]
            out["body_direction_agreement_3"] = sum(signs)/3.0
        if i >= 1:
            sign = 1 if b.close > bars[i-1].close else -1 if b.close < bars[i-1].close else 0
            run = 0
            for j in range(i, max(0, i-6), -1):
                sj = 1 if bars[j].close > bars[j-1].close else -1 if bars[j].close < bars[j-1].close else 0
                if sj == 0 or sj != sign:
                    break
                run += 1
            out["same_color_run"] = float(run)
        rows.append(out)
    return rows


def analyse(ledger, features, direction, period):
    chosen = [r for r in ledger if r["direction"] == direction and r["period"] == period]
    wins = [r for r in chosen if r["outcome"] == "WIN"]
    losses = [r for r in chosen if r["outcome"] == "LOSS"]
    lines = [f"## {direction} / {period}: W={len(wins)} L={len(losses)} D={sum(r['outcome']=='DRAW' for r in chosen)}",
             "| Context (not standard indicator) | Winners median | Losers median | Cliff delta (W vs L) | MW p | BH q |",
             "|---|---:|---:|---:|---:|---:|"]
    tests, values = [], {}
    for name in CONTEXT_FEATURES:
        w = [features[r["signal_time"]][name] for r in wins if features[r["signal_time"]][name] is not None]
        l = [features[r["signal_time"]][name] for r in losses if features[r["signal_time"]][name] is not None]
        p = mann_whitney_p(w, l)
        tests.append((name, p))
        values[name] = (w, l, p)
    q = benjamini_hochberg(tests)
    for name in CONTEXT_FEATURES:
        w, l, p = values[name]
        wm = statistics.median(w) if w else float("nan")
        lm = statistics.median(l) if l else float("nan")
        d = cliff_delta(w, l)
        lines.append(f"| {name} | {wm:.5g} | {lm:.5g} | {d if d is not None else float('nan'):.3f} | {p if p is not None else float('nan'):.4g} | {q[name] if q[name] is not None else float('nan'):.4g} |")
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path("eurusd_history_extended.csv"))
    ap.add_argument("--split-date", default=SPLIT_DATE)
    ap.add_argument("--adx-min", type=float, default=15.0)
    ap.add_argument("--out", type=Path, default=Path("research/LOSS_CONTEXT_AUDIT.md"))
    args = ap.parse_args()
    m1 = load_m1(args.data)
    segments = make_m5(m1)
    split = parse_time(args.split_date)
    ledger = build_ledger(segments, split, args.adx_min)
    feature_map = {}
    for segment in segments:
        rows = context_rows(segment)
        for bar, row in zip(segment, rows):
            feature_map[bar.timestamp.isoformat()] = row
    lines = [
        "# Loss-context audit: causal price action beyond standard indicators", "",
        f"Data: {args.data}; M1 rows={len(m1)}; complete M5 bars={sum(map(len, segments))}; segments={len(segments)}.",
        f"Frozen trigger: BB/Williams re-entry with ADX >= {args.adx_min:g}; settlement next M5 candle; payout 92%.",
        f"Events={len(ledger)}. Chronological split={args.split_date}.",
        "Features describe OHLC path structure and local context, not conventional indicator values.",
        "All context features use only candles at or before signal close. Settlement candle supplies outcome only.",
        "Mann-Whitney tests are exploratory; BH correction is applied across the 12 features within each direction/period.",
        "No thresholds, filters, or strategy parameters are selected. Holdout was already inspected in earlier work and is not independent confirmation.",
        "",
    ]
    for direction in ("CALL", "PUT"):
        for period in ("TRAIN", "HOLDOUT"):
            lines.extend(analyse(ledger, feature_map, direction, period))
            lines.append("")
    lines += [
        "## Interpretation rules", "",
        "- A large winner/loser difference is a hypothesis, not a trading rule.",
        "- Prioritize features with consistent effect direction in train and holdout, adequate counts, and meaningful BH-adjusted evidence.",
        "- A feature that only separates losses in one small cohort is not a robust loss signature.",
        "- Do not tune thresholds on this historical holdout. Any hypothesis must be frozen and tested prospectively on new continuous non-OTC data.",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines)+"\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
