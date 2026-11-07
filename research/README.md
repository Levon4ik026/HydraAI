# HydraAI Research — validation workspace

This branch is based on `hydra/stabilization` and keeps all experiments isolated from the Desktop application and production math core.

## Frozen PUT forward experiment

The prospective monitor and candidate remain unchanged. See:
- `PUT_PROSPECTIVE_VALIDATION_PROTOCOL_2026-11-07.md`
- `frozen_put_candidate.py`
- `watch_frozen_put_candidate.py`

Do not tune thresholds using forward observations. Keep the data collector and monitor running independently; neither executes trades.

## Research scoring and uncertainty

- `backtest_engine.py`: closed-candle signal scoring, next-candle-open entry, gap-safe settlement, non-overlap scheduling, 92% default payout, chronological partitions and walk-forward windows.
- `statistical_validation.py`: Wilson interval, exact one-sided binomial diagnostic, break-even and net-unit arithmetic.
- `BACKTEST_ENGINE_SPEC.md` and `STATISTICAL_VALIDATION.md`: conventions and limitations.

The binomial p-value assumes independent decisive outcomes. It is not a proof of edge and does not correct for serial dependence, parameter search, regime selection or execution costs.

## Run

    python -m unittest discover -s tests -v
    python -m unittest discover -s research/tests -v

All code here is research-only. Nothing in this branch is imported into or connected to the live Desktop application.


Statistical unit tests were added for Wilson intervals, binomial-tail arithmetic, 92% payout break-even, draw handling and invalid inputs.

The forward monitor prints a Wilson 95% interval alongside the live decisive win rate; this is descriptive uncertainty, not a deployment signal.
