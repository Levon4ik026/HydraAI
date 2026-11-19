"""Fail-closed observation and risk gate for HydraAI demo integration.

This module deliberately does not send broker orders. It validates feed data,
records candidate signals and exposes a separate execution gate that remains
closed until an explicitly verified broker adapter is supplied.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional
import csv
import math


@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class FeedCheck:
    ok: bool
    reason: str
    count: int
    latest_age_seconds: Optional[float]


@dataclass(frozen=True)
class Signal:
    candidate_id: str
    direction: str
    signal_time: str
    entry_time: str
    expiry_minutes: int
    entry_reference: float
    reason: str


def _parse_time(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def load_candles(path: str | Path) -> list[Candle]:
    rows: list[Candle] = []
    with Path(path).open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        required = {"datetime_utc", "open", "high", "low", "close"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"CSV must contain columns: {sorted(required)}")
        for row in reader:
            try:
                c = Candle(_parse_time(row["datetime_utc"]),
                           float(row["open"]), float(row["high"]),
                           float(row["low"]), float(row["close"]))
            except (TypeError, ValueError, KeyError):
                continue
            if not all(math.isfinite(x) and x > 0 for x in (c.open, c.high, c.low, c.close)):
                continue
            if c.high < max(c.open, c.close, c.low) or c.low > min(c.open, c.close, c.high):
                continue
            rows.append(c)
    rows.sort(key=lambda x: x.timestamp)
    dedup: dict[datetime, Candle] = {c.timestamp: c for c in rows}
    return [dedup[k] for k in sorted(dedup)]


def check_feed(candles: list[Candle], now: Optional[datetime] = None,
               min_bars: int = 60, max_age_seconds: int = 180) -> FeedCheck:
    if len(candles) < min_bars:
        return FeedCheck(False, f"need at least {min_bars} valid candles", len(candles), None)
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    age = (now - candles[-1].timestamp).total_seconds()
    if age < -60:
        return FeedCheck(False, "latest candle is more than 60s in the future", len(candles), age)
    if age > max_age_seconds:
        return FeedCheck(False, f"stale feed: {age:.0f}s old", len(candles), age)
    tail = candles[-min_bars:]
    for left, right in zip(tail, tail[1:]):
        gap = (right.timestamp - left.timestamp).total_seconds()
        if not 50 <= gap <= 70:
            return FeedCheck(False, f"minute gap detected: {gap:.0f}s", len(candles), age)
    return FeedCheck(True, "fresh continuous feed", len(candles), age)


def ema(values: list[float], period: int) -> list[Optional[float]]:
    out: list[Optional[float]] = [None] * len(values)
    if len(values) < period:
        return out
    alpha = 2.0 / (period + 1.0)
    current = sum(values[:period]) / period
    out[period - 1] = current
    for i in range(period, len(values)):
        current = alpha * values[i] + (1.0 - alpha) * current
        out[i] = current
    return out


def rsi(values: list[float], period: int = 14) -> list[Optional[float]]:
    out: list[Optional[float]] = [None] * len(values)
    if len(values) <= period:
        return out
    gains = [max(values[i] - values[i-1], 0.0) for i in range(1, len(values))]
    losses = [max(values[i-1] - values[i], 0.0) for i in range(1, len(values))]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    def value(g: float, l: float) -> float:
        if l == 0:
            return 100.0 if g > 0 else 50.0
        return 100.0 - 100.0 / (1.0 + g / l)
    out[period] = value(avg_gain, avg_loss)
    for i in range(period + 1, len(values)):
        avg_gain = ((period - 1) * avg_gain + gains[i-1]) / period
        avg_loss = ((period - 1) * avg_loss + losses[i-1]) / period
        out[i] = value(avg_gain, avg_loss)
    return out


def aggregate_m5(candles: list[Candle]) -> list[Candle]:
    """Aggregate only exact, contiguous five-candle UTC minute buckets."""
    buckets: dict[datetime, list[Candle]] = {}
    for c in candles:
        minute = c.timestamp.replace(second=0, microsecond=0)
        start_minute = minute.minute - minute.minute % 5
        start = minute.replace(minute=start_minute)
        buckets.setdefault(start, []).append(c)
    result = []
    for start, group in sorted(buckets.items()):
        group.sort(key=lambda x: x.timestamp)
        if len(group) != 5:
            continue
        if any((b.timestamp - a.timestamp).total_seconds() != 60 for a, b in zip(group, group[1:])):
            continue
        result.append(Candle(start, group[0].open, max(x.high for x in group),
                             min(x.low for x in group), group[-1].close))
    return result


def candidate_001_signals(m5: list[Candle]) -> list[Signal]:
    """Conservative implementation of the documented CAND-001 condition."""
    closes = [c.close for c in m5]
    e20, e50, r = ema(closes, 20), ema(closes, 50), rsi(closes, 14)
    out = []
    for i in range(120, len(m5) - 1):
        c = m5[i]
        if e20[i] is None or e50[i] is None or r[i] is None:
            continue
        atr_series = []
        for end in range(max(14, i - 120), i + 1):
            tr_window = []
            for j in range(end - 13, end + 1):
                prev = m5[j-1].close
                tr_window.append(max(m5[j].high - m5[j].low,
                                     abs(m5[j].high - prev), abs(m5[j].low - prev)))
            atr_series.append(sum(tr_window) / 14)
        if len(atr_series) < 2:
            continue
        atr = atr_series[-1]
        prior_atrs = atr_series[:-1]
        rank = sum(x <= atr for x in prior_atrs) / len(prior_atrs) * 100
        if r[i] >= 70 and c.close < c.open and e20[i] > e50[i] and rank > 67:
            entry = m5[i+1]
            out.append(Signal("CAND-001", "PUT", c.timestamp.isoformat(),
                              entry.timestamp.isoformat(), 5, entry.open,
                              f"RSI14={r[i]:.2f}; bearish M5; EMA20>EMA50; ATR percentile={rank:.1f}"))
    return out


class DemoExecutionGate:
    """Execution stays disabled unless every safety condition is explicitly met."""
    def __init__(self, *, account_mode: str = "DEMO", instrument: str = "EURUSD",
                 otc: bool = False, broker_adapter_verified: bool = False,
                 explicit_live_authorization: bool = False):
        self.account_mode = account_mode.upper()
        self.instrument = instrument.upper()
        self.otc = otc
        self.broker_adapter_verified = broker_adapter_verified
        self.explicit_live_authorization = explicit_live_authorization

    def can_submit(self, *, feed_ok: bool, payout: float,
                   open_positions: int, daily_loss_units: float,
                   max_daily_loss_units: float = 3.0) -> tuple[bool, str]:
        if self.account_mode != "DEMO":
            return False, "account mode must be DEMO"
        if self.instrument != "EURUSD" or self.otc:
            return False, "only non-OTC EURUSD is permitted"
        if not self.broker_adapter_verified:
            return False, "broker order adapter is not verified; execution locked"
        if not feed_ok:
            return False, "feed is stale or discontinuous"
        if payout < 0.92:
            return False, "payout below configured 92% floor"
        if open_positions >= 1:
            return False, "one-position limit reached"
        if daily_loss_units >= max_daily_loss_units:
            return False, "daily loss limit reached"
        return True, "risk checks passed"

    def can_submit_real(self) -> bool:
        return self.account_mode == "REAL" and self.explicit_live_authorization and self.broker_adapter_verified


def append_signal_log(path: str | Path, signals: Iterable[Signal]) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(signals)
    if not rows:
        return 0
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(rows[0]).keys()))
        if not exists:
            writer.writeheader()
        for signal in rows:
            writer.writerow(asdict(signal))
    return len(rows)
