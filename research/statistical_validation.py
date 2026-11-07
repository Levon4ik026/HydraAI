"""Statistical diagnostics for fixed-payout, research-only trade samples.

The exact binomial test assumes independent, identically distributed decisive
outcomes. Financial trades can be dependent; treat its p-value as a diagnostic,
not a deployment criterion. Draws are excluded from the decisive WR denominator.
"""
from __future__ import annotations

import math
from typing import Any


def wilson_interval(successes: int, trials: int, confidence_z: float = 1.959963984540054) -> tuple[float, float] | None:
    """Two-sided Wilson score interval as proportions in [0, 1]."""
    if isinstance(successes, bool) or isinstance(trials, bool):
        raise ValueError("successes and trials must be integers")
    if int(successes) != successes or int(trials) != trials:
        raise ValueError("successes and trials must be integers")
    successes, trials = int(successes), int(trials)
    if trials < 0 or successes < 0 or successes > trials:
        raise ValueError("require 0 <= successes <= trials")
    if not math.isfinite(confidence_z) or confidence_z <= 0:
        raise ValueError("confidence_z must be finite and positive")
    if trials == 0:
        return None
    p = successes / trials
    z2 = confidence_z * confidence_z
    denominator = 1.0 + z2 / trials
    center = (p + z2 / (2.0 * trials)) / denominator
    radius = confidence_z * math.sqrt(
        p * (1.0 - p) / trials + z2 / (4.0 * trials * trials)
    ) / denominator
    return max(0.0, center - radius), min(1.0, center + radius)


def binomial_upper_tail(successes: int, trials: int, null_probability: float) -> float | None:
    """P[X >= successes] under Binomial(trials, null_probability), evaluated stably."""
    if isinstance(successes, bool) or isinstance(trials, bool):
        raise ValueError("successes and trials must be integers")
    if int(successes) != successes or int(trials) != trials:
        raise ValueError("successes and trials must be integers")
    successes, trials = int(successes), int(trials)
    if trials < 0 or successes < 0 or successes > trials:
        raise ValueError("require 0 <= successes <= trials")
    if not math.isfinite(null_probability) or not 0.0 <= null_probability <= 1.0:
        raise ValueError("null_probability must be in [0, 1]")
    if trials == 0:
        return None
    if successes == 0:
        return 1.0
    if null_probability == 0.0:
        return 0.0
    if null_probability == 1.0:
        return 1.0
    log_p = math.log(null_probability)
    log_q = math.log1p(-null_probability)
    logs = [
        math.lgamma(trials + 1) - math.lgamma(k + 1) - math.lgamma(trials - k + 1)
        + k * log_p + (trials - k) * log_q
        for k in range(successes, trials + 1)
    ]
    peak = max(logs)
    return min(1.0, math.exp(peak) * sum(math.exp(value - peak) for value in logs))


def summarize_fixed_payout(
    wins: int,
    losses: int,
    draws: int = 0,
    payout: float = 0.92,
    confidence_z: float = 1.959963984540054,
) -> dict[str, Any]:
    """Summarize outcomes and compare decisive WR with fixed-payout break-even."""
    counts = (wins, losses, draws)
    if any(isinstance(value, bool) or int(value) != value or value < 0 for value in counts):
        raise ValueError("wins, losses and draws must be non-negative integers")
    wins, losses, draws = map(int, counts)
    if not math.isfinite(payout) or payout < 0:
        raise ValueError("payout must be finite and non-negative")
    decisive = wins + losses
    total = decisive + draws
    breakeven = 1.0 / (1.0 + payout) if payout >= 0 else None
    interval = wilson_interval(wins, decisive, confidence_z)
    p_value = binomial_upper_tail(wins, decisive, breakeven) if decisive else None
    net = wins * payout - losses
    return {
        "trades": total,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "decisive_trades": decisive,
        "win_rate": wins / decisive if decisive else None,
        "wilson_95_low": interval[0] if interval else None,
        "wilson_95_high": interval[1] if interval else None,
        "break_even_win_rate": breakeven,
        "binomial_p_value_one_sided_iid_assumption": p_value,
        "net_profit_units": round(net, 6),
        "expectancy_per_trade_including_draws": net / total if total else None,
        "payout": payout,
        "statistical_warning": (
            "Binomial p-value assumes independent decisive outcomes; serial dependence, "
            "regime selection and multiple testing can make it anti-conservative."
        ),
    }
