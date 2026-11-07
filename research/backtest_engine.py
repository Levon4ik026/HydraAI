"""Leakage-aware, research-only binary-option backtest primitives.

The engine does not create signals or place orders. Callers provide signal indices
computed from closed candles. Candle timestamps represent candle OPEN times.
A signal on candle N is evaluated after N closes; entry is candle N+1 open.
For an H-minute expiry, settlement is the close of candle N+H.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
import math
from typing import Iterable, Mapping, Sequence


PAYOUT_DEFAULT = 0.92
SUPPORTED_HORIZONS_MIN = (1, 2, 3, 5)


@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float

    def __post_init__(self) -> None:
        stamp = self.timestamp
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            raise ValueError("Candle timestamp must be timezone-aware")
        object.__setattr__(self, "timestamp", stamp.astimezone(timezone.utc))
        values = (self.open, self.high, self.low, self.close)
        if not all(math.isfinite(float(value)) for value in values):
            raise ValueError("OHLC values must be finite")
        if min(values) <= 0:
            raise ValueError("OHLC prices must be positive")
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high is below another OHLC component")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low is above another OHLC component")


@dataclass(frozen=True)
class Trade:
    signal_time: datetime
    entry_time: datetime
    settlement_time: datetime
    direction: str
    horizon_min: int
    entry_price: float
    exit_price: float
    outcome: str
    payout: float
    profit_units: float

    def to_dict(self) -> dict:
        return asdict(self)


def validate_candles(candles: Sequence[Candle], interval_seconds: int = 60) -> None:
    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be positive")
    previous = None
    for candle in candles:
        if not isinstance(candle, Candle):
            raise TypeError("candles must contain Candle objects")
        if previous is not None and candle.timestamp <= previous:
            raise ValueError("candle timestamps must be strictly increasing; duplicates are not repaired")
        previous = candle.timestamp


def chronological_partitions(
    candles: Sequence[Candle],
    train_ratio: float = 0.60,
    validation_ratio: float = 0.20,
) -> dict[str, tuple[int, int]]:
    """Return half-open index ranges; remaining rows form holdout."""
    if not 0 < train_ratio < 1 or not 0 < validation_ratio < 1:
        raise ValueError("partition ratios must be between 0 and 1")
    if train_ratio + validation_ratio >= 1:
        raise ValueError("train_ratio + validation_ratio must be below 1")
    n = len(candles)
    train_end = int(n * train_ratio)
    validation_end = train_end + int(n * validation_ratio)
    if train_end < 1 or validation_end <= train_end or validation_end >= n:
        raise ValueError("not enough candles for the requested chronological partitions")
    return {
        "train": (0, train_end),
        "validation": (train_end, validation_end),
        "holdout": (validation_end, n),
    }


def walk_forward_windows(
    row_count: int,
    train_size: int,
    validation_size: int,
    step_size: int,
) -> list[dict[str, tuple[int, int]]]:
    """Build expanding-train, rolling-validation windows using half-open indices."""
    if min(row_count, train_size, validation_size, step_size) <= 0:
        raise ValueError("row_count and all window sizes must be positive")
    windows = []
    train_end = train_size
    while train_end + validation_size <= row_count:
        windows.append({
            "train": (0, train_end),
            "validation": (train_end, train_end + validation_size),
        })
        train_end += step_size
    if not windows:
        raise ValueError("not enough rows for one walk-forward window")
    return windows


def _payout_for(signal_index: int, payout: float | Mapping[int, float]) -> float:
    value = payout.get(signal_index, PAYOUT_DEFAULT) if isinstance(payout, Mapping) else payout
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"invalid payout for signal index {signal_index}: {value}")
    return value


def backtest_signals(
    candles: Sequence[Candle],
    signals: Mapping[int, str],
    horizon_min: int,
    *,
    payout: float | Mapping[int, float] = PAYOUT_DEFAULT,
    interval_seconds: int = 60,
    allow_overlapping: bool = False,
    draw_epsilon: float = 1e-12,
) -> list[Trade]:
    """Score caller-supplied closed-candle signals without crossing data gaps.

    signals maps the index of the signal candle to CALL or PUT. For per-trade
    payout, pass a mapping from signal index to rate; missing keys use 92%.
    A payout of 0.92 means +0.92 on a win, -1 on a loss and 0 on a draw.
    """
    validate_candles(candles, interval_seconds)
    if horizon_min <= 0 or horizon_min * 60 % interval_seconds:
        raise ValueError("horizon_min must be a positive multiple of candle interval")
    if not math.isfinite(draw_epsilon) or draw_epsilon < 0:
        raise ValueError("draw_epsilon must be finite and non-negative")

    normalized: dict[int, str] = {}
    for raw_index, raw_direction in signals.items():
        index = int(raw_index)
        direction = str(raw_direction).upper()
        if index < 0 or index >= len(candles) - 1:
            raise ValueError(f"signal index out of range or has no next candle: {index}")
        if direction not in {"CALL", "PUT"}:
            raise ValueError(f"unsupported direction at index {index}: {raw_direction}")
        normalized[index] = direction

    bars_per_horizon = horizon_min * 60 // interval_seconds
    trades: list[Trade] = []
    next_available_signal = 0

    for signal_index in sorted(normalized):
        if not allow_overlapping and signal_index < next_available_signal:
            continue
        entry_index = signal_index + 1
        exit_index = signal_index + bars_per_horizon
        if exit_index >= len(candles):
            continue

        contiguous = all(
            (candles[j].timestamp - candles[j - 1].timestamp).total_seconds() == interval_seconds
            for j in range(signal_index + 1, exit_index + 1)
        )
        if not contiguous:
            continue

        signal = candles[signal_index]
        entry = candles[entry_index]
        exit_candle = candles[exit_index]
        direction = normalized[signal_index]
        delta = exit_candle.close - entry.open
        rate = _payout_for(signal_index, payout)

        if abs(delta) <= draw_epsilon:
            outcome, profit = "DRAW", 0.0
        elif (direction == "CALL" and delta > 0) or (direction == "PUT" and delta < 0):
            outcome, profit = "WIN", rate
        else:
            outcome, profit = "LOSS", -1.0

        trades.append(Trade(
            signal_time=signal.timestamp,
            entry_time=entry.timestamp,
            settlement_time=exit_candle.timestamp + timedelta(seconds=interval_seconds),
            direction=direction,
            horizon_min=horizon_min,
            entry_price=float(entry.open),
            exit_price=float(exit_candle.close),
            outcome=outcome,
            payout=rate,
            profit_units=profit,
        ))
        if not allow_overlapping:
            # The current trade settles at the exit candle close. A signal evaluated
            # on that same close may enter at the following candle open.
            next_available_signal = exit_index

    return trades


def summarize_trades(trades: Iterable[Trade]) -> dict:
    items = list(trades)
    wins = sum(t.outcome == "WIN" for t in items)
    losses = sum(t.outcome == "LOSS" for t in items)
    draws = sum(t.outcome == "DRAW" for t in items)
    decisive = wins + losses
    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    losing_streak = 0
    max_losing_streak = 0
    for trade in items:
        equity += trade.profit_units
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
        if trade.outcome == "LOSS":
            losing_streak += 1
            max_losing_streak = max(max_losing_streak, losing_streak)
        else:
            losing_streak = 0
    mean_payout = sum(t.payout for t in items) / len(items) if items else 0.0
    fixed_payout = not items or all(abs(t.payout - items[0].payout) <= 1e-12 for t in items)
    return {
        "trades": len(items),
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "decisive_trades": decisive,
        "win_rate_pct": round(wins / decisive * 100, 4) if decisive else None,
        "net_profit_units": round(sum(t.profit_units for t in items), 6),
        "expectancy_per_trade": round(sum(t.profit_units for t in items) / len(items), 6) if items else None,
        "max_drawdown_units": round(max_drawdown, 6),
        "max_consecutive_losses": max_losing_streak,
        "mean_payout": round(mean_payout, 6),
        "break_even_win_rate_pct": round(100 / (1 + items[0].payout), 4) if items and fixed_payout else None,
    }


def trades_in_window(
    trades: Iterable[Trade],
    start: datetime,
    end: datetime,
) -> list[Trade]:
    """Keep trades signalled in [start, end) and fully settled by end."""
    if start.tzinfo is None or end.tzinfo is None or start >= end:
        raise ValueError("start/end must be timezone-aware and start < end")
    start_utc, end_utc = start.astimezone(timezone.utc), end.astimezone(timezone.utc)
    return [
        trade for trade in trades
        if start_utc <= trade.signal_time < end_utc and trade.settlement_time <= end_utc
    ]
