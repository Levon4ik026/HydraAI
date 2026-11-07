"""Causal market-stress diagnostics for research-only strategy evaluation."""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime
import math
import statistics
from typing import Iterable, Sequence
from research.backtest_engine import Candle, Trade, summarize_trades, validate_candles

REGIME_NORMAL = "NORMAL"
REGIME_ELEVATED = "ELEVATED"
REGIME_EXTREME = "EXTREME"
REGIME_UNAVAILABLE = "UNAVAILABLE"

def true_ranges(candles: Sequence[Candle], interval_seconds: int = 60) -> list[float]:
    """True range resets after a timestamp gap; never bridges missing candles."""
    validate_candles(candles, interval_seconds)
    values = []
    for i, candle in enumerate(candles):
        contiguous = (i > 0 and
            (candle.timestamp - candles[i-1].timestamp).total_seconds() == interval_seconds)
        if not contiguous:
            values.append(candle.high - candle.low)
        else:
            pc = candles[i-1].close
            values.append(max(candle.high-candle.low, abs(candle.high-pc), abs(candle.low-pc)))
    return values

def classify_volatility_regimes(candles: Sequence[Candle], lookback: int = 20,
                                elevated_ratio: float = 1.5, extreme_ratio: float = 2.5,
                                interval_seconds: int = 60) -> list[dict]:
    """Use current true range against median true range of prior contiguous candles only."""
    validate_candles(candles, interval_seconds)
    if lookback < 2:
        raise ValueError("lookback must be at least 2")
    if not (math.isfinite(elevated_ratio) and math.isfinite(extreme_ratio)):
        raise ValueError("thresholds must be finite")
    if elevated_ratio <= 0 or extreme_ratio <= elevated_ratio:
        raise ValueError("require 0 < elevated_ratio < extreme_ratio")
    tr = true_ranges(candles, interval_seconds)
    rows, segment_start = [], 0
    for i, candle in enumerate(candles):
        if i and (candle.timestamp-candles[i-1].timestamp).total_seconds() != interval_seconds:
            segment_start = i
        if i-segment_start < lookback:
            rows.append({"timestamp": candle.timestamp, "regime": REGIME_UNAVAILABLE,
                         "true_range": tr[i], "baseline_median_tr": None,
                         "range_ratio": None, "body_to_baseline": None})
            continue
        baseline = statistics.median(tr[i-lookback:i])
        ratio = tr[i] / baseline if baseline > 0 else (math.inf if tr[i] > 0 else 1.0)
        body = abs(candle.close-candle.open) / baseline if baseline > 0 else None
        regime = REGIME_EXTREME if ratio >= extreme_ratio else REGIME_ELEVATED if ratio >= elevated_ratio else REGIME_NORMAL
        rows.append({"timestamp": candle.timestamp, "regime": regime, "true_range": tr[i],
                     "baseline_median_tr": baseline, "range_ratio": ratio, "body_to_baseline": body})
    return rows

def summarize_by_signal_regime(trades: Iterable[Trade], regime_rows: Sequence[dict]) -> dict[str, dict]:
    by_time = {row["timestamp"]: row["regime"] for row in regime_rows}
    buckets, missing = defaultdict(list), 0
    for trade in trades:
        regime = by_time.get(trade.signal_time)
        if regime is None or regime == REGIME_UNAVAILABLE:
            missing += 1
        else:
            buckets[regime].append(trade)
    result = {name: summarize_trades(buckets.get(name, []))
              for name in (REGIME_NORMAL, REGIME_ELEVATED, REGIME_EXTREME)}
    result["excluded_unavailable_or_unmatched"] = {"trades": missing}
    return result

def summarize_event_window(trades: Iterable[Trade], start: datetime, end: datetime) -> dict:
    if start.tzinfo is None or end.tzinfo is None or start >= end:
        raise ValueError("event window must be timezone-aware and start < end")
    return summarize_trades([t for t in trades if start <= t.signal_time < end and t.settlement_time <= end])

def shock_candles(regime_rows: Sequence[dict], minimum_body_ratio: float = 2.0) -> list[dict]:
    if not math.isfinite(minimum_body_ratio) or minimum_body_ratio <= 0:
        raise ValueError("minimum_body_ratio must be finite and positive")
    return [r for r in regime_rows if r["regime"] == REGIME_EXTREME
            and r["body_to_baseline"] is not None and r["body_to_baseline"] >= minimum_body_ratio]

def next_candle_baseline_by_regime(candles: Sequence[Candle], regime_rows: Sequence[dict],
                                   interval_seconds: int = 60) -> dict[str, dict]:
    """Descriptive all-bar CALL/PUT baseline conditioned on signal-time regime.

    Each candle is an observation only if the immediately following candle is
    contiguous. This baseline is intentionally overlapping and is not a
    tradable strategy result.
    """
    validate_candles(candles, interval_seconds)
    if len(candles) != len(regime_rows):
        raise ValueError("regime_rows must align one-to-one with candles")
    buckets = {name: {"up": 0, "down": 0, "draw": 0}
               for name in (REGIME_NORMAL, REGIME_ELEVATED, REGIME_EXTREME)}
    for i in range(len(candles) - 1):
        current, following = candles[i], candles[i + 1]
        if (following.timestamp-current.timestamp).total_seconds() != interval_seconds:
            continue
        regime = regime_rows[i]["regime"]
        if regime not in buckets:
            continue
        delta = following.close-following.open
        if abs(delta) <= 1e-12:
            buckets[regime]["draw"] += 1
        elif delta > 0:
            buckets[regime]["up"] += 1
        else:
            buckets[regime]["down"] += 1
    result = {}
    for regime, counts in buckets.items():
        decisive = counts["up"] + counts["down"]
        result[regime] = {
            **counts,
            "decisive": decisive,
            "call_win_rate": counts["up"] / decisive if decisive else None,
            "put_win_rate": counts["down"] / decisive if decisive else None,
        }
    return result
