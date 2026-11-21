"""Conservative regime classifier and forward-only candidate selector.

No candidate is eligible on historical research figures alone. Eligibility is
computed from forward outcomes tagged with the regime at signal time.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import sqrt
from typing import Iterable
from .engine import Candle

REGIMES = ("TREND", "RANGE", "HIGH_VOLATILITY", "IMPULSE", "UNKNOWN")

@dataclass(frozen=True)
class Regime:
    name: str
    confidence: float
    details: str

@dataclass(frozen=True)
class CandidateStats:
    candidate_id: str
    regime: str
    wins: int
    losses: int
    draws: int = 0
    max_drawdown_units: float = 0.0
    payout: float = 0.92

    @property
    def trades(self) -> int:
        return self.wins + self.losses

    @property
    def expectancy(self) -> float:
        n = self.trades
        return ((self.wins * self.payout) - self.losses) / n if n else float("-inf")

    @property
    def wilson_lower(self) -> float:
        n = self.trades
        if not n: return 0.0
        z = 1.96
        p = self.wins / n
        den = 1 + z*z/n
        center = p + z*z/(2*n)
        margin = z*sqrt((p*(1-p)+z*z/(4*n))/n)
        return (center-margin)/den


def classify_regime(candles: list[Candle]) -> Regime:
    """Classify using only the last 60 completed M1 bars; conservative UNKNOWN fallback."""
    if len(candles) < 60:
        return Regime("UNKNOWN", 0.0, "need 60 completed M1 candles")
    cs = candles[-60:]
    closes = [c.close for c in cs]
    ranges = [(c.high-c.low) for c in cs]
    if any(not (c.high >= max(c.open,c.close,c.low) and c.low <= min(c.open,c.close,c.high)) for c in cs):
        return Regime("UNKNOWN", 0.0, "invalid OHLC")
    returns = [(closes[i]/closes[i-1]-1) for i in range(1,len(closes))]
    abs_returns = sorted(abs(x) for x in returns)
    med = abs_returns[len(abs_returns)//2]
    recent_vol = sum(ranges[-10:])/10
    baseline_vol = sum(ranges[:-10])/50
    net_move = abs(closes[-1]/closes[0]-1)
    path_move = sum(abs(x) for x in returns)
    efficiency = net_move/path_move if path_move else 0.0
    impulse = abs(returns[-1]) / max(med, 1e-12)
    if recent_vol > baseline_vol*2.0 and baseline_vol > 0:
        return Regime("HIGH_VOLATILITY", min(.99, recent_vol/(baseline_vol*2.0)*.7), f"range ratio={recent_vol/baseline_vol:.2f}")
    if impulse >= 4.0:
        return Regime("IMPULSE", min(.99, impulse/6), f"last return / median abs return={impulse:.2f}")
    if efficiency >= .55 and net_move >= .00035:
        return Regime("TREND", min(.95, .5+efficiency/2), f"directional efficiency={efficiency:.2f}")
    if efficiency <= .25:
        return Regime("RANGE", min(.9, .6+(0.25-efficiency)), f"directional efficiency={efficiency:.2f}")
    return Regime("UNKNOWN", .35, f"mixed structure; efficiency={efficiency:.2f}")


def select_candidate(regime: Regime, stats: Iterable[CandidateStats], *, payout: float,
                     min_trades: int = 100, max_drawdown_units: float = 3.0) -> tuple[str | None, str]:
    """Select only a forward-validated edge; otherwise WAIT.

    The 95% Wilson lower confidence bound must exceed the break-even win rate
    for the supplied payout, and realized expectancy must be positive.
    """
    if regime.name not in REGIMES or regime.name == "UNKNOWN":
        return None, "WAIT: market regime is not classified confidently"
    if not (0 < payout <= 1):
        return None, "WAIT: invalid payout"
    breakeven = 1/(1+payout)
    eligible=[]
    for s in stats:
        if s.regime != regime.name or s.trades < min_trades: continue
        if s.payout + 1e-9 < payout:  # stats cannot be reused at a worse payout
            continue
        if s.max_drawdown_units > max_drawdown_units: continue
        if s.expectancy <= 0 or s.wilson_lower <= breakeven: continue
        eligible.append(s)
    if not eligible:
        return None, f"WAIT: no candidate has >= {min_trades} forward trades with 95% lower WR > {breakeven:.2%}, positive expectancy and DD <= {max_drawdown_units:.1f}"
    best=max(eligible, key=lambda x:(x.expectancy, x.wilson_lower, -x.max_drawdown_units))
    return best.candidate_id, f"selected {best.candidate_id}; regime={regime.name}; n={best.trades}; expectancy={best.expectancy:.3f}; Wilson95-LB={best.wilson_lower:.2%}"