# Direct vs inverse indicator experiment — 2026-11-09

## Question
Can a consistently weak directional rule become profitable when every signal is reversed?

## Dataset and protocol
- Source: `eurusd_research_clean.csv`, 486,488 EUR/USD M1 candles, 2025-07-21 15:11 UTC through 2026-11-05 16:08 UTC.
- The experiment was run on this full dataset. Chronological split: first 70% of rows for TRAIN, final 30% for TEST; boundary at 2026-06-17 04:44 UTC.
- Indicators are calculated independently inside uninterrupted one-minute segments; no indicator lookback or expiry is allowed to bridge a timestamp gap.
- Signal is formed at candle close; entry is next candle open; expiry is the close after 1, 3, or 5 minutes.
- Ties are draws and excluded from win-rate denominator. Each candle can generate a signal, so trades overlap; the large counts are not independent observations.
- Direct EV per unit stake assumes fixed 92% net payout: `win_rate × 1.92 − 1`. Inverse win rate is the direct loss rate among decisive outcomes. Fees, payout changes, execution delay and OTC are not modelled.

## Rules tested
- EMA9/EMA21 trend direction.
- Five-candle momentum direction.
- RSI14 extreme momentum: CALL when RSI >= 70, PUT when RSI <= 30.
- RSI14 extreme fade: opposite of the preceding RSI rule.
- Bollinger 20-period, 2-standard-deviation fade: CALL below lower band, PUT above upper band.

## Main results: weak RSI-extreme momentum rule and its inverse
| Expiry | Split | Direct win rate | Inverse win rate | Inverse EV at 92% |
|---:|---|---:|---:|---:|
| 1m | Train | 47.59% | 52.41% | +0.0062 |
| 1m | Test | 48.30% | 51.70% | -0.0073 |
| 3m | Train | 47.02% | 52.98% | +0.0173 |
| 3m | Test | 47.79% | 52.21% | +0.0025 |
| 5m | Train | 46.47% | 53.53% | +0.0277 |
| 5m | Test | 47.48% | 52.52% | +0.0084 |

The 5-minute inverse looks marginally positive in the holdout, but the estimated advantage is tiny: about 0.0084 units per unit stake before any friction. The 3-minute result is effectively at break-even. The 1-minute result is negative. This is a candidate for stricter validation, not a usable trading signal.

## Other rules: holdout direct / inverse win rate
| Rule | Expiry | Direct TEST | Inverse TEST |
|---|---:|---:|---:|
| EMA9/21 trend | 1m | 49.34% | 50.66% |
| EMA9/21 trend | 3m | 49.15% | 50.85% |
| EMA9/21 trend | 5m | 49.08% | 50.92% |
| MOM5 trend | 1m | 48.78% | 51.22% |
| MOM5 trend | 3m | 48.73% | 51.27% |
| MOM5 trend | 5m | 48.99% | 51.01% |
| RSI extreme momentum | 1m | 48.30% | 51.70% |
| RSI extreme momentum | 3m | 47.79% | 52.21% |
| RSI extreme momentum | 5m | 47.48% | 52.52% |
| RSI extreme fade | 1m | 51.70% | 48.30% |
| RSI extreme fade | 3m | 52.21% | 47.79% |
| RSI extreme fade | 5m | 52.52% | 47.48% |
| Bollinger fade | 1m | 52.84% | 47.16% |
| Bollinger fade | 3m | 52.98% | 47.02% |
| Bollinger fade | 5m | 52.79% | 47.21% |

## Interpretation
1. The idea is real: reversing a rule with a sub-50% hit rate raises the hit rate to its complement, provided ties are excluded symmetrically.
2. But inversion does not automatically create an edge. EMA and momentum inversions remain below the 52.08% break-even rate required at 92% payout.
3. RSI extreme momentum is the most interesting weak rule in this small rule set. Its inverse barely clears the theoretical 92% hurdle at 3m and 5m in the holdout, and fails at 1m.
4. The 5m holdout edge is very small and may be due to overlapping trades, market-regime dependence, parameter selection or chance. No confidence interval or multiple-testing correction is applied here.
5. RSI extreme fade and Bollinger fade are already above 50%; reversing them makes results worse. “Always do the opposite” is not a universal principle.

## Decision
**Do not add any inverse strategy to HydraAI signals yet.** The next gate should be a stricter event-driven replay of the inverse RSI-extreme rule with non-overlapping positions, confidence intervals, regime splits and a final untouched holdout. We should also test whether the result survives payout 85%, 90% and 92%. This experiment is research-only; automatic trading remains disabled.

## Reproducibility
Run:
```bash
python research/inverse_indicator_experiment.py /path/to/eurusd_research_clean.csv --payout 0.92
```
