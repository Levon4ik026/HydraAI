"""Gap-aware EUR/USD candle indicators and deterministic binary backtesting."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from math import isfinite
from typing import Iterable, Mapping, Sequence, Any

@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float

@dataclass(frozen=True)
class Trade:
    signal_time: datetime
    entry_time: datetime
    exit_time: datetime
    direction: str
    entry_price: float
    exit_price: float
    payout: float
    outcome: str
    profit_units: float
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

def _timestamp(value: Any) -> datetime:
    dt = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("Timestamp must include a timezone (UTC recommended).")
    return dt.astimezone(timezone.utc)

def normalize_candles(rows: Iterable[Mapping[str, Any]]) -> list[Candle]:
    """Parse OHLC, reject malformed candles, sort ascending, keep last duplicate."""
    parsed: dict[datetime, Candle] = {}
    for row in rows:
        ts = _timestamp(row.get("datetime", row.get("datetime_utc")))
        o, h, l, c = (float(row[k]) for k in ("open", "high", "low", "close"))
        if not all(isfinite(v) and v > 0 for v in (o, h, l, c)):
            raise ValueError(f"Non-finite or non-positive OHLC at {ts.isoformat()}")
        if h < max(o, l, c) or l > min(o, h, c):
            raise ValueError(f"Invalid OHLC ordering at {ts.isoformat()}")
        parsed[ts] = Candle(ts, o, h, l, c)
    return [parsed[k] for k in sorted(parsed)]

def split_contiguous(candles: Sequence[Candle], interval: timedelta = timedelta(minutes=1)) -> list[list[Candle]]:
    """Split on every missing/irregular candle; no indicator state crosses a gap."""
    if not candles:
        return []
    segments: list[list[Candle]] = [[candles[0]]]
    for candle in candles[1:]:
        if candle.timestamp - segments[-1][-1].timestamp != interval:
            segments.append([candle])
        else:
            segments[-1].append(candle)
    return segments

def _ema(values: Sequence[float], period: int) -> list[float | None]:
    if period < 1:
        raise ValueError("EMA period must be >= 1")
    alpha = 2.0 / (period + 1.0)
    result: list[float | None] = [None] * len(values)
    state = None
    for i, value in enumerate(values):
        state = value if state is None else alpha * value + (1.0 - alpha) * state
        if i >= period - 1:
            result[i] = state
    return result

def _rsi(values: Sequence[float], period: int = 14) -> list[float | None]:
    if period < 1:
        raise ValueError("RSI period must be >= 1")
    out: list[float | None] = [None] * len(values)
    if len(values) <= period:
        return out
    changes = [values[i] - values[i - 1] for i in range(1, len(values))]
    gain = sum(max(x, 0.0) for x in changes[:period]) / period
    loss = sum(max(-x, 0.0) for x in changes[:period]) / period
    def value(g: float, l: float) -> float:
        if l == 0.0 and g == 0.0: return 50.0
        if l == 0.0: return 100.0
        if g == 0.0: return 0.0
        return 100.0 - 100.0 / (1.0 + g / l)
    out[period] = value(gain, loss)
    for i in range(period + 1, len(values)):
        change = changes[i - 1]
        gain = ((period - 1) * gain + max(change, 0.0)) / period
        loss = ((period - 1) * loss + max(-change, 0.0)) / period
        out[i] = value(gain, loss)
    return out

def calculate_indicators(candles: Sequence[Candle], ema_fast: int = 20, ema_slow: int = 50, rsi_period: int = 14) -> list[dict[str, Any]]:
    """Calculate indicators independently in each contiguous one-minute segment."""
    result = []
    for segment_id, segment in enumerate(split_contiguous(candles)):
        closes = [c.close for c in segment]
        fast, slow, rsi = _ema(closes, ema_fast), _ema(closes, ema_slow), _rsi(closes, rsi_period)
        for i, candle in enumerate(segment):
            signal = 0
            if fast[i] is not None and slow[i] is not None and rsi[i] is not None:
                if fast[i] > slow[i] and 50.0 <= rsi[i] <= 65.0: signal = 1
                elif fast[i] < slow[i] and 35.0 <= rsi[i] < 50.0: signal = -1
            result.append({"timestamp": candle.timestamp, "open": candle.open, "high": candle.high,
                "low": candle.low, "close": candle.close, "segment_id": segment_id,
                "ema_fast": fast[i], "ema_slow": slow[i], "rsi": rsi[i], "signal": signal})
    return result

def backtest_non_overlapping(rows: Sequence[Mapping[str, Any]], horizon: int, payout: float = 0.92,
    payout_by_entry: Mapping[datetime, float] | None = None, start_time: datetime | None = None,
    end_time: datetime | None = None) -> list[Trade]:
    """One CALL/PUT scheduler. Win=+payout, loss=-1, draw=0; payout is net."""
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 1:
        raise ValueError("horizon must be a positive integer")
    if not isfinite(payout) or payout < 0: raise ValueError("payout must be finite and non-negative")
    start = _timestamp(start_time) if start_time is not None else None
    end = _timestamp(end_time) if end_time is not None else None
    times = [_timestamp(r["timestamp"]) for r in rows]
    if any(current <= previous for previous, current in zip(times, times[1:])):
        raise ValueError("row timestamps must be strictly increasing; duplicates or reversals are not repaired")
    for index, row in enumerate(rows):
        for key in ("open", "close"):
            value = float(row[key])
            if not isfinite(value) or value <= 0:
                raise ValueError(f"{key} must be finite and positive at row {index}")
    trades: list[Trade] = []
    i = 0
    while i + horizon < len(rows):
        signal = int(rows[i].get("signal", 0))
        if signal not in (-1, 1):
            i += 1
            continue
        entry_i, exit_i = i + 1, i + horizon
        if any(times[j] - times[j - 1] != timedelta(minutes=1) for j in range(i + 1, exit_i + 1)):
            i += 1
            continue
        signal_time, entry_time, exit_time = times[i], times[entry_i], times[exit_i]
        entry_price, exit_price = float(rows[entry_i]["open"]), float(rows[exit_i]["close"])
        change = exit_price - entry_price
        actual_payout = float(payout_by_entry.get(entry_time, payout)) if payout_by_entry else payout
        if not isfinite(actual_payout) or actual_payout < 0:
            raise ValueError(f"Invalid payout for entry {entry_time.isoformat()}")
        if abs(change) < 1e-12: outcome, profit = "DRAW", 0.0
        elif (signal == 1 and change > 0) or (signal == -1 and change < 0): outcome, profit = "WIN", actual_payout
        else: outcome, profit = "LOSS", -1.0
        if (start is None or exit_time >= start) and (end is None or exit_time < end):
            trades.append(Trade(signal_time, entry_time, exit_time, "CALL" if signal == 1 else "PUT",
                entry_price, exit_price, actual_payout, outcome, profit))
        i = exit_i
    return trades

def summarize(trades: Sequence[Trade]) -> dict[str, float | int]:
    wins = sum(t.outcome == "WIN" for t in trades)
    losses = sum(t.outcome == "LOSS" for t in trades)
    draws = sum(t.outcome == "DRAW" for t in trades)
    decisive = wins + losses
    equity = peak = max_dd = 0.0
    for trade in trades:
        equity += trade.profit_units
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    return {"trades": len(trades), "wins": wins, "losses": losses, "draws": draws,
        "decisive_win_rate_pct": round(100.0 * wins / decisive, 4) if decisive else 0.0,
        "net_profit_units": round(sum(t.profit_units for t in trades), 4),
        "max_drawdown_units": round(max_dd, 4)}
