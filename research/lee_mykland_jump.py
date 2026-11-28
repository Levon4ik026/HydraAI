"""Fičura (2019) Lee–Mykland L-estimator jump detector.

Research-only implementation of the paper's equations (4)-(9).
Input prices are closes of already completed bars. A detected jump at bar i
is only observable at that bar's close; downstream execution must not fill
at that same close in a causal backtest.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence


@dataclass(frozen=True)
class Jump:
    index: int
    direction: str
    log_return: float
    local_sigma: float
    l_statistic: float
    threshold: float


def _threshold(n: int, confidence: float) -> float:
    """Fičura eqs. (6)-(9): Gumbel quantile of the normalized maximum."""
    if n <= 2:
        raise ValueError("n must be greater than 2")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")
    c = math.sqrt(2.0 / math.pi)
    root = math.sqrt(2.0 * math.log(n))
    cn = root / c - (math.log(math.pi) + math.log(math.log(n))) / (2.0 * c * root)
    sn = 1.0 / (c * root)
    gumbel_quantile = -math.log(-math.log(confidence))
    return cn + sn * gumbel_quantile


def detect_jumps(
    closes: Sequence[float],
    *,
    k: int,
    confidence: float,
    threshold_n: int | None = None,
) -> list[Jump]:
    """Detect jumps using only the k-2 bipower products preceding each return.

    closes[i] is the close of bar i. Return i is log(closes[i]/closes[i-1]).
    Local variance for return i uses returns i-k+2 ... i-1, never return i.
    threshold_n controls the sample length n in the paper's extreme-value
    normalization. If omitted, the number of returns in this supplied sample
    is used. For split-safe work, pass the fixed length of the relevant
    partition; n affects only a deterministic threshold, not future prices.
    """
    if k < 4:
        raise ValueError("k must be >= 4")
    prices = [float(x) for x in closes]
    if len(prices) < k + 1:
        return []
    if any(not math.isfinite(x) or x <= 0 for x in prices):
        raise ValueError("all closes must be finite and positive")

    returns = [math.log(prices[i] / prices[i - 1]) for i in range(1, len(prices))]
    n = int(threshold_n if threshold_n is not None else len(returns))
    threshold = _threshold(n, confidence)
    jumps: list[Jump] = []

    # i is the return index (close index) under test. All volatility inputs
    # end at i-1, so the tested return cannot inflate its own denominator.
    for i in range(k - 1, len(returns)):
        first = i - k + 2
        last = i - 1
        products = [
            abs(returns[j]) * abs(returns[j - 1])
            for j in range(first, last + 1)
        ]
        if len(products) != k - 2:
            continue
        local_variance = sum(products) / (k - 2)
        if not math.isfinite(local_variance) or local_variance <= 0:
            continue
        sigma = math.sqrt(local_variance)
        l_value = returns[i] / sigma
        if abs(l_value) > threshold:
            jumps.append(Jump(
                index=i + 1,
                direction="CALL" if returns[i] > 0 else "PUT",
                log_return=returns[i],
                local_sigma=sigma,
                l_statistic=l_value,
                threshold=threshold,
            ))
    return jumps
