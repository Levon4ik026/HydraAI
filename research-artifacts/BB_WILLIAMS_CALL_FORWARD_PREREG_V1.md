# Preregistered forward audit — BB/Williams/ADX CALL 5m

Protocol version: 1.0
Branch: hydra/research-validation
Frozen candidate: CALL-only Bollinger(20, 2 population SD) lower-band re-entry + Williams %R(14) upward cross of -80 + Wilder ADX(14) >= 15.
Historical discovery sample: Dukascopy EURUSD M1 BID, 2026-10-07 through 2026-10-28 01:19 UTC. That sample and the previously inspected post-split observations are not prospective evidence.
Forward start: 2026-10-29 00:00:00 UTC. No signal whose entry is before this boundary is scored.

## Exact rule
1. Build only complete UTC-aligned M5 candles; reset indicators at every missing M5 bucket.
2. On a completed M5 candle, CALL when the previous close was below the previous Bollinger lower band and the current close returns above the current lower band; simultaneously Williams %R(14) crosses upward through -80 (previous <= -80, current > -80).
3. Require Wilder ADX(14) >= 15 on the completed signal candle. The signal is available only after that candle closes.
4. Enter at the immediately following M5 open. Expiry is 5 minutes; settle at the close of that entry M5 candle.
5. CALL only. PUT-side triggers are diagnostic and are not traded by this frozen candidate.

## Accounting and review
- Payout is fixed at 92% for the audit: WIN +0.92u, LOSS -1u, DRAW 0u.
- Break-even decisive win rate is 52.0833%.
- Report CALL, diagnostic PUT, matched opposite-direction CALL timestamps, and non-signal ADX>=15 background separately.
- Report trades, W/L/D, decisive WR, wins/all signals, 95% Wilson interval, net, ROI, PF, max drawdown, max loss streak, signal frequency and WAIT share.
- Wilson intervals assume independent decisive outcomes; market serial dependence makes them optimistic. Add a UTC-day block bootstrap for net result.
- No parameter, direction, expiry, threshold, or filter changes during the forward audit.
- Minimum review threshold: 100 forward CALL trades. A candidate is only preliminarily promising if WR >= 57%, net > 0, PF > 1, and the Wilson lower bound exceeds 52.0833%. This is still not production approval.
- Dukascopy BID is a research proxy, not Pocket Option executable pricing. Spread, quote construction, payout variation, latency, and platform settlement are not modeled.
- No real trades, OTC instruments, production deployment, or automatic execution.
