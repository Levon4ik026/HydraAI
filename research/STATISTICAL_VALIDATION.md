# Statistical validation diagnostics

This module provides descriptive uncertainty calculations for a frozen, fixed-payout strategy sample. It does not select or optimize a strategy.

## Outputs

- Wilson score 95% interval for decisive win rate (draws excluded).
- Exact one-sided binomial upper-tail probability under the 92% payout break-even null (default payout).
- Net units: wins × payout − losses.
- Expectancy per all trades, including zero-profit draws.

At 92% payout the break-even decisive win rate is 1 / 1.92 = 52.0833%.

## Interpretation safeguards

The binomial calculation assumes independent, identically distributed decisive outcomes. Time-series trades can be serially dependent, regime-dependent, and selected after many experiments. Therefore the p-value is only a diagnostic and can be anti-conservative. A nominally small p-value is not proof of an edge.

Wilson intervals also do not correct for parameter search, multiple testing, nonstationarity, execution costs, quote latency, or data-quality failures. Report sample size and calendar coverage alongside the interval. Keep the prospective rule and thresholds frozen; do not tune on the forward sample.

This module must remain research-only and must not be imported by the Desktop application.
